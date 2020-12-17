SnakeMQ is a small cross-platform Python library for easy and reliable
communication between hosts.

[![Build Status](https://travis-ci.org/dsiroky/snakemq.svg?branch=master)](https://travis-ci.org/dsiroky/snakemq)

# Features
  * pure Python, cross-platform
  * automatic reconnect
  * keep-alive for idle connections
  * reliable delivery - configurable message role and delivery timeout
  * persistent/transient queues
  * asynchronous - polling
  * symmetrical - single TCP connection for duplex communication
  * multiple storage options - SQLite, MongoDB, ...
  * brokerless - similar philosophy like [ZeroMQ](http://www.zeromq.org/)
  * additional modules - RPC, bandwidth throttling

Tested and working with Python versions: 2.6, 2.7, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, pypy, pypy3

# Homepage
<https://github.com/dsiroky/snakemq>

# Forum & bugs & issues
  * forum at [Google Groups](https://groups.google.com/forum/#!forum/snakemq)
  * bugtracking at [GitHub issues](https://github.com/dsiroky/snakemq/issues)

# Download
  * packages at [PyPI](http://pypi.python.org/pypi/snakeMQ)

# Documentation
<https://snakemq.readthedocs.io/en/latest/>

# Changelog
<https://snakemq.readthedocs.io/en/latest/changelog.html>

# Notes
Python 3.5 has broken SSL support.
