#! -*- coding: utf-8 -*-
"""
@author: David Siroky (siroky@dasir.cz)
@license: MIT License (see LICENSE.txt or
          U{http://www.opensource.org/licenses/mit-license.php})
"""

try:
    import builtins
except ImportError:
    import __builtin__ as builtins
import os
import errno
import threading
import socket
import sys

import mock
from nose.tools import timed

import snakemq.link
import snakemq.poll

import utils

#############################################################################
#############################################################################

TEST_PORT = 40000

LOOP_RUNTIME = 2.5
LOOP_RUNTIME_ASSERT = 2.2  # SSL needs more time, this should be fine

#############################################################################
#############################################################################

has_ssl = sys.version_info < (3, 5)

#############################################################################
#############################################################################

class TestConnector(utils.TestCase):
    def setUp(self):
        self.link = snakemq.link.Link()

    ########################################################

    def tearDown(self):
        self.link.cleanup()

    ########################################################

    def test_connector_cleanup(self):
        addr = self.link.add_connector(("localhost", TEST_PORT))
        self.link.connect(addr)
        self.link.del_connector(addr)
        self.assertEqual(len(self.link._socks_waiting_to_connect), 0)

    ########################################################

    def test_connection_refused(self):
        addr = self.link.add_connector(("localhost", TEST_PORT))
        link_w = mock.Mock(wraps=self.link)
        with mock.patch.object(self.link, "handle_conn_refused",
                                link_w.handle_conn_refused):
            with mock.patch.object(self.link, "connect",
                                link_w.connect):
                if not self.link.connect(addr):
                    # if the refusal did not happen in connect then it must
                    # happen in the next poll round
                    # MS Windows has long poll/select reaction (aroung 1s)
                    self.link.poll(2)
        # just make sure that the connection failed
        self.assertEqual(link_w.connect.call_count, 1)
        self.assertEqual(link_w.handle_conn_refused.call_count, 1)
        self.assertEqual(len(self.link._socks_waiting_to_connect), 0)
        self.link.del_connector(addr)

#############################################################################
#############################################################################

class TestLink(utils.TestCase):
    def setUp(self):
        self.link_server, self.link_client = self.create_links()

    def tearDown(self):
        self.link_server.cleanup()
        self.link_client.cleanup()

    ########################################################

    def create_links(self):
        link_server = snakemq.link.Link()
        link_server.add_listener(("", TEST_PORT))
        link_client = snakemq.link.Link()
        link_client.add_connector(("localhost", TEST_PORT))
        return link_server, link_client

    ########################################################

    def run_srv_cli(self, server, client):
        thr_server = threading.Thread(target=server, args=[self.link_server],
                                      name="srv")
        thr_server.start()
        try:
            client(self.link_client)
        finally:
            thr_server.join()

    ########################################################

    @timed(LOOP_RUNTIME_ASSERT)
    def test_large_single_send(self):
        """
        Try a single raw send with large data and compare actually sent data
        with received data.
        """
        container = {"sent": None, "received": []}
        data_to_send = b"abcd" * 200000 # something "big enough" to be split

        def server(link):
            def on_recv(conn_id, data):
                container["received"].append(data)
            def on_disconnect(conn_id):
                link.stop()

            link.on_recv = on_recv
            link.on_disconnect = on_disconnect
            link.loop(runtime=LOOP_RUNTIME)

        def client(link):
            def on_connect(conn_id):
                link.send(conn_id, data_to_send)
            def on_ready_to_send(conn_id, last_send_size):
                container["sent"] = data_to_send[:last_send_size]
                link.close(conn_id)
                link.stop()

            link.on_connect = on_connect
            link.on_ready_to_send = on_ready_to_send
            link.loop(runtime=LOOP_RUNTIME)

        self.run_srv_cli(server, client)
        received = b"".join(container["received"])
        self.assertEqual(container["sent"], received,
                        (len(container["sent"]), len(received)))

    ########################################################

    @timed(LOOP_RUNTIME_ASSERT)
    def test_close_in_recv(self):
        """
        Calling link.close() in on_recv() must not cause any troubles.
        """
        def server(link):
            def on_connect(conn_id):
                link.send(conn_id, b"a")

            def on_disconnect(conn_id):
                link.stop()

            link.on_connect = on_connect
            link.on_disconnect = on_disconnect
            link.loop(runtime=LOOP_RUNTIME)

        def client(link):
            def on_recv(conn_id, packet):
                link.close(conn_id) # <- close in recv

            def on_disconnect(conn_id):
                link.stop()

            link.on_recv = on_recv
            link.on_disconnect = on_disconnect

            # handle_close must be called only 1x
            link_wrapper = mock.Mock(wraps=link)
            with mock.patch.object(link, "handle_close",
                                    link_wrapper.handle_close):
                link.loop(runtime=LOOP_RUNTIME)
            self.assertEqual(link_wrapper.handle_close.call_count, 1)

        self.run_srv_cli(server, client)

    ########################################################

    def test_recv_on_closed_socket(self):
        sock = snakemq.link.LinkSocket()
        # this must not raise an exception
        self.link_server.handle_recv(sock)

#############################################################################
#############################################################################

class TestLinkSSL(TestLink):
    __test__ = has_ssl

    def create_links(self):
        cfg = snakemq.link.SSLConfig("testkey.pem", "testcert.pem")
        link_server = snakemq.link.Link()
        link_server.add_listener(("", TEST_PORT), ssl_config=cfg)
        link_client = snakemq.link.Link()
        link_client.add_connector(("localhost", TEST_PORT), ssl_config=cfg)
        return link_server, link_client

    ########################################################

    def test_ssl_handshake_none_sslobj(self):
        link = snakemq.link.Link()
        sock = mock.Mock()
        sock.sock._sslobj = None
        link._in_ssl_handshake.add(sock)
        link.poller = mock.Mock()
        self.assertEqual(link.ssl_handshake(sock), snakemq.link.SSL_HANDSHAKE_FAILED)
        self.assertNotIn(sock, link._in_ssl_handshake)

    ########################################################

    def test_failed_handshake_cleanup(self):
        link = snakemq.link.Link()
        sock = mock.Mock()
        sock.sock._sslobj = mock.Mock()  # anything but None
        sock.sock.do_handshake.side_effect = socket.error()
        link._in_ssl_handshake.add(sock)
        def handle_close(sock):
            # during handle_close() the socket must be still have
            # the "handshake flag"
            self.assertIn(sock, link._in_ssl_handshake)
        link.handle_close = mock.Mock(wraps=handle_close)
        link.poller = mock.Mock()
        self.assertEqual(link.ssl_handshake(sock), snakemq.link.SSL_HANDSHAKE_FAILED)
        self.assertNotIn(sock, link._in_ssl_handshake)
        self.assertEqual(link.handle_close.call_count, 1)

#############################################################################
#############################################################################

"""
class TestLinkSSLFailures(utils.TestCase):
    def test_handshake(self):
        pass # TODO

    def test_recv(self):
        pass # TODO

    def test_send(self):
        pass # TODO
"""

#############################################################################
#############################################################################

class TestBell(utils.TestCase):
    def test_bell_pipe(self):
        link = snakemq.link.Link()
        buf = b"abc"
        link._poll_bell.write(buf)
        link._poll_bell.wait(0.2)
        self.assertEqual(link._poll_bell.read(len(buf)), buf)

    ########################################################

    def test_bell_wakeup(self):
        """
        Bell must fire event only on wake up call. Otherwise it must block the
        poll.
        """
        link = snakemq.link.Link()
        bell_rd = link._poll_bell.r

        # no event, no descriptor returned by poll
        self.assertEqual(len(link.poll(0)), 0)

        link.wakeup_poll()
        fds = link.poll(1.0)
        self.assertEqual(len(fds), 1)
        self.assertEqual(fds[0][0], bell_rd)

        # make sure that the pipe is flushed after wakeup
        try:
            link._poll_bell.read(1)
        except OSError as exc:
            self.assertEqual(exc.errno, errno.EAGAIN)
        else:
            self.fail()

#############################################################################
#############################################################################

class TestSelectPoll(utils.TestCase):
    """
    tests for snakemq.poll.SelectPoll
    """

    def test_socket_to_filedescriptor(self):
        """
        issue #1
        """
        socket_to_fd = snakemq.poll.SelectPoll._socket_to_fd
        has_long = hasattr(builtins, "long")
        if has_long:
            valid_classes = (int, long)
        else:
            # python3 does not have long
            valid_classes = int
        self.assertIsInstance(socket_to_fd(int(1)), valid_classes)
        if has_long:
            self.assertIsInstance(socket_to_fd(long(1)), valid_classes)
        self.assertIsInstance(socket_to_fd(socket.socket()), valid_classes)
