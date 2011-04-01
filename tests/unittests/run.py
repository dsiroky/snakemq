#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: David Siroky (siroky@dasir.cz)
@license: MIT License (see LICENSE.txt or 
          U{http://www.opensource.org/licenses/mit-license.php})
"""

import sys
import unittest

sys.path.insert(0, "../..")

import snakemq

from tests_link import *
from tests_packeter import *
from tests_buffers import *
from tests_queues import *
from tests_messaging import *

#############################################################################
#############################################################################

if __name__ == "__main__":
    unittest.main()
