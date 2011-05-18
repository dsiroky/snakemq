# -*- coding: utf-8 -*-
"""
Link loop poll interruptor.

Read part must be nonblocking.
"""
# pylint: disable=C0103

import os
import socket
import errno

if os.name != "nt":
    import fcntl

############################################################################
############################################################################

class BellBase(object):
    def __repr__(self):
        return "<%s %x r=%r w=%r>" % (self.__class__.__name__,
                                      id(self), self.r, self.w)

############################################################################
############################################################################

class PosixBell(BellBase):
    def __init__(self):
        self.r, self.w = os.pipe()
        fcntl.fcntl(self.r, fcntl.F_SETFL, os.O_NONBLOCK)

    def write(self, buf):
        os.write(self.w, buf)

    def read(self, num):
        return os.read(self.r, num)

############################################################################
############################################################################

class WinBell(BellBase):
    """
    WinBell is no bell.
    """
    def __init__(self):
        r = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        r.setblocking(False)
        r.bind(("127.0.0.1", 0))
        r.listen(1)
        self.sw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sw.connect(r.getsockname())
        self.w = self.sw.fileno()
        self.sr = r.accept()[0]
        self.r = self.sr.fileno()
        r.close()

    def write(self, buf):
        self.sw.send(buf)

    def read(self, num):
        try:
            return self.sr.recv(num)
        except socket.error as exc:
            # emulate os.read exception
            if exc.errno == errno.WSAEWOULDBLOCK:
                new_exc = OSError()
                new_exc.errno = errno.EAGAIN
                raise new_exc
            else:
                raise

############################################################################
############################################################################

if os.name == "nt":
    Bell = WinBell
else:
    Bell = PosixBell
