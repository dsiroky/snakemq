# -*- coding: utf-8 -*-
"""
Windows implementation of poll() does not accept file descriptors.
SnakeMQ need libev.
"""

import os
import socket
import random

############################################################################
############################################################################

class _Bell(object):
    def __repr__(self):
        return "<Bell %x r=%r w=%r>" % (id(self), self.r, self.w)

############################################################################
############################################################################

class PosixBell(object):
    def __init__(self):
        self.r, self.w = os.pipe()

    def write(self, buf):
        os.write(self.w, buf)

    def read(self, num):
        return os.read(self.r, num)

############################################################################
############################################################################

class WinBell(object):
    """
    WinBell is no bell.
    """
    def __init__(self):
        self.r = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.w = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def write(self, buf):
        pass

    def read(self, num):
        return "a"

############################################################################
############################################################################

if os.name == "nt":
    Bell = WinBell
else:
    Bell = PosixBell
