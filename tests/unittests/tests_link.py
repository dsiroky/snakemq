#! -*- coding: utf-8 -*-

import os
import fcntl
import errno
import threading

import mocker

import snakemq.link

import utils

#############################################################################
#############################################################################

TEST_PORT = 40000

#############################################################################
#############################################################################

class TestLink(utils.TestCase):
    def run_srv_cli(self, server, client):
        link_server = snakemq.link.Link()
        link_server.add_listener(("", TEST_PORT))
        link_client = snakemq.link.Link()
        link_client.add_connector(("localhost", TEST_PORT))

        thr_server = threading.Thread(target=server, args=[link_server])
        try:
            thr_server.start()
            client(link_client)
            thr_server.join()
        finally:
            link_server.cleanup()
            link_client.cleanup()

    ########################################################

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
            link.loop(runtime=0.5)

        def client(link):
            def on_connect(conn_id):
                data = "abcd" * 1000000 # something "big enough"
                size = link.send(conn_id, data)
                container["sent"] = data[:size]
                link.close(conn_id)
                link.stop()

            link.on_connect = on_connect
            link.loop(runtime=0.5)

        self.run_srv_cli(server, client)
        self.assertEqual(container["sent"], "".join(container["received"]))

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
        link.handle_conn_refused = utils.FuncCallLogger(link.handle_conn_refused)
        addr = link.add_connector(("localhost", TEST_PORT))
        link._connect(addr)
        link.loop_iteration(1.0)
        # just make sure that the connection failed
        # TODO replace with mocker
        self.assertEqual(len(link.handle_conn_refused.call_log), 1)
        link.del_connector(addr)
        self.assertEqual(len(link._socks_waiting_to_connect), 0)
        link.cleanup()

    ########################################################

    def test_bell(self):
        """
        Bell must fire event only on wake up call. Otherwise it must block the
        poll.
        """
        link = snakemq.link.Link()
        bell_rd = link._poll_bell[0]
        
        # no event, no descriptor returned by poll
        self.assertEqual(len(link.loop_iteration(0)), 0)
        
        link.wakeup_poll()
        self.assertEqual(link.loop_iteration(0)[0][0], bell_rd)

        # make sure that the pipe is flushed after wakeup
        fcntl.fcntl(bell_rd, fcntl.F_SETFL, os.O_NONBLOCK)
        try:
            os.read(bell_rd, 1)
        except OSError, exc:
            self.assertEqual(exc.errno, errno.EAGAIN)
        else:
            self.fail()

    ########################################################

    def test_close_in_recv(self):
        """
        Calling link.close() in on_recv() must not cause any troubles.
        """
        def server(link):
            def on_connect(conn_id):
                link.send(conn_id, "a")

            def on_disconnect(conn_id):
                link.stop()

            link.on_connect = on_connect
            link.on_disconnect = on_disconnect
            link.loop(runtime=0.5)

        def client(link):
            def on_recv(conn_id, packet):
                link.close(conn_id) # <- close in recv

            def on_disconnect(conn_id):
                link.stop()

            link.on_recv = on_recv
            link.on_disconnect = on_disconnect

            # handle_close must be called only 1x
            link_mocker = mocker.Mocker()
            patched_link = link_mocker.patch(link)
            mocker.expect(patched_link.handle_close(mocker.ANY))\
                        .passthrough().count(1)
            with link_mocker:
                link.loop(runtime=0.5)

        self.run_srv_cli(server, client)
