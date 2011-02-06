# -*- coding: utf-8 -*-
"""
@author: David Siroky (siroky@dasir.cz)
"""

import select
import socket
import sys
import errno
import time
import bisect
import logging

from snakemq.exceptions import SnakeMQUnknownConnectionID

############################################################################
############################################################################

RECV_BLOCK_SIZE = 128 * 1024
RECONNECT_INTERVAL = 1.0

############################################################################
############################################################################

class Link(object):
    """
    Just a bare wire stream communication. Keeper of opened (TCP) connections.
    NOT thread-safe.
    """

    def __init__(self):
        self.poller = select.poll()
        self.log = logging.getLogger("snakemq.link")

        # callbacks
        self.on_connect = None #: C{func(conn_id)}
        self.on_disconnect = None #: C{func(conn_id)}
        self.on_recv = None #: C{func(conn_id, data)}
        self.on_ready_to_send = None #: C{func(conn_id)}, last send was successful
        self.on_loop_iteration = None #: C{func()}
        
        self._do_loop = False # False breaks the loop

        self._new_conn_id = 0 # counter for conn id generator

        self._sock_by_fd = {}
        self._conn_by_sock = {}
        self._sock_by_conn = {}

        self._listen_socks = {} # address:sock
        self._listen_socks_filenos = set()

        self._connectors = set()
        self._socks_connectors = {} # sock:address
        self._socks_waiting_to_connect = set()
        self._plannned_connections = [] # (when, address)
        self._reconnect_intervals = {} # address:interval

    ##########################################################

    def __del__(self):
        self.cleanup()

    ##########################################################

    def cleanup(self):
        """
        Close all sockets and remove all connectors and listeners.
        """
        assert not self._do_loop

        for address in list(self._connectors):
            self.del_connector(address)

        for address in self._listen_socks.keys():
            self.del_listener(address)

        for sock in self._sock_by_fd.values():
            self.handle_close(sock)

        # be sure that no memory is wasted
        assert len(self._sock_by_fd) == 0
        assert len(self._conn_by_sock) == 0
        assert len(self._sock_by_conn) == 0
        assert len(self._listen_socks) == 0
        assert len(self._listen_socks_filenos) == 0
        assert len(self._connectors) == 0
        assert len(self._socks_connectors) == 0
        assert len(self._socks_waiting_to_connect) == 0
        assert len(self._plannned_connections) == 0
        assert len(self._reconnect_intervals) == 0
        
    ##########################################################

    def add_connector(self, address, reconnect_interval=RECONNECT_INTERVAL):
        """
        This will not create an immediate connection. It just adds a connector
        to the pool.
        @param address: remote address
        @param reconnect_interval: reconnect interval in seconds
        """
        assert isinstance(reconnect_interval, (int, float))
        address = socket.gethostbyname(address[0]), address[1]
        if address in self._connectors:
            raise ValueError("connector '%r' already set", address)
        self._connectors.add(address)
        self._reconnect_intervals[address] = reconnect_interval
        self.plan_connect(0, address) # connect ASAP

    ##########################################################

    def del_connector(self, address):
        self._connectors.remove(address)
        del self._reconnect_intervals[address]
        # filter out address from plan
        self._plannned_connections = \
            [(when, _address)
                  for (when, _address) in self._plannned_connections
                  if _address != address]

    ##########################################################

    def add_listener(self, address):
        """
        Adds listener to the pool. This method is not blocking. Run only once.
        """
        address = socket.gethostbyname(address[0]), address[1]
        if address in self._listen_socks:
            raise ValueError("listener '%r' already set" % address)
        listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        fileno = listen_sock.fileno()
        listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listen_sock.setblocking(0)

        self._sock_by_fd[fileno] = listen_sock
        self._listen_socks[address] = listen_sock
        self._listen_socks_filenos.add(fileno)

        listen_sock.bind(address)
        listen_sock.listen(5)
        self.poller.register(listen_sock, select.POLLIN)

    ##########################################################

    def del_listener(self, address):
        sock = self._listen_socks.pop(address)
        fileno = sock.fileno()
        self._listen_socks_filenos.remove(fileno)
        del self._sock_by_fd[fileno]
        sock.close()

    ##########################################################

    def send(self, conn_id, data):
        """
        WARNING: this operation is non-blocking and if the remote side closes
        the connection then this call will be successful but the data will
        be lost. Always wait for C{Link.on_ready_to_send} to have confirmation
        about successful send.

        @return: number of bytes sent
        """
        sock = self.get_socket(conn_id)
        try:
            sent_length = sock.send(data)
        except socket.error, exc:
            err = exc.args[0]
            if err == errno.EWOULDBLOCK:
                return 0
            elif err in (errno.ECONNRESET, errno.ENOTCONN, errno.ESHUTDOWN,
                        errno.ECONNABORTED, errno.EPIPE, errno.EBADF):
                self.handle_close(sock)
                return 0
            else:
                raise

        self.poller.modify(sock, select.POLLIN | select.POLLOUT)
        return sent_length

    ##########################################################

    def get_socket(self, conn_id):
        """
        @raise SnakeMQUnknownConnectionID: when the C{conn_id} is nonexistent
        """
        try:
            return self._sock_by_conn[conn_id]
        except KeyError:
            raise SnakeMQUnknownConnectionID(conn_id)

    ##########################################################

    def close(self, conn_id):
        self.handle_close(self.get_socket(conn_id))

    ##########################################################

    def loop(self, poll_timeout=0.1, count=None, runtime=None):
        """
        Start the communication loop.
        @param poll_timeout: in seconds, should be less then the minimal
                              reconnect time
        @param count: count of poll events (not timeouts) or None
        @param runtime: max time of running loop in seconds (also depends
                        on the poll timeout) or None
        """
        poll_timeout *= 1000

        self._do_loop = True

        # plan fresh connects
        self.deal_connects()

        time_start = time.time()
        while (self._do_loop and
                (count is not 0) and 
                not ((runtime is not None) and
                      (time.time() - time_start > runtime))):
            is_event = self.loop_iteration(poll_timeout)
            if self.on_loop_iteration:
                self.on_loop_iteration()
            if is_event and (count is not None):
                count -= 1

        self._do_loop = False

    ##########################################################

    def stop(self):
        """
        Interrupt the loop. It doesn't perform a cleanup.
        """
        self._do_loop = False

    ##########################################################
    ##########################################################

    def new_connection_id(self, sock):
        """
        Create a virtual connection ID. This ID will be passed to C{on_*}
        functions. It is a unique identifier for every new connection during
        the instance's existence.
        """
        # NOTE e.g. pair address+port can't be used as a connection identifier
        # because it is not unique enough. It might be the same for 2 connections
        # distinct in time.

        self._new_conn_id += 1
        conn_id = "%ifd%i" % (self._new_conn_id, sock.fileno())
        self._conn_by_sock[sock] = conn_id
        self._sock_by_conn[conn_id] = sock
        return conn_id

    ##########################################################

    def del_connection_id(self, sock):
        conn_id = self._conn_by_sock.pop(sock)
        del self._sock_by_conn[conn_id]

    ##########################################################

    def plan_connect(self, when, address):
        item = (when, address)
        idx = bisect.bisect(self._plannned_connections, item)
        self._plannned_connections.insert(idx, item)
    
    ##########################################################

    def _connect(self, address):
        """
        Try to make an actual connection.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(0)

        self._sock_by_fd[sock.fileno()] = sock
        self._socks_connectors[sock] = address
        self._socks_waiting_to_connect.add(sock)
        
        err = sock.connect_ex(address)
        if err in (0, errno.EISCONN):
            self.handle_connect(sock)
        elif err not in (errno.EINPROGRESS, errno.EWOULDBLOCK):
            raise socket.error(err, errno.errorcode[err])

        self.poller.register(sock)

    ##########################################################

    def handle_connect(self, sock):
        self.poller.modify(sock, select.POLLIN)
        self._socks_waiting_to_connect.discard(sock)

        conn_id = self.new_connection_id(sock)
        self.log.info("connect %s %r" % (conn_id, sock.getpeername()))
        if self.on_connect:
            self.on_connect(conn_id)

    ##########################################################

    def handle_accept(self, sock):
        try:
            newsock, address = sock.accept()
        except socket.error, exc:
            self.log.error("accept %r: %r" % (sock, exc))
            return
        newsock.setblocking(0)
        self._sock_by_fd[newsock.fileno()] = newsock
        self.poller.register(newsock, select.POLLIN)

        conn_id = self.new_connection_id(newsock)
        self.log.info("accept %s %r" % (conn_id, address))
        if self.on_connect:
            self.on_connect(conn_id)

    ##########################################################

    def handle_recv(self, sock):
        buf = []
        do_close = False
        while True:
            try:
                fragment = sock.recv(RECV_BLOCK_SIZE)
                if not fragment:
                    do_close = True
                    break
                buf.append(fragment)
            except socket.error, exc:
                err = exc.args[0]
                if err == errno.EWOULDBLOCK:
                    break
                elif err in (errno.ECONNRESET, errno.ENOTCONN, errno.ESHUTDOWN,
                            errno.ECONNABORTED, errno.EPIPE, errno.EBADF):
                    do_close = True
                    break
                else:
                    raise

        if buf:
            buf = "".join(buf)
            conn_id = self._conn_by_sock[sock]
            self.log.debug("recv %s len=%i" % (conn_id, len(buf)))
            if self.on_recv:
                self.on_recv(conn_id, buf)
        
        if do_close:
            self.handle_close(sock)

    ##########################################################

    def handle_conn_refused(self, sock):
        self.poller.unregister(sock)
        del self._sock_by_fd[sock.fileno()]
        sock.close()

        address = self._socks_connectors.pop(sock)
        self.plan_connect(time.time() + self._reconnect_intervals[address],
                          address)

    ##########################################################

    def handle_close(self, sock):
        self.poller.unregister(sock)
        del self._sock_by_fd[sock.fileno()]
        sock.close()

        if sock in self._conn_by_sock:
            conn_id = self._conn_by_sock[sock]
            self.del_connection_id(sock)
            self.log.info("disconnect %s " % conn_id)
            if self.on_disconnect:
                self.on_disconnect(conn_id)

        if sock in self._socks_connectors:
            address = self._socks_connectors.pop(sock)
            interval = self._reconnect_intervals.get(address)
            if interval:
                self.plan_connect(time.time() + interval, address)

    ##########################################################

    def handle_ready_to_send(self, sock):
        self.poller.modify(sock, select.POLLIN)
        conn_id = self._conn_by_sock[sock]
        self.log.debug("ready to send " + conn_id)
        if self.on_ready_to_send:
            self.on_ready_to_send(conn_id)

    ##########################################################

    def handle_fd_mask(self, fd, mask):
        # socket might have been already discarded by the Link
        # so this iteration might be skipped
        if fd not in self._sock_by_fd:
            return
        sock = self._sock_by_fd[fd]

        if mask & (select.POLLERR | select.POLLHUP | select.POLLNVAL):
            if sock in self._socks_waiting_to_connect:
                self.handle_conn_refused(sock)
            else:
                self.handle_close(sock)
        else:
            if mask & select.POLLOUT:
                if sock in self._socks_waiting_to_connect:
                    self.handle_connect(sock)
                else:
                    self.handle_ready_to_send(sock)
            if mask & select.POLLIN:
                if fd in self._listen_socks_filenos:
                    self.handle_accept(sock)
                else:
                    self.handle_recv(sock)

    ##########################################################

    def loop_iteration(self, poll_timeout):
        """
        @return: number of sockets with performed operations
        """
        fds = self.poller.poll(poll_timeout)
        for fd, mask in fds:
            self.handle_fd_mask(fd, mask)
        self.deal_connects()
        return len(fds)

    ##########################################################

    def deal_connects(self):
        now = time.time()
        to_remove = 0
        for when, address in self._plannned_connections:
            reconnect_interval = self._reconnect_intervals[address]
            if (when <= now) or (when > now + reconnect_interval * 2):
                to_remove += 1
                self._connect(address)
            else:
                break

        if to_remove:
            del self._plannned_connections[:to_remove]

