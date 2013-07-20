#!/usr/bin/env python
"""
Send a single large packet over a single connection.

@author: David Siroky (siroky@dasir.cz)
@license: MIT License (see LICENSE.txt or 
          U{http://www.opensource.org/licenses/mit-license.php})
"""

import time
import logging
import sys
from multiprocessing import Process

sys.path.insert(0, "../..")

import snakemq
import snakemq.link
import snakemq.packeter
import snakemq.throttle

###########################################################################

DATA_SIZE = 1 * 1024 * 1024
PORT = 4000

###########################################################################

def srv():
    s = snakemq.link.Link()
    container = {"start_time": None}

    def on_connect(conn_id):
        container["start_time"] = time.time()

    def on_packet_recv(conn_id, packet):
        assert len(packet) == DATA_SIZE
        diff = time.time() - container["start_time"]
        print "flow: %.02f MBps" % (DATA_SIZE / diff / 1024**2)

    def on_disconnect(conn_id):
        s.stop()

    s.add_listener(("", PORT))
    tr = snakemq.packeter.Packeter(s)
    tr.on_connect = on_connect
    tr.on_packet_recv = on_packet_recv
    tr.on_disconnect = on_disconnect
    s.loop()
    s.cleanup()

###########################################################################

def cli():
    s = snakemq.link.Link()

    def on_connect(conn_id):
        tr.send_packet(conn_id, "x" * DATA_SIZE)

    def on_packet_sent(conn_id, packet_id):
        s.stop()

    s.add_connector(("localhost", PORT))
    throttle = snakemq.throttle.Throttle(s, 100000)
    tr = snakemq.packeter.Packeter(throttle)
    tr.on_connect = on_connect
    tr.on_packet_sent = on_packet_sent
    s.loop()
    s.cleanup()

###########################################################################

# avoid logging overhead
logger = logging.getLogger("snakemq")
logger.setLevel(logging.ERROR)

thr_srv = Process(target=srv)
thr_srv.start()
thr_cli = Process(target=cli)
thr_cli.start()
thr_srv.join()
thr_cli.join()
