#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
sys.path.insert(0, "../")

import logging
import time

import snakemq
import snakemq.link
import snakemq.packeter
import snakemq.messaging
from snakemq.message import Message
from snakemq.contrib import rpc

class A(object):
    def get_fo(self):
        return "xcv"

    @rpc.as_signal
    def mysignal(self):
        print "mysignal"

snakemq.init_logging()
logger = logging.getLogger("snakemq")
logger.setLevel(logging.DEBUG)

s = snakemq.link.Link()

s.add_listener(("", 4000))

tr = snakemq.packeter.Packeter(s)
m = snakemq.messaging.Messaging("boss", "", tr)
rh = snakemq.messaging.ReceiveHook(m)
srpc = rpc.RpcServer(rh)
srpc.register_object(A(), "abc")

s.loop(count=1000)
