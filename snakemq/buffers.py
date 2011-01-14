# -*- coding: utf-8 -*-
"""
@author: David Siroky (siroky@dasir.cz)
"""

from collections import deque

############################################################################
############################################################################

MAX_BUF_CHUNK_SIZE = 64 * 1024

############################################################################
############################################################################

class StreamBuffer(object):
    # TODO add size limit + hysteresis to avoid often signalling

    def __init__(self):
        self.queue = deque()
        self.size = 0 # current size of the buffer

    ############################################################

    def __del__(self):
        self.queue.clear()

    ############################################################

    def get(self, size, cut):
        """
        Get from the left side.
        @param cut: True = remove returned data from buffer
        @return: max N-bytes from the buffer.
        """
        assert (((self.size > 0) and (len(self.queue) > 0)) 
             or ((self.size == 0) and (len(self.queue) == 0)))

        retbuf = []
        i = 0
        while size and self.queue:
            if cut:
                fragment = self.queue.popleft()
            else:
                fragment = self.queue[i]

            if len(fragment) > size:
                if cut:
                    # paste back the rest
                    self.queue.appendleft(fragment[size:])
                # get only needed
                fragment = fragment[:size]
                frag_len = size
            else:
                frag_len = len(fragment)
            
            retbuf.append(fragment)
            del fragment

            size -= frag_len
            if cut:
                self.size -= frag_len
            else:
                i += 1
                if i == len(self.queue):
                    break

        return "".join(retbuf)

    ############################################################

    def put(self, buf):
        """
        Add to the right side.
        """
        if not buf:
            # do not insert an empty string
            return

        self.size += len(buf)
        for i in range(len(buf) // MAX_BUF_CHUNK_SIZE + 1):
            chunk = buf[i * MAX_BUF_CHUNK_SIZE:(i + 1) * MAX_BUF_CHUNK_SIZE]
            if not chunk:
                break
            self.queue.append(chunk)
            del chunk
        del buf

    ############################################################

    def cut(self, size):
        """
        More efficient version of get(cut=True) and no data will be returned.
        """
        assert (((self.size > 0) and (len(self.queue) > 0)) 
             or ((self.size == 0) and (len(self.queue) == 0)))

        while size and self.queue:
            fragment = self.queue.popleft()

            if len(fragment) > size:
                # paste back the rest
                self.queue.appendleft(fragment[size:])
                frag_len = size
            else:
                frag_len = len(fragment)
            
            del fragment
            size -= frag_len
            self.size -= frag_len

    ############################################################

    def __len__(self):
        assert sum([len(item) for item in self.queue]) == self.size
        return self.size

