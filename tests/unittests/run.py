#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: David Siroky (siroky@dasir.cz)
@license: MIT License (see LICENSE.txt or
          U{http://www.opensource.org/licenses/mit-license.php})
"""

import sys
import os

import nose

UTESTS_DIR = os.path.realpath(os.path.dirname(__file__))
sys.path.insert(0, os.path.realpath(os.path.join(UTESTS_DIR, "../..")))

#############################################################################
#############################################################################

def run():
    os.chdir(UTESTS_DIR)
    ret = nose.run(argv=["noserunner",
                  "--cover-erase", "--cover-package=snakemq"]
                  + sys.argv[1:])
    sys.exit(0 if ret else 1)

if __name__ == "__main__":
    run()
