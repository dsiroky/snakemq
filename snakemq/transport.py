# -*- coding: utf-8 -*-
"""
Packet format: [4B size|payload], size is bytes number of all following
the the first 4 bytes including the type byte.

@author: David Siroky (siroky@dasir.cz)
"""

import logging
import struct
import socket

from snakemq.buffers import StreamBuffer
from snakemq.exceptions import SnakeMQUnknownConnectionID, SnakeMQBadPacket

############################################################################
############################################################################

SEND_BLOCK_SIZE = 16 * 1024

SIZEOF_BIN_SIZE = struct.calcsize("I")

############################################################################
############################################################################

def _empty_func(*args, **kwargs):
    """
    Sink.
    """
    pass

#################################################################

def size_to_bin(size):
    # make the size a signed integer - negative integers might be
    # reserved for future extensions
    return struct.pack("I", socket.htonl(size))

#################################################################

def bin_to_size(buf):
    return socket.ntohl(struct.unpack("I", buf)[0])

############################################################################
############################################################################

class ReceiveBuffer(StreamBuffer):
    def __init__(self):
        StreamBuffer.__init__(self)
        self.packet_size = None # packet size by its header
  
    ############################################################

    def put(self, buf):
        """
        Add data to the buffer.
        @return: list of fully received packets
        """
        StreamBuffer.put(self, buf)

        packets = []
        while self.size:
            if self.packet_size is None:
                if self.size < SIZEOF_BIN_SIZE:
                    # wait for more data
                    break
                header = self.get(SIZEOF_BIN_SIZE, True)
                self.packet_size = bin_to_size(header)
                if self.packet_size < 0:
                    raise SnakeMQBadPacket("wrong packet header")
            else:
                if self.size < self.packet_size:
                    # wait for more data
                    break
                packets.append(self.get(self.packet_size, True))
                self.packet_size = None

        return packets

############################################################################
############################################################################

class ConnectionInfo(object):
    """
    Connection information and receive buffer handler.
    """
    def __init__(self):
        self.send_buffer = StreamBuffer()
        self.recv_buffer = ReceiveBuffer()

############################################################################
############################################################################

class Transport(object):
    """
    Packets between nodes. Data of unfinished packet reception will be dropped.

    @ivar on_connect: C{func(conn_id)}
    @ivar on_disconnect: C{func(conn_id)}
    @ivar on_packet_recv: C{func(conn_id, packet)}
    @ivar on_error: C{func(conn_id, exception)}
    """

    def __init__(self, link):
        self.link = link
        self.log = logging.getLogger("snakemq.transport")

        # callbacks
        self.on_connect = _empty_func
        self.on_disconnect = _empty_func
        self.on_packet_recv = _empty_func
        self.on_error = _empty_func

        self._connections = {} # conn_id:ConnectionInfo

        self.link.on_connect = self._on_connect
        self.link.on_disconnect = self._on_disconnect
        self.link.on_recv = self._on_recv
        self.link.on_ready_to_send = self._on_ready_to_send

    ###########################################################
    ###########################################################

    def send_packet(self, conn_id, buf):
        """
        Thread-safe.
        Queue data to be sent over the link.
        """
        with self.link.lock:
            try:
                conn = self._connections[conn_id]
            except KeyError:
                raise SnakeMQUnknownConnectionID(conn_id)
            conn.send_buffer.put(size_to_bin(len(buf)) + buf)
            self._on_ready_to_send(conn_id)

    ###########################################################
    ###########################################################

    def _on_connect(self, conn_id):
        self._connections[conn_id] = ConnectionInfo()
        self.on_connect(conn_id)

    ###########################################################

    def _on_disconnect(self, conn_id):
        # TODO signal unsent data and unreceived data
        del self._connections[conn_id]
        self.on_disconnect(conn_id)

    ###########################################################

    def _on_recv(self, conn_id, buf):
        try:
            packets = self._connections[conn_id].recv_buffer.put(buf)
        except SnakeMQBadPacket, exc:
            self.log.error("conn=%s %r" % (conn_id, exc))
            self.on_error(conn_id, exc)
            self.link.close(conn_id)
            return

        for packet in packets:
            self.log.debug("recv packet %s len=%i" % (conn_id, len(packet)))
            self.on_packet_recv(conn_id, packet)

    ###########################################################

    def _on_ready_to_send(self, conn_id):
        conn = self._connections[conn_id]
        buf = conn.send_buffer.get(SEND_BLOCK_SIZE, False)
        if buf:
            sent_length = self.link.send(conn_id, buf)
            conn.send_buffer.cut(sent_length)

