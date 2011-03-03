#!/usr/bin/python
"""
High amount of parallel connections.
"""

import time
import logging
import sys
import os
import threading
import multiprocessing

sys.path.insert(0, "../..")

import snakemq
import snakemq.link
import snakemq.packeter
import snakemq.exceptions

###########################################################################

DATA_SIZE = 5
CLI_PROC_COUNT = 5
CLI_THR_COUNT = 5
COUNT = 100
RUNTIME = 3.0
PORT = 4000

###########################################################################

barrier = multiprocessing.Value("i", 0)

###########################################################################

def check_barrier():
    barrier.acquire()
    barrier.value += 1
    barrier.release()

    while barrier.value < CLI_PROC_COUNT * CLI_THR_COUNT + 1:
        pass

###########################################################################

def srv():
    s = snakemq.link.Link()
    container = {"start_time": time.time(), "count": 0}

    def on_connect(conn_id):
        print conn_id
        pass

    def on_packet_recv(conn_id, packet):
        assert len(packet) == DATA_SIZE
        container["count"] += 1
        if container["count"] >= COUNT * CLI_PROC_COUNT * CLI_THR_COUNT:
            s.stop()

    s.add_listener(("", PORT))
    tr = snakemq.packeter.Packeter(s)
    tr.on_connect = on_connect
    tr.on_packet_recv = on_packet_recv
    check_barrier()
    s.loop()
    s.cleanup()

    diff = time.time() - container["start_time"]
    count = container["count"]
    print count
    print "flow: %.02f MBps, %i pkts/s" % (DATA_SIZE * count / diff / 1024**2,
                count / diff)

###########################################################################

def cli():
    s = snakemq.link.Link()

    def on_connect(conn_id):
        for i in xrange(COUNT):
            try:
                tr.send_packet(conn_id, "x" * DATA_SIZE)
            except snakemq.exceptions.SnakeMQUnknownConnectionID:
                break
            #print "a",os.getpid()

    def on_disconnect(conn_id):
        s.stop()

    s.add_connector(("localhost", PORT))
    tr = snakemq.packeter.Packeter(s)
    tr.on_connect = on_connect
    tr.on_disconnect = on_disconnect
    check_barrier()
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

snakemq.init()

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
