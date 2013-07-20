#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.path.insert(0, "../")

import threading
import time
import logging

import snakemq
import snakemq.link
import snakemq.packeter
import snakemq.messaging
import snakemq.queues
import snakemq.rpc

class B(object):
    def wer(self):
        print("wer")

def f():
    time.sleep(1)
    c = None
    while True:
        if list(m._conn_by_ident.keys()):
            c = 1
        if c:
            try:
                print(proxy.get_fo())
            except Exception as exc:
                print("remote traceback", str(exc.__remote_traceback__))
            s.stop()
        time.sleep(2)

snakemq.init_logging()

logger = logging.getLogger("snakemq")
logger.setLevel(logging.DEBUG)

s = snakemq.link.Link()
s.add_connector(("localhost", 4000))

tr = snakemq.packeter.Packeter(s)

m = snakemq.messaging.Messaging("soldier", "", tr, None)

t = threading.Thread(target=f)
t.setDaemon(1)
t.start()

rh = snakemq.messaging.ReceiveHook(m)

crpc = snakemq.rpc.RpcClient(rh)
srpc = snakemq.rpc.RpcServer(rh)
srpc.register_object(B(), "b")

proxy = crpc.get_proxy("boss", "abc")

proxy.mysignal.as_signal(10)
proxy.mysignal()

s.loop()
