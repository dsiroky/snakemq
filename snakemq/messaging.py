# -*- coding: utf-8 -*-
"""
@author: David Siroky (siroky@dasir.cz)
"""
# TODO same ident over more links + round robin sending

import logging

import snakemq.codec
import snakemq.exceptions
import snakemq.version

############################################################################
############################################################################

PART_TYPE_PROTOCOL_VERSION = 0
PART_TYPE_IDENT = 1
PART_TYPE_MESSAGE = 2

MESSAGE_TYPE_SIGNAL = 0 #: deliver only if connected
MESSAGE_TYPE_TRANSIENT = 1 #: drop on process end (queue to memory if needed)
MESSAGE_TYPE_PERSISTENT = 2 #: deliver at all cost (queue to disk if needed)

############################################################################
############################################################################

def _empty(*args, **kwargs):
    """
    Sink.
    """
    pass

#############################################################################
#############################################################################

class Messaging(object):
    def __init__(self, identifier, transport, codec=snakemq.codec.BerCodec()):
        self.identifier = identifier
        self.transport = transport
        assert isinstance(codec, snakemq.codec.BaseCodec)
        self.codec = codec
        self.log = logging.getLogger("snakemq.messaging")

        # callbacks
        self.on_error = _empty #: C{func(conn_id, exception)}
        self.on_message_recv = _empty #: C{func(conn_id, ident, message)}

        self._ident_by_conn = {}
        self._conn_by_ident = {}

        self.transport.on_connect = self._on_connect
        self.transport.on_disconnect = self._on_disconnect
        self.transport.on_packet_recv = self._on_packet_recv

    ###########################################################

    def _on_connect(self, conn_id):
        self.send_greetings(conn_id)

    ###########################################################

    def _on_disconnect(self, conn_id):
        if conn_id in self._ident_by_conn:
            ident = self._ident_by_conn.pop(conn_id)
            del self._conn_by_ident[ident]

    ###########################################################

    def accept_protocol_version(self, remote_version):
        """
        You can override this.
        @return: bool
        """
        return remote_version == snakemq.version.PROTOCOL_VERSION

    ###########################################################

    def _on_packet_recv(self, conn_id, packet):
        try:
            parts = self.codec.decode(packet)

            # TODO format checking
            for (part_type, data) in parts:
                if part_type == PART_TYPE_PROTOCOL_VERSION:
                    if not self.accept_protocol_version(data):
                        self.log.warning("incompatible protocol version %i" % data)
                    self.transport.link.close(conn_id)
                elif part_type == PART_TYPE_IDENT:
                    self._ident_by_conn[conn_id] = data
                    self._conn_by_ident[data] = conn_id
                    self.log.info("ident %s:%s"  % (conn_id, data))
                else:
                    pass
                    # TODO queuing, routing

        except snakemq.exceptions.SnakeMQException, exc:
            self.log.error("conn=%s ident=%s %r" % 
                  (conn_id, self._ident_by_conn.get(conn_id), exc))
            self.on_error(conn_id, exc)
            self.transport.link.close(conn_id)

    ###########################################################

    def send_greetings(self, conn_id):
        self.transport.send_packet(conn_id, self.codec.encode([
              (PART_TYPE_PROTOCOL_VERSION, snakemq.version.PROTOCOL_VERSION),
              (PART_TYPE_IDENT, self.identifier)
            ]))

    ###########################################################

    def get_route(self, ident):
        """
        @return: conn_id
        @raise SnakeMQUnknownRoute:
        """
        try:
            return self._conn_by_ident[ident]
        except KeyError:
            raise snakemq.exceptions.SnakeMQUnknownRoute(ident)

    ###########################################################

    def send_message(self, ident, message, ttl=None, msg_type=MESSAGE_TYPE_SIGNAL):
        """
        @param ident: destination address
        @param message: any string
        @param ttl: time to live - C{datetime.DateTime} when the message
                    should be dropped or None
        @param msg_type:
        """
        conn_id = self.get_route(ident)
