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
    pass

##########################################################################
##########################################################################

class FuncCallLogger(object):
    def __init__(self, func):
        self.func = func
        self.call_log = [] #: list of (args, kwargs, return_value)

    def __call__(self, *args, **kwargs):
        ret = self.func(*args, **kwargs)
        self.call_log.append((args, kwargs, ret))
        return ret
