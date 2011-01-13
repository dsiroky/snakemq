#! -*- coding: utf-8 -*-

import unittest
import threading
import time
import hashlib

import snakemq.link

TEST_PORT = 40000

class TestLink(unittest.TestCase):
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
                link.quit(blocking=False)

            link.on_recv = on_recv
            link.on_disconnect = on_disconnect
            link.loop(runtime=0.5)

        def client(link):
            def on_connect(conn_id):
                data = "abcd" * 1000000 # something "big enough"
                size = link.send(conn_id, data)
                container["sent"] = data[:size]
                link.close(conn_id)
                link.quit(blocking=False)

            link.on_connect = on_connect
            link.loop(runtime=0.5)

        self.run_srv_cli(server, client)
        self.assertEqual(container["sent"], "".join(container["received"]))
