#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: David Siroky (siroky@dasir.cz)
@license: MIT License (see LICENSE.txt or 
          U{http://www.opensource.org/licenses/mit-license.php})
"""

import sys
import os

import nose

sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "../..")))

#############################################################################
#############################################################################

if __name__ == "__main__":
    nose.run(argv=["noserunner",
                  "--cover-erase", "--cover-package=snakemq"]
                  + sys.argv[1:])
