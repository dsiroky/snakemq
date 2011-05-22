# -*- coding: utf-8 -*-
"""
Message container.

@author: David Siroky (siroky@dasir.cz)
@license: MIT License (see LICENSE.txt or
          U{http://www.opensource.org/licenses/mit-license.php})
"""

import uuid as uuid_module

###########################################################################
###########################################################################

FLAG_PERSISTENT = 0x1  # store to a persistent storage

MAX_UUID_LENGTH = 16

###########################################################################
###########################################################################

class Message(object):
    def __init__(self, data, uuid=None, ttl=0, flags=0):
        """
        @param data: (bytes) payload, B{must be immutable} (or deepcopied)
        @param uuid: (bytes) unique message identifier (implicitly generated)
        @param ttl: messaging TTL in seconds (integer or float)
        @param flags: combination of FLAG_*
        """
        assert type(data) == bytes
        assert uuid is None or (type(uuid) == bytes), uuid
        self.data = data
        self.uuid = (uuid or bytes(uuid_module.uuid4().bytes))[:MAX_UUID_LENGTH]
        self.ttl = float(ttl)
        self.flags = flags

    def __repr__(self):
        return "<%s id=%X uuid=%r ttl=%f len=%i>" % (
            self.__class__.__name__, id(self), self.uuid,
            self.ttl, len(self.data))
