#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.path.insert(0, "../")

import logging

import snakemq
import snakemq.link
import snakemq.packeter

def on_recv(conn, packet):
    print("received from", conn, packet)
    pktr.send_packet(conn, b"hi")

snakemq.init_logging()
logger = logging.getLogger("snakemq")
logger.setLevel(logging.DEBUG)

s = snakemq.link.Link()
s.add_listener(("", 4000))

pktr = snakemq.packeter.Packeter(s)
pktr.on_packet_recv.add(on_recv)

s.loop()
