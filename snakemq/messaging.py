# -*- coding: utf-8 -*-
"""
Data format
===========
Each packet contains always a single frame: ``[1B type|payload]``.

Payload
-------
- protokol version: ``[4B version]``.
- incompatible protocol: ``[]``
- identification: ``[ident]``
- message: ``[16B UUID|4B TTL|4B flags|message]``

:author: David Siroky (siroky@dasir.cz)
:license: MIT License (see LICENSE.txt or
          U{http://www.opensource.org/licenses/mit-license.php})
"""

import struct
import logging
import threading
import re

from snakemq.exceptions import (SnakeMQBrokenMessage, SnakeMQException,
                                SnakeMQIncompatibleProtocol)
from snakemq.queues import QueuesManager
from snakemq.message import Message
from snakemq.callbacks import Callback
import snakemq.version

############################################################################
############################################################################
# py2/3
############################################################################

try:
    memoryview
except NameError:
    memoryview = buffer

############################################################################
############################################################################

MAX_IDENT_LENGTH = 50

FRAME_TYPE_PROTOCOL_VERSION = 0
FRAME_TYPE_INCOMPATIBLE_PROTOCOL = 1
FRAME_TYPE_IDENTIFICATION = 2
FRAME_TYPE_MESSAGE = 3

FRAME_TYPE_TYPE = "B"
FRAME_TYPE_SIZE = 1  # 1 byte

FRAME_FORMAT_PROTOCOL_VERSION = "!I"
FRAME_FORMAT_PROTOCOL_VERSION_SIZE = struct.calcsize(FRAME_FORMAT_PROTOCOL_VERSION)
FRAME_FORMAT_MESSAGE = "!16sII"
FRAME_FORMAT_MESSAGE_SIZE = struct.calcsize(FRAME_FORMAT_MESSAGE)

MIN_FRAME_SIZE = 1  # just the type field

ENCODING = "utf-8"

#############################################################################
#############################################################################

class Messaging(object):
    def __init__(self, identifier, domain, packeter, queues_storage=None):
        """
        :param identifier: peer identifier
        :param domain: currently unused
        :param packeter: :class:`~snakemq.packeter.Packeter`
        :param queues_storage: :class:`~snakemq.storage.QueuesStorageBase`
        """
        self.identifier = identifier[:MAX_IDENT_LENGTH]
        self.domain = domain
        self.packeter = packeter
        self.queues_manager = QueuesManager(queues_storage)
        self.log = logging.getLogger("snakemq.messaging")

        #{ callbacks
        self.on_error = Callback()  #: ``func(conn_id, exception)``
        self.on_message_recv = Callback()  #: ``func(conn_id, ident, message)``
        self.on_connect = Callback()  #: ``func(conn_id, ident)``
        self.on_disconnect = Callback()  #: ``func(conn_id, ident)``
        #}

        self._ident_by_conn = {}
        self._conn_by_ident = {}

        packeter.link.on_loop_pass.add(self._on_link_loop_pass)
        packeter.on_connect.add(self._on_connect)
        packeter.on_disconnect.add(self._on_disconnect)
        packeter.on_packet_recv.add(self._on_packet_recv)

        self._lock = threading.Lock()

    ###########################################################

    def _on_connect(self, conn_id):
        self.send_protocol_version(conn_id)
        self.send_identification(conn_id)

    ###########################################################

    def _on_disconnect(self, conn_id):
        if conn_id not in self._ident_by_conn:
            return

        ident = self._ident_by_conn.pop(conn_id)
        with self._lock:
            self.queues_manager.get_queue(ident).disconnect()
        del self._conn_by_ident[ident]
        self.on_disconnect(conn_id, ident)

    ###########################################################

    def parse_protocol_version(self, payload, conn_id):
        if len(payload) != FRAME_FORMAT_PROTOCOL_VERSION_SIZE:
            raise SnakeMQBrokenMessage("protocol version")

        protocol = struct.unpack(FRAME_FORMAT_PROTOCOL_VERSION, payload)[0]
        if protocol != snakemq.version.PROTOCOL_VERSION:
            self.send_incompatible_protocol(conn_id)
            raise SnakeMQIncompatibleProtocol(
                            "remote side protocol version is %i" % protocol)
        self.log.debug("conn=%s remote version %X" % (conn_id, protocol))

    ###########################################################

    def parse_incompatible_protocol(self, conn_id):
        self.log.debug("conn=%s remote side rejected protocol version" % conn_id)
        # TODO

    ###########################################################

    def parse_identification(self, remote_ident, conn_id):
        remote_ident = remote_ident.decode(ENCODING, "replace")
        self.log.debug("conn=%s remote ident '%s'" % (conn_id, remote_ident))

        if conn_id in self._ident_by_conn:
            # avoid multiple identifications
            return

        with self._lock:
            self.queues_manager.get_queue(remote_ident).connect()
        self._ident_by_conn[conn_id] = remote_ident
        self._conn_by_ident[remote_ident] = conn_id
        self.on_connect(conn_id, remote_ident)

    ###########################################################

    def parse_message(self, payload, conn_id):
        if len(payload) < FRAME_FORMAT_MESSAGE_SIZE:
            raise SnakeMQBrokenMessage("message")

        muuid, ttl, flags = struct.unpack(FRAME_FORMAT_MESSAGE,
                                          payload[:FRAME_FORMAT_MESSAGE_SIZE])
        message = Message(data=bytes(payload[FRAME_FORMAT_MESSAGE_SIZE:]),
                          uuid=muuid, ttl=ttl, flags=flags)
        self.on_message_recv(conn_id, self._ident_by_conn[conn_id], message)

    ###########################################################

    def _on_packet_recv(self, conn_id, packet):
        try:
            if len(packet) < MIN_FRAME_SIZE:
                raise SnakeMQBrokenMessage("too small")

            frame_type = ord(packet[:FRAME_TYPE_SIZE])
            payload = memoryview(packet)[FRAME_TYPE_SIZE:]

            # TODO allow parse_* calls only after protocol version negotiation
            if frame_type == FRAME_TYPE_PROTOCOL_VERSION:
                self.parse_protocol_version(payload, conn_id)
            elif frame_type == FRAME_TYPE_INCOMPATIBLE_PROTOCOL:
                self.parse_incompatible_protocol(conn_id)
            elif frame_type == FRAME_TYPE_IDENTIFICATION:
                self.parse_identification(bytes(payload), conn_id)
            elif frame_type == FRAME_TYPE_MESSAGE:
                self.parse_message(payload, conn_id)
        except SnakeMQException as exc:
            self.log.error("conn=%s ident=%s %r" %
                  (conn_id, self._ident_by_conn.get(conn_id), exc))
            self.on_error(conn_id, exc)
            self.packeter.link.close(conn_id)

    ###########################################################

    def frame_protocol_version(self):
        return (struct.pack(FRAME_TYPE_TYPE, FRAME_TYPE_PROTOCOL_VERSION) +
                struct.pack(FRAME_FORMAT_PROTOCOL_VERSION,
                            snakemq.version.PROTOCOL_VERSION))

    def send_protocol_version(self, conn_id):
        self.packeter.send_packet(conn_id, self.frame_protocol_version())

    ###########################################################

    def frame_incompatible_protocol(self):
        return struct.pack(FRAME_TYPE_TYPE, FRAME_TYPE_INCOMPATIBLE_PROTOCOL)

    def send_incompatible_protocol(self, conn_id):
        self.packeter.send_packet(conn_id, self.frame_incompatible_protocol())

    ###########################################################

    def frame_identification(self):
        return (struct.pack(FRAME_TYPE_TYPE, FRAME_TYPE_IDENTIFICATION) +
                self.identifier.encode(ENCODING))

    def send_identification(self, conn_id):
        self.packeter.send_packet(conn_id, self.frame_identification())

    ###########################################################

    def frame_message(self, message):
        return (struct.pack(FRAME_TYPE_TYPE, FRAME_TYPE_MESSAGE) +
                struct.pack(FRAME_FORMAT_MESSAGE,
                            message.uuid,
                            int(message.ttl),
                            message.flags) +
                message.data)

    def send_message_frame(self, conn_id, message):
        self.packeter.send_packet(conn_id, self.frame_message(message))

    ###########################################################

    def _on_link_loop_pass(self):
        for ident, conn_id in self._conn_by_ident.items():
            with self._lock:
                queue = self.queues_manager.get_queue(ident)
                if len(queue) == 0:
                    continue
                item = queue.get()
                queue.pop()
                self.send_message_frame(conn_id, item)

    ###########################################################

    def send_message(self, ident, message):
        """
        Thread safe.

        :param ident: destination address
        :param message: :class:`~snakemq.message.Message`
        """
        assert isinstance(message, Message)
        with self._lock:
            self.queues_manager.get_queue(ident).push(message)
        self.packeter.link.wakeup_poll()

#############################################################################
#############################################################################

class ReceiveHook(object):
    """
    Received messages are classified by regexp. Appropriate callbacks are
    called.
    """

    def __init__(self, messaging):
        self.messaging = messaging
        #: regexp:(compiled_regexp, callback)
        self._hooks = {}

        messaging.on_message_recv = self._on_message_receive

    ###########################################################

    def register(self, regexp, callback):
        """
        :param regexp:
        :param callback: L{Messaging.on_message_recv}
        """
        self._hooks[regexp] = (re.compile(regexp), callback)

    ###########################################################

    def unregister(self, regexp):
        del self._hooks[regexp]

    ###########################################################

    def clear(self):
        self._hooks.clear()

    ###########################################################

    def _get_callbacks(self, txt):
        """
        :return: all callbacks that matches
        """
        return [callback for regexp, callback in self._hooks.values()
                                            if regexp.match(txt)]

    ###########################################################

    def _on_message_receive(self, conn_id, ident, message):
        for callback in self._get_callbacks(message.data):
            callback(conn_id, ident, message)
