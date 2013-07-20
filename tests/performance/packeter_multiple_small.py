#!/usr/bin/env python
"""
Send many small packets over a single connection.

@author: David Siroky (siroky@dasir.cz)
@license: MIT License (see LICENSE.txt or 
          U{http://www.opensource.org/licenses/mit-license.php})
"""

import time
import logging
import sys
import os
import cProfile as profile

sys.path.insert(0, "../..")

import snakemq
import snakemq.link
import snakemq.packeter

###########################################################################

DATA_SIZE = 5
COUNT = 100000
PORT = 4000

###########################################################################

def srv():
    s = snakemq.link.Link()
    container = {"start_time": None, "count": 0}

    def on_connect(conn_id):
        container["start_time"] = time.time()

    def on_packet_recv(conn_id, packet):
        assert len(packet) == DATA_SIZE
        container["count"] += 1

    def on_disconnect(conn_id):
        diff = time.time() - container["start_time"]
        print "flow: %.02f MBps, %i pkts/s" % (DATA_SIZE * COUNT / diff / 1024**2,
                    COUNT / diff)
        s.stop()

    s.add_listener(("", PORT))
    tr = snakemq.packeter.Packeter(s)
    tr.on_connect = on_connect
    tr.on_packet_recv = on_packet_recv
    tr.on_disconnect = on_disconnect
    s.loop()
    s.cleanup()
    assert container["count"] == COUNT

###########################################################################

def cli():
    s = snakemq.link.Link()
    container = {"count": 0}

    def on_connect(conn_id):
        for i in xrange(COUNT):
            tr.send_packet(conn_id, "x" * DATA_SIZE)

    def on_packet_sent(conn_id, packet_id):
        container["count"] += 1
        if container["count"] == COUNT:
            s.stop()

    s.add_connector(("localhost", PORT))
    tr = snakemq.packeter.Packeter(s)
    tr.on_connect = on_connect
    tr.on_packet_sent = on_packet_sent
    #profile.runctx("s.loop()", globals(), locals(), "/tmp/prof_cli.dat")
    s.loop()
    s.cleanup()

###########################################################################

# avoid logging overhead
logger = logging.getLogger("snakemq")
logger.setLevel(logging.ERROR)

if os.fork() > 0:
    srv()
else:
    cli()
