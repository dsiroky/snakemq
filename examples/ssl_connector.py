#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.path.insert(0, "../")
import ssl

import logging

import snakemq
import snakemq.link

def on_connect(conn):
    sock = slink.get_socket_by_conn(conn)
    print conn, sock
    print sock.getpeercert()

snakemq.init_logging()
logger = logging.getLogger("snakemq")
logger.setLevel(logging.DEBUG)

sslcfg = snakemq.link.SSLConfig("testpeer.key",
                                "testpeer.crt",
                                ca_certs="testroot.crt",
                                cert_reqs=ssl.CERT_REQUIRED)

slink = snakemq.link.Link()
slink.add_connector(("localhost", 4000), ssl_config=sslcfg)

slink.on_connect.add(on_connect)

slink.loop()
