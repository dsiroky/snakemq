#!/usr/bin/env python
"""
High amount of parallel connections.

@author: David Siroky (siroky@dasir.cz)
@license: MIT License (see LICENSE.txt or 
          U{http://www.opensource.org/licenses/mit-license.php})
"""

import time
import logging
import sys
import os
import threading
import multiprocessing
import random

sys.path.insert(0, "../..")

import snakemq
import snakemq.link
import snakemq.packeter
import snakemq.exceptions

###########################################################################

DATA_SIZE = 5
CLI_PROC_COUNT = 10
CLI_THR_COUNT = 20
PACKETS_COUNT = 1000
PORT = 4000

###########################################################################

barrier = multiprocessing.Value("i", 0)

###########################################################################

def check_barrier():
    barrier.acquire()
    barrier.value += 1
    barrier.release()

    while barrier.value < CLI_PROC_COUNT * CLI_THR_COUNT:
        pass

###########################################################################

def srv():
    s = snakemq.link.Link()
    container = {"start_time": None, "cli_count": 0, "count": 0}

    def on_connect(conn_id):
        container["cli_count"] += 1
        if container["cli_count"] == CLI_PROC_COUNT * CLI_THR_COUNT:
            container["start_time"] = time.time()
            print "all connected"

    def on_packet_recv(conn_id, packet):
        assert len(packet) == DATA_SIZE
        container["count"] += 1
        if container["count"] >= PACKETS_COUNT * CLI_PROC_COUNT * CLI_THR_COUNT:
            s.stop()

    s.add_listener(("", PORT))
    tr = snakemq.packeter.Packeter(s)
    tr.on_connect = on_connect
    tr.on_packet_recv = on_packet_recv
    s.loop()
    s.cleanup()

    diff = time.time() - container["start_time"]
    count = container["count"]
    print "flow: %.02f MBps, total %i pkts, %i pkts/s" % (
          DATA_SIZE * count / diff / 1024**2, count, count / diff)

###########################################################################

def cli():
    s = snakemq.link.Link()

    def on_connect(conn_id):
        check_barrier()
        for i in xrange(PACKETS_COUNT):
            tr.send_packet(conn_id, "x" * DATA_SIZE)

    def on_disconnect(conn_id):
        s.stop()

    # listen queue on the server is short so the reconnect interval needs to be
    # short because all clients are trying to connect almost at the same time
    s.add_connector(("localhost", PORT), reconnect_interval=0.3)
    # spread the connections
    time.sleep(random.randint(0, 1000) / 1000.0)

    tr = snakemq.packeter.Packeter(s)
    tr.on_connect = on_connect
    tr.on_disconnect = on_disconnect
    s.loop()
    s.cleanup()

def cli_proc():
    thrs = []
    for i in range(CLI_THR_COUNT):
        thr = threading.Thread(target=cli)
        thrs.append(thr)
        thr.start()
    
    for thr in thrs:
        thr.join()

###########################################################################

# avoid logging overhead
logger = logging.getLogger("snakemq")
logger.setLevel(logging.ERROR)

procs = []
for i in range(CLI_PROC_COUNT):
    proc = multiprocessing.Process(target=cli_proc)
    procs.append(proc)
    proc.start()

srv()

for proc in procs:
    proc.join()
