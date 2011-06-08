#! -*- coding: utf-8 -*-
"""
@author: David Siroky (siroky@dasir.cz)
@license: MIT License (see LICENSE.txt or 
          U{http://www.opensource.org/licenses/mit-license.php})
"""

import unittest

##########################################################################
##########################################################################

class TestCase(unittest.TestCase):
    def shortDescription(self):
        return str(self)
