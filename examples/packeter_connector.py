#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.path.insert(0, "../")

import logging

import snakemq
import snakemq.link
import snakemq.packeter

def on_connect(conn):
    pktr.send_packet(conn, b"hello")

def on_recv(conn, packet):
    print("received from", conn, packet)

snakemq.init_logging()
logger = logging.getLogger("snakemq")
logger.setLevel(logging.DEBUG)

s = snakemq.link.Link()
s.add_connector(("localhost", 4000))

pktr = snakemq.packeter.Packeter(s)
pktr.on_connect.add(on_connect)
pktr.on_packet_recv.add(on_recv)

s.loop()
