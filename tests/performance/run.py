#!/usr/bin/python

import threading
import time
import logging
import sys

sys.path.insert(0, "../..")

import snakemq
import snakemq.link
import snakemq.transport

###########################################################################

DATA_SIZE = 300 * 1024 * 1024
PORT = 4000

###########################################################################

def srv(container):
    s = snakemq.link.Link()

    def on_packet_recv(self, packet):
        assert len(packet) == DATA_SIZE
        diff = time.time() - container["start_time"]
        print "flow: %.02f MBps" % (DATA_SIZE / diff / 1024**2)

    def on_disconnect(conn_id):
        s.quit(blocking=False)

    s.add_listener(("", PORT))
    tr = snakemq.transport.Transport(s)
    tr.on_packet_recv = on_packet_recv
    tr.on_disconnect = on_disconnect
    s.loop()
    s.cleanup()

###########################################################################

def cli(container):
    s = snakemq.link.Link()

    def on_connect(conn_id):
        container["start_time"] = time.time()
        tr.send_packet(conn_id, "x" * DATA_SIZE)

    def on_packet_sent(conn_id):
        s.quit(blocking=False)

    s.add_connector(("localhost", PORT))
    tr = snakemq.transport.Transport(s)
    tr.on_connect = on_connect
    tr.on_packet_sent = on_packet_sent
    s.loop()
    s.cleanup()

###########################################################################

snakemq.init()

# avoid logging overhead
logger = logging.getLogger("snakemq")
logger.setLevel(logging.ERROR)

container = {"start_time": None}

thr_srv = threading.Thread(target=srv, args=[container])
thr_srv.start()
thr_cli = threading.Thread(target=cli, args=[container])
thr_cli.start()
thr_srv.join()
thr_cli.join()
