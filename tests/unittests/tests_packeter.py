#! -*- coding: utf-8 -*-
"""
@author: David Siroky (siroky@dasir.cz)
@license: MIT License (see LICENSE.txt or 
          U{http://www.opensource.org/licenses/mit-license.php})
"""

import threading

import snakemq.link
import snakemq.packeter

import utils

#############################################################################
#############################################################################

TEST_PORT = 40000

LOOP_RUNTIME = 1.5

#############################################################################
#############################################################################

class TestPacketer(utils.TestCase):
    def create_links(self):
        link_server = snakemq.link.Link()
        link_server.add_listener(("", TEST_PORT))
        link_client = snakemq.link.Link()
        link_client.add_connector(("localhost", TEST_PORT))
        return link_server, link_client

    ########################################################

    def run_srv_cli(self, server, client):
        """
        Server is executed in a thread.
        """
        link_server, link_client = self.create_links()
        packeter_server = snakemq.packeter.Packeter(link=link_server)
        packeter_client = snakemq.packeter.Packeter(link=link_client)

        thr_server = threading.Thread(target=server, args=[link_server,
                                                          packeter_server])
        thr_server.start()
        try:
            client(link_client, packeter_client)
        finally:
            thr_server.join()
            link_server.cleanup()
            link_client.cleanup()

    ########################################################

    def test_multiple_small_packets(self):
        to_send = [b"ab", b"cde", b"fg", b"hijk"]
        container = {"received": []}

        def server(link, packeter):
            def on_recv(conn_id, packet):
                container["received"].append(packet)
                if len(container["received"]) == len(to_send):
                    link.close(conn_id)

            def on_disconnect(conn_id):
                link.stop()

            packeter.on_packet_recv = on_recv
            packeter.on_disconnect = on_disconnect
            link.loop(runtime=LOOP_RUNTIME)

        def client(link, packeter):
            def on_connect(conn_id):
                for data in to_send:
                    packeter.send_packet(conn_id, data)

            def on_disconnect(conn_id):
                link.stop()

            packeter.on_connect = on_connect
            packeter.on_disconnect = on_disconnect
            try:
                link.loop(runtime=LOOP_RUNTIME)
            except Exception as e:
                import traceback
                traceback.print_exc()

        self.run_srv_cli(server, client)
        self.assertEqual(to_send, container["received"])

    ########################################################

    def test_large_packet(self):
        to_send = b"abcd" * 200000 # something "big enough"
        assert len(to_send) > snakemq.packeter.SEND_BLOCK_SIZE
        container = {"received": None}

        def server(link, packeter):
            def on_recv(conn_id, packet):
                container["received"] = packet
                link.close(conn_id)

            def on_disconnect(conn_id):
                link.stop()

            packeter.on_packet_recv = on_recv
            packeter.on_disconnect = on_disconnect
            link.loop(runtime=LOOP_RUNTIME)

        def client(link, packeter):
            def on_connect(conn_id):
                packeter.send_packet(conn_id, to_send)

            def on_disconnect(conn_id):
                link.stop()

            packeter.on_connect = on_connect
            packeter.on_disconnect = on_disconnect
            link.loop(runtime=LOOP_RUNTIME)

        self.run_srv_cli(server, client)
        self.assertEqual(to_send, container["received"],
                        (len(to_send), len(container["received"])))

#############################################################################
#############################################################################

class TestPacketerSSL(TestPacketer):
    def create_links(self):
        cfg = snakemq.link.SSLConfig("testkey.pem", "testcert.pem")
        link_server = snakemq.link.Link()
        link_server.add_listener(("", TEST_PORT), ssl_config=cfg)
        link_client = snakemq.link.Link()
        link_client.add_connector(("localhost", TEST_PORT), ssl_config=cfg)
        return link_server, link_client

