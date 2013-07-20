#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Perform many simultaneous RPC calls.

@author: David Siroky (siroky@dasir.cz)
@license: MIT License (see LICENSE.txt or 
          U{http://www.opensource.org/licenses/mit-license.php})
"""

import sys
sys.path.insert(0, "../../")

import threading
import multiprocessing
import time
import random

import snakemq.link
import snakemq.packeter
import snakemq.messaging
import snakemq.rpc

###########################################################################
###########################################################################

THREADS_COUNT = 20

###########################################################################
###########################################################################

class ServerClass(object):
    def f1(self):
        time.sleep(random.random() / 50.0)
        print "f1 ",

    def f2(self):
        time.sleep(random.random() / 50.0)
        print "f2 ",

    def f3(self):
        time.sleep(random.random() / 50.0)
        print "f3 ",

###########################################################################

def server():
    s = snakemq.link.Link()
    s.add_listener(("", 4000))
    tr = snakemq.packeter.Packeter(s)
    m = snakemq.messaging.Messaging("boss", "", tr)
    rh = snakemq.messaging.ReceiveHook(m)
    srpc = snakemq.rpc.RpcServer(rh)
    srpc.register_object(ServerClass(), "abc")
    s.loop()

###########################################################################
###########################################################################

def client_thread(proxy):
    time.sleep(1) # wait for server
    while True:
        (proxy.f1, proxy.f2, proxy.f3)[random.randint(0, 2)]()

###########################################################################

def client():
    s = snakemq.link.Link()
    s.add_connector(("localhost", 4000))
    tr = snakemq.packeter.Packeter(s)
    m = snakemq.messaging.Messaging("soldier", "", tr, None)
    rh = snakemq.messaging.ReceiveHook(m)
    crpc = snakemq.rpc.RpcClient(rh)
    proxy = crpc.get_proxy("boss", "abc")

    for i in range(THREADS_COUNT):
        thr = threading.Thread(target=client_thread, args=(proxy,))
        thr.setDaemon(True)
        thr.start()
    
    s.loop()

###########################################################################
###########################################################################

srv = multiprocessing.Process(target=server)
srv.start()

cli = multiprocessing.Process(target=client)
cli.start()

raw_input()
