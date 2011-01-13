# -*- coding: utf-8 -*-
"""
@author: David Siroky (siroky@dasir.cz)
"""

import logging

import snakemq.codec
import snakemq.exceptions
import snakemq.version

############################################################################
############################################################################

PART_TYPE_PROTOCOL_VERSION = 0
PART_TYPE_IDENT = 1
PART_TYPE_MESSAGE = 2

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
    """
    @ivar on_error: C{func(conn_id, exception)}
    """

    def __init__(self, identifier, transport, codec=snakemq.codec.BerCodec()):
        self.identifier = identifier
        self.transport = transport
        assert isinstance(codec, snakemq.codec.BaseCodec)
        self.codec = codec
        self.log = logging.getLogger("snakemq.messaging")

        # callbacks
        self.on_error = _empty

        self._ident_by_conn = {}

        self.transport.on_connect = self._on_connect
        self.transport.on_disconnect = self._on_disconnect
        self.transport.on_packet_recv = self._on_packet_recv

    ###########################################################

    def _on_connect(self, conn_id):
        self.send_greetings(conn_id)

    ###########################################################

    def _on_disconnect(self, conn_id):
        if conn_id in self._ident_by_conn:
            del self._ident_by_conn[conn_id]

    ###########################################################

    def _on_packet_recv(self, conn_id, packet):
        try:
            parts = self.codec.decode(packet)
        except snakemq.exceptions.SnakeMQBadPacket, exc:
            self.log.error("conn=%s ident=%s %r" % 
                  (conn_id, self._ident_by_conn.get(conn_id), exc))
            self.on_error(conn_id, exc)
            self.transport.link.close(conn_id)
            return

        # TODO format checking
        for (part_type, data) in parts:
            if part_type == PART_TYPE_PROTOCOL_VERSION:
                if data != snakemq.version.PROTOCOL_VERSION:
                    self.log.warning("different protocol version %i" % data)
            elif part_type == PART_TYPE_IDENT:
                self._ident_by_conn[conn_id] = data
            else:
                pass
                # TODO

    ###########################################################

    def send_greetings(self, conn_id):
        self.transport.send_packet(conn_id, self.codec.encode([
              (PART_TYPE_PROTOCOL_VERSION, snakemq.version.PROTOCOL_VERSION),
              (PART_TYPE_IDENT, self.identifier)
            ]))
