#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.path.insert(0, "../")

import snakemq
import snakemq.link
import snakemq.packeter
import snakemq.messaging
import snakemq.message

def on_recv(conn, ident, message):
    print("received from", conn, ident, message)

s = snakemq.link.Link()
s.add_listener(("", 4000))

pktr = snakemq.packeter.Packeter(s)

m = snakemq.messaging.Messaging("xlistener", "", pktr)
m.on_message_recv.add(on_recv)

msg = snakemq.message.Message(b"hello", ttl=60)
m.send_message("xconnector", msg)

s.loop()
