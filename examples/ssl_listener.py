#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
sys.path.insert(0, "../")

import logging

import snakemq
import snakemq.link

snakemq.init_logging()
logger = logging.getLogger("snakemq")
logger.setLevel(logging.DEBUG)

sslcfg = snakemq.link.SSLConfig("testroot.key",
                                "testroot.crt")

s = snakemq.link.Link()
s.add_listener(("", 4000), ssl_config=sslcfg)

s.loop()
