# -*- coding: utf-8 -*-
"""
Queues and persistent storage. TTL is decreased only by the
disconnected time.  Queue manager "downtime" is not included.

@author: David Siroky (siroky@dasir.cz)
@license: MIT License (see LICENSE.txt or 
          U{http://www.opensource.org/licenses/mit-license.php})
"""

import time
import bisect
import sqlite3
from collections import defaultdict, deque

from snakemq.message import Message, FLAG_PERSISTENT

###########################################################################
###########################################################################
# queue
###########################################################################

class Queue(object):
    def __init__(self, name, manager):
        self.name = name
        self.manager = manager
        self.queue = []
        self.last_disconnect_absolute = None
        self.connected = False

        if manager.storage:
            self.load_persistent_data()
        self.disconnect()

    ####################################################

    def load_persistent_data(self):
        self.queue[:] = self.manager.storage.get_items(self.name)            

    ####################################################

    def connect(self):
        self.connected = True

        # remove outdated items and update TTL
        diff = time.time() - self.last_disconnect_absolute
        fresh_queue = []
        storage_update_ttls = []
        storage_to_delete = []
        for item in self.queue:
            item.ttl -= diff
            if item.ttl >= 0: # must include 0
                fresh_queue.append(item)
                if item.flags & FLAG_PERSISTENT:
                    storage_update_ttls.append(item)
            else:
                if item.flags & FLAG_PERSISTENT:
                    storage_to_delete.append(item)
        if self.manager.storage:
            self.manager.storage.update_items_ttl(storage_update_ttls)
            self.manager.storage.delete_items(storage_to_delete)
        self.queue[:] = fresh_queue

    ####################################################

    def disconnect(self):
        self.connected = False
        self.last_disconnect_absolute = time.time()

    ####################################################

    def push(self, item):
        if (item.ttl <= 0) and not self.connected:
            # do not queue already obsolete items
            return
        self.queue.append(item)
        if ((item.flags & FLAG_PERSISTENT) and (item.ttl > 0) and 
                self.manager.storage):
            # no need to store items with no TTL
            self.manager.storage.push(self.name, item)
        
    ####################################################

    def get(self):
        """
        Get first item but do not remove it. Use {Queue.pop()} to remove it
        e.g. after successful delivery. Items are always "fresh".
        @return: item or None if empty
        """
        # no need to test TTL because it is filtered in connect()
        if self.queue:
            return self.queue[0]
        else:
            return None

    ####################################################

    def pop(self):
        """
        Remove first item.
        @return: None
        """
        if not self.queue:
            return
        item = self.queue.pop(0)
        if (item.flags & FLAG_PERSISTENT) and self.manager.storage:
            self.manager.storage.delete_items([item])

    ####################################################

    def __len__(self):
        return len(self.queue)

###########################################################################
###########################################################################
# storage
###########################################################################

class QueuesStorage(object):
    def close(self):
        raise NotImplementedError

    def get_queues(self):
        """
        @return: list of queues names
        """
        raise NotImplementedError

    def get_items(self, queue_name):
        """
        @return: items of the queue
        """
        raise NotImplementedError

    def push(self, queue_name, item):
        raise NotImplementedError

    def delete_items(self, items):
        raise NotImplementedError

    def update_items_ttl(self, items):
        raise NotImplementedError

###########################################################################
###########################################################################

class MemoryQueuesStorage(QueuesStorage):
    """
    For testing purposes - B{THIS STORAGE IS NOT PERSISTENT.}
    """
    def __init__(self):
        self.queues = defaultdict(deque)  #: name:queue

    def close(self):
        pass

    def get_queues(self):
        return self.queues.keys()

    def get_items(self, queue_name):
        return self.queues[queue_name]

    def push(self, queue_name, item):
        self.queues[queue_name].append(item)

    def delete_items(self, items):
        for queue in self.queues.values():
            for item in items:
                try:
                    queue.remove(item)
                except ValueError:
                    pass

    def update_items_ttl(self, items):
        # TTLs are already updated by the caller
        pass

###########################################################################
###########################################################################

class SqliteQueuesStorage(QueuesStorage):
    def __init__(self, filename):
        self.filename = filename
        self.conn = sqlite3.connect(self.filename)
        self.crs = self.conn.cursor()
        self.test_format()
        self.sweep()

    ####################################################

    def close(self):
        if self.crs:
            self.crs.close()
            self.crs = None
        if self.conn:
            self.conn.close()
            self.conn = None

    ####################################################

    def test_format(self):
        """
        Make sure that the database file content is OK.
        """
        self.crs.execute("""SELECT count(1) FROM sqlite_master
                                  WHERE type='table' AND name='items'""")
        if self.crs.fetchone()[0] != 1:
            self.prepare_format()

    ####################################################

    def prepare_format(self):
        with self.conn:
            self.crs.execute("""CREATE TABLE items (queue_name TEXT, uuid TEXT,
                                        data TEXT, ttl REAL, flags INTEGER)""")

    ####################################################

    def sweep(self):
        with self.conn:
            self.crs.execute("""VACUUM""")

    ####################################################

    def get_queues(self):
        self.crs.execute("""SELECT queue_name FROM items GROUP BY queue_name""")
        return [r[0] for r in self.crs.fetchall()]

    ####################################################

    def get_items(self, queue_name):
        self.crs.execute("""SELECT uuid, data, ttl, flags FROM items
                                   WHERE queue_name = ?""",
                          (queue_name,))
        items = []
        for res in self.crs.fetchall():
            items.append(Message(uuid=res[0].decode("base64"), 
                                data=res[1],
                                ttl=res[2],
                                flags=res[3]))
        return items

    ####################################################

    def push(self, queue_name, item):
        with self.conn:
            self.crs.execute("""INSERT INTO items
                                    (queue_name, uuid, data, ttl, flags)
                                    VALUES (?, ?, ?, ?, ?)""",
                          (queue_name, item.uuid.encode("base64"), item.data,
                          item.ttl, item.flags))

    ####################################################

    def delete_items(self, items):
        # TODO use SQL operator "IN"
        with self.conn:
            for item in items:
                self.crs.execute("""DELETE FROM items WHERE uuid = ?""", 
                              (item.uuid.encode("base64"),))

    ####################################################

    def update_items_ttl(self, items):
        with self.conn:
            for item in items:
                self.crs.execute("""UPDATE items SET ttl = ? WHERE uuid = ?""",
                          (item.ttl, item.uuid.encode("base64")))

###########################################################################
###########################################################################
# manager
###########################################################################

class QueuesManager(object):
    def __init__(self, storage):
        """
        @param storage: None or persistent storage
        """
        self.storage = storage
        assert isinstance(storage, QueuesStorage)
        self.queues = {} #: name:Queue
        if storage:
            self.load_from_storage()

    ####################################################

    def load_from_storage(self):
        for queue_name in self.storage.get_queues():
            self.get_queue(queue_name)

    ####################################################

    def get_queue(self, queue_name):
        """
        @return: Queue
        """
        if queue_name in self.queues:
            queue = self.queues[queue_name]
        else:
            queue = Queue(queue_name, self)
            self.queues[queue_name] = queue
        return queue

    ####################################################

    def cleanup(self):
        """
        remove empty queues
        """
        for queue_name, queue in self.queues.items():
            if not queue:
                del self.queues[queue_name]

    ####################################################

    def close(self):
        """
        Delete queues and close persistent storage.
        """
        self.queues.clear()
        if self.storage:
            self.storage.close()
            self.storage = None

    ####################################################

    def collect_garbage(self):
        """
        Call this periodically to remove obsolete items and empty queues.
        """
        # TODO

    ####################################################

    def __len__(self):
        return len(self.queues)

