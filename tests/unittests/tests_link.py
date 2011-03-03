#! -*- coding: utf-8 -*-

import threading

import snakemq.link

import utils

TEST_PORT = 40000

class TestLink(utils.TestCase):
    def run_srv_cli(self, server, client):
        link_server = snakemq.link.Link()
        link_server.add_listener(("", TEST_PORT))
        link_client = snakemq.link.Link()
        link_client.add_connector(("localhost", TEST_PORT))

        thr_server = threading.Thread(target=server, args=[link_server])
        thr_server.start()
        client(link_client)
        thr_server.join()

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
        self.assertEqual(len(link.handle_conn_refused.call_log), 1)
        link.del_connector(addr)
        self.assertEqual(len(link._socks_waiting_to_connect), 0)
        link.cleanup()
