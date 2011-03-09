# -*- coding: utf-8 -*-
"""
@author: David Siroky (siroky@dasir.cz)
"""

class SnakeMQException(Exception):
    pass

class SnakeMQBrokenFormat(SnakeMQException):
    pass

class SnakeMQBrokenPacket(SnakeMQBrokenFormat):
    """
    Received packet has wrong structure.
    """
    pass

class SnakeMQBrokenMessage(SnakeMQBrokenFormat):
    """
    Received message has wrong structure.
    """
    pass

class SnakeMQIncompatibleProtocol(SnakeMQException):
    """
    Remote side has incompatible protocol version.
    """
    pass

class SnakeMQUnknownRoute(SnakeMQException):
    """
    Message destination/route unknown.
    """
    pass
