# -*- coding: utf-8 -*-
"""
Simple callbacks helper.

@author: David Siroky (siroky@dasir.cz)
@license: MIT License (see LICENSE.txt or 
          U{http://www.opensource.org/licenses/mit-license.php})
"""

###########################################################################
###########################################################################

class CallbackPresent(Exception):
    pass

###########################################################################
###########################################################################

class Callback(object):
    def __init__(self, single=True):
        """
        @param single: if True then only a single callback function can be
                      assigned.
        """
        self.single = single
        self.callbacks = set()

    ####################################################

    def add(self, func):
        """
        Callback can be set only once.
        @raises CallbackPresent:
        """
        if (len(self.callbacks) > 0) and self.single:
            raise CallbackPresent()
        self.callbacks.add(func)

    ####################################################

    def __call__(self, *args, **kwargs):
        for callback in self.callbacks:
            callback(*args, **kwargs)

