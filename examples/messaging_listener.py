#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.path.insert(0, "../")

import logging

import snakemq
import snakemq.link
import snakemq.packeter
import snakemq.messaging
import snakemq.message

def on_recv(conn, ident, message):
    print("received from", conn, ident, message)

def on_drop(ident, message):
    print("message dropped", ident, message)

snakemq.init_logging()
logger = logging.getLogger("snakemq")
logger.setLevel(logging.DEBUG)

ssl_cfg = snakemq.link.SSLConfig("../tests/unittests/testkey.pem",
                                "../tests/unittests/testcert.pem")
s = snakemq.link.Link()
s.add_listener(("", 4000), ssl_config=ssl_cfg)

pktr = snakemq.packeter.Packeter(s)

m = snakemq.messaging.Messaging("xlistener", "", pktr)
m.on_message_recv.add(on_recv)
m.on_message_drop.add(on_drop)

msg = snakemq.message.Message(b"hello", ttl=60)
m.send_message("xconnector", msg)

s.loop()
