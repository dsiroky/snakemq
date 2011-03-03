# -*- coding: utf-8 -*-
"""
Packet format: [4B size|payload], size is bytes count (in network order) of
all following packet data.

@author: David Siroky (siroky@dasir.cz)
"""
# TODO example or test for 2 links - send large data - sending should be interleaved

import logging
import struct
from collections import deque

from snakemq.buffers import StreamBuffer
from snakemq.exceptions import SnakeMQUnknownConnectionID, SnakeMQBadPacket

############################################################################
############################################################################

SEND_BLOCK_SIZE = 16 * 1024

BIN_SIZE_FORMAT = "!I" # network order 32-bit unsigned integer
SIZEOF_BIN_SIZE = struct.calcsize(BIN_SIZE_FORMAT)

############################################################################
############################################################################

def size_to_bin(size):
    # make the size a signed integer - negative integers might be
    # reserved for future extensions
    return struct.pack(BIN_SIZE_FORMAT, size)

#################################################################

def bin_to_size(buf):
    return struct.unpack(BIN_SIZE_FORMAT, buf)[0]

############################################################################
############################################################################

class ReceiveBuffer(StreamBuffer):
    def __init__(self):
        StreamBuffer.__init__(self)
        self.packet_size = None # cache for packet size by its header
  
    ############################################################

    def get_packets(self):
        """
        @return: list of fully received packets
        """
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

class Packeter(object):
    """
    Packets transport between nodes. Data of unfinished packet reception
    (closed connection) will be dropped. Packets over a single connection are
    serialized one by one.
    """

    def __init__(self, link):
        self.link = link
        self.log = logging.getLogger("snakemq.packeter")

        # callbacks
        self.on_connect = None #: C{func(conn_id)}
        self.on_disconnect = None #: C{func(conn_id)}
        self.on_packet_recv = None #: C{func(conn_id, packet)}
        #: C{func(conn_id, packet_id)}, just a signal when a packet was fully sent
        self.on_packet_sent = None
        self.on_error = None #: C{func(conn_id, exception)}

        self._connections = {} # conn_id:ConnectionInfo
        self._queued_packets = deque()
        self._last_packet_id = 0

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
        @return: packet id
        """
        try:
            conn = self._connections[conn_id]
        except KeyError:
            raise SnakeMQUnknownConnectionID(conn_id)

        self._last_packet_id += 1
        packet_id = self._last_packet_id

        buf = size_to_bin(len(buf)) + buf
        conn.send_buffer.put(buf)
        self._queued_packets.append((len(buf), packet_id))
        self._on_ready_to_send(conn_id)

        return packet_id

    ###########################################################
    ###########################################################

    def _on_connect(self, conn_id):
        self._connections[conn_id] = ConnectionInfo()
        if self.on_connect:
            self.on_connect(conn_id)

    ###########################################################

    def _on_disconnect(self, conn_id):
        # TODO signal unsent data and unreceived data
        del self._connections[conn_id]
        if self.on_disconnect:
            self.on_disconnect(conn_id)

    ###########################################################

    def _on_recv(self, conn_id, buf):
        recv_buffer = self._connections[conn_id].recv_buffer
        recv_buffer.put(buf)
        try:
            packets = recv_buffer.get_packets()
        except SnakeMQBadPacket, exc:
            self.log.error("conn=%s %r" % (conn_id, exc))
            if self.on_error:
                self.on_error(conn_id, exc)
            self.link.close(conn_id)
            return

        for packet in packets:
            self.log.debug("recv packet %s len=%i" % (conn_id, len(packet)))
            if self.on_packet_recv:
                self.on_packet_recv(conn_id, packet)

    ###########################################################

    def _on_ready_to_send(self, conn_id):
        conn = self._connections[conn_id]
        buf = conn.send_buffer.get(SEND_BLOCK_SIZE, False)
        if buf:
            sent_length = self.link.send(conn_id, buf)
            conn.send_buffer.cut(sent_length)
            while sent_length > 0:
                first, packet_id = self._queued_packets.popleft()
                if first <= sent_length:
                    if self.on_packet_sent:
                        self.on_packet_sent(conn_id, packet_id)
                else:
                    self._queued_packets.appendleft((first - sent_length,
                                                    packet_id))
                sent_length -= first
