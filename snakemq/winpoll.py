# -*- coding: utf-8 -*-
"""
Stupid poll implementation for MS Win. Wrapper for select. Not working for file
descriptors.
"""

import select
import socket

select.EPOLLIN = 1
select.EPOLLOUT = 4
select.EPOLLERR = 8
select.EPOLLHUP = 16

class Epoll(object):
    def __init__(self):
        self.fds = {}

    def register(self, fd, eventmask=select.EPOLLIN | select.EPOLLOUT):
        if isinstance(fd, socket.socket):
            self.fds[fd] = eventmask

    def unregister(self, fd):
        del self.fds[fd]

    def modify(self, fd, eventmask):
        self.fds[fd] = eventmask

    def poll(self, timeout):
        """
        @param timeout: seconds
        """
        if len(self.fds) == 0:
            return []

        rlist = []
        wlist = []
        xlist = []
        for fd, mask in self.fds.items():
            if mask & select.EPOLLIN:
                rlist.append(fd.fileno())
            if mask & select.EPOLLOUT:
                wlist.append(fd.fileno())
            xlist.append(fd.fileno())
        
        rlist, wlist, xlist = select.select(rlist, wlist, xlist, timeout)

        res = {}
        for fd in rlist:
            res[fd] = res.get(fd, 0) | select.EPOLLIN
        for fd in wlist:
            res[fd] = res.get(fd, 0) | select.EPOLLOUT
        for fd in xlist:
            res[fd] = res.get(fd, 0) | select.EPOLLERR

        return res.items()
