#! -*- coding: utf-8 -*-
"""
@author: David Siroky (siroky@dasir.cz)
@license: MIT License (see LICENSE.txt or 
          U{http://www.opensource.org/licenses/mit-license.php})
"""

import os
import errno
import threading

import mock
from nose.tools import timed

import snakemq.link

import utils

#############################################################################
#############################################################################

TEST_PORT = 40000

LOOP_RUNTIME = 0.5
LOOP_RUNTIME_ASSERT = 0.3

#############################################################################
#############################################################################

class TestLink(utils.TestCase):
    def create_links(self):
        link_server = snakemq.link.Link()
        link_server.add_listener(("", TEST_PORT))
        link_client = snakemq.link.Link()
        link_client.add_connector(("localhost", TEST_PORT))
        return link_server, link_client

    ########################################################

    def run_srv_cli(self, server, client):
        link_server, link_client = self.create_links()

        thr_server = threading.Thread(target=server, args=[link_server], name="srv")
        thr_server.start()
        try:
            client(link_client)
        finally:
            thr_server.join()
            link_server.cleanup()
            link_client.cleanup()

    ########################################################

    @timed(LOOP_RUNTIME_ASSERT)
    def test_large_single_send(self):
        """
        Try a single raw send with large data and compare actually sent data
        with received data.
        """
        container = {"sent": None, "received": []}

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
                data = b"abcd" * 1000000 # something "big enough"
                size = link.send(conn_id, data)
                container["sent"] = data[:size]
                link.close(conn_id)
                link.stop()

            link.on_connect = on_connect
            link.loop(runtime=LOOP_RUNTIME)

        self.run_srv_cli(server, client)
        received = b"".join(container["received"])
        self.assertEqual(container["sent"], received,
                        (len(container["sent"]), len(received)))

    ########################################################

    def test_connector_cleanup(self):
        link = snakemq.link.Link()
        addr = link.add_connector(("localhost", TEST_PORT))
        link._connect(addr)
        link.del_connector(addr)
        self.assertEqual(len(link._socks_waiting_to_connect), 0)
        link.cleanup()

    ########################################################

    def test_connector_cleanup_connection_refused(self):
        link = snakemq.link.Link()
        link_wrapper = mock.Mock(wraps=link)
        with mock.patch.object(link, "handle_conn_refused",
                                link_wrapper.handle_conn_refused):
            addr = link.add_connector(("localhost", TEST_PORT))
            link._connect(addr)
            link.loop_pass(1.0)
        # just make sure that the connection failed
        self.assertEqual(link_wrapper.handle_conn_refused.call_count, 1)
        link.del_connector(addr)
        self.assertEqual(len(link._socks_waiting_to_connect), 0)
        link.cleanup()

    ########################################################

    def test_bell_pipe(self):
        link = snakemq.link.Link()
        buf = b"abc"
        link._poll_bell.write(buf)
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
        self.assertEqual(len(link.loop_pass(0)), 0)
        
        link.wakeup_poll()
        fds = link.loop_pass(1.0)
        self.assertEqual(len(fds), 1)
        self.assertEqual(fds[0][0], bell_rd)

        # make sure that the pipe is flushed after wakeup
        try:
            link._poll_bell.read(1)
        except OSError as exc:
            self.assertEqual(exc.errno, errno.EAGAIN)
        else:
            self.fail()

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

#############################################################################
#############################################################################

class TestLinkSSL(TestLink):
    def create_links(self):
        cfg = snakemq.link.SSLConfig("testkey.pem", "testcert.pem")
        link_server = snakemq.link.Link()
        link_server.add_listener(("", TEST_PORT), ssl_config=cfg)
        link_client = snakemq.link.Link()
        link_client.add_connector(("localhost", TEST_PORT), ssl_config=cfg)
        return link_server, link_client

#############################################################################
#############################################################################

class TestLinkSSLFailures(utils.TestCase):
    def test_handshake(self):
        pass # TODO

    def test_recv(self):
        pass # TODO

    def test_send(self):
        pass # TODO
