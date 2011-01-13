#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import unittest

sys.path.insert(0, "../..")

import snakemq

from tests_link import *
from tests_buffers import *

if __name__ == "__main__":
    snakemq.init()
    unittest.main()
