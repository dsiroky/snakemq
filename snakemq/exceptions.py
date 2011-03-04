# -*- coding: utf-8 -*-
"""
@author: David Siroky (siroky@dasir.cz)
"""

class SnakeMQException(Exception):
    pass

class SnakeMQBadPacket(SnakeMQException):
    """
    Received packet has wrong structure.
    """
    pass

class SnakeMQUnknownRoute(SnakeMQException):
    """
    Message destination/route unknown.
    """
    pass
