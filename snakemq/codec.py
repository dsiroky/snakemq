# -*- coding: utf-8 -*-
"""
Packet serialization

@author: David Siroky (siroky@dasir.cz)
"""

import types
import struct
import socket

from snakemq.exceptions import SnakeMQBadPacket

##########################################################################
##########################################################################

BER_TYPE_INTEGER = 2
BER_TYPE_OCTET_STRING = 4
BER_TYPE_SEQUENCE = 16 | 0b100000

SIZEOF_INT = struct.calcsize("I")

##########################################################################
##########################################################################

class BaseCodec(object):
    @staticmethod
    def encode(value):
        raise NotImplementedError

    @staticmethod
    def decode(value):
        raise NotImplementedError

##########################################################################
##########################################################################

class BerCodec(BaseCodec):
    """
    Simple ad-hoc ASN.1/BER codec.
    """

    #########################################################

    @staticmethod
    def _gen_length(value):
        value_length = len(value)
        length = struct.pack("I", socket.htonl(value_length)).lstrip("\0")
        if value_length <= 0x80:
            return length
        else:
            return chr(0x80 + len(length)) + length

    #########################################################

    @staticmethod
    def _parse_length(value):
        """
        @return: (length, data_start_idx)
        """
        # skip BER type
        first = ord(value[1])
        value_length = len(value)

        if first > 0x80:
            l_of_l = first - 0x80
            if value_length < 2 + l_of_l: # type, l of l, length
                raise SnakeMQBadPacket("data too short")
                
            bin_length = ("\0" * (SIZEOF_INT - l_of_l) + # pad missing zeroes
                        value[2:2 + l_of_l])
            length = socket.ntohl(struct.unpack("I", bin_length)[0]) 
        else:
            length = first
            l_of_l = 0

        if value_length < 2 + l_of_l + length:
            raise SnakeMQBadPacket("data too short")

        return length, 2 + l_of_l

    #########################################################

    @staticmethod
    def encode(value):
        """
        Integers are supported only >= 0.
        """
        if isinstance(value, types.IntType):
            assert value >= 0
            value = struct.pack("I", socket.htonl(value))
            return chr(BER_TYPE_INTEGER) + BerCodec._gen_length(value) + value
        elif isinstance(value, types.StringTypes):
            return chr(BER_TYPE_OCTET_STRING) + BerCodec._gen_length(value) + value
        elif isinstance(value, (types.ListType, types.TupleType)):
            value = "".join([BerCodec.encode(item) for item in value])
            return chr(BER_TYPE_SEQUENCE) + BerCodec._gen_length(value) + value
        else:
            raise ValueError("unsupported type %r" % value)

    #########################################################

    @staticmethod
    def _decode(value):
        """
        @return: data, parsed_length
        """
        if len(value) < 2: # at least type and length
            raise SnakeMQBadPacket("data too short")

        value_type = ord(value[0])
        length, data_start = BerCodec._parse_length(value)
        value = value[data_start:]

        if value_type == BER_TYPE_INTEGER:
            data = socket.ntohl(struct.unpack("I", value[:length])[0])
        elif value_type == BER_TYPE_OCTET_STRING:
            data = value[:length]
        elif value_type == BER_TYPE_SEQUENCE:
            data = []
            _length = length
            while _length:
                item, item_length = BerCodec._decode(value[:_length])
                data.append(item)
                value = value[item_length:]
                _length -= item_length
        else:
            raise SnakeMQBadPacket("unsupported BER type %i" % value_type)

        return data, data_start + length

    #########################################################

    @staticmethod
    def decode(value):
        return BerCodec._decode(value)[0]

