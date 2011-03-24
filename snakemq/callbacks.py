# -*- coding: utf-8 -*-
"""
Simple callbacks helper.

@author: David Siroky (siroky@dasir.cz)
@license: MIT License (see LICENSE.txt or 
          U{http://www.opensource.org/licenses/mit-license.php})
"""

###########################################################################
###########################################################################

def empty(*args, **kwargs):
    """
    Dummy default callback.
    """
    return None

###########################################################################
###########################################################################

class CallbackPresent(Exception):
    pass

###########################################################################
###########################################################################

class Callback(object):
    def __init__(self):
        self.callbacks_by_obj = {}

    def __set__(self, instance, value):
        """
        Callback can be set only once.
        @raises CallbackPresent:
        """
        if instance in self.callbacks_by_obj:
            raise CallbackPresent()
        self.callbacks_by_obj[instance] = value

    def __get__(self, instance, owner):
        cb = self.callbacks_by_obj.get(instance)
        if cb:
            return cb
        else:
            return empty

    def __delete__(self, instance):
        try:
            del self.callbacks[instance]
        except KeyError:
            pass

