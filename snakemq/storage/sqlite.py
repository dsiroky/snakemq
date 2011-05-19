# -*- coding: utf-8 -*-
"""
SQLite queue storage.

@author: David Siroky (siroky@dasir.cz)
@license: MIT License (see LICENSE.txt)
"""

import sqlite3
from binascii import b2a_base64, a2b_base64

from snakemq.message import Message
from snakemq.storage import QueuesStorageBase

###########################################################################
###########################################################################

class SqliteQueuesStorage(QueuesStorageBase):
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
                                        data BLOB, ttl REAL, flags INTEGER)""")

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
            data = res[1]
            if type(data) != bytes:
                data = bytes(data)  # XXX python2 hack
            items.append(Message(uuid=a2b_base64(res[0]),
                                data=data,
                                ttl=res[2],
                                flags=res[3]))
        return items

    ####################################################

    def push(self, queue_name, item):
        with self.conn:
            self.crs.execute("""INSERT INTO items
                                    (queue_name, uuid, data, ttl, flags)
                                    VALUES (?, ?, ?, ?, ?)""",
                          (queue_name, b2a_base64(item.uuid), item.data,
                          item.ttl, item.flags))

    ####################################################

    def delete_items(self, items):
        # TODO use SQL operator "IN"
        with self.conn:
            for item in items:
                self.crs.execute("""DELETE FROM items WHERE uuid = ?""",
                              (b2a_base64(item.uuid),))

    ####################################################

    def update_items_ttl(self, items):
        with self.conn:
            for item in items:
                self.crs.execute("""UPDATE items SET ttl = ? WHERE uuid = ?""",
                          (item.ttl, b2a_base64(item.uuid)))
