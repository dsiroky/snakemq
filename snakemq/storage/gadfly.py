# -*- coding: utf-8 -*-
"""
Gadfly queue storage.

:author: David Siroky (siroky@dasir.cz)
:license: MIT License (see LICENSE.txt)
"""

from __future__ import absolute_import

import os
from binascii import b2a_hex, a2b_hex

import gadfly

from snakemq.message import Message, MAX_UUID_LENGTH
from snakemq.messaging import MAX_IDENT_LENGTH
from snakemq.storage import QueuesStorageBase

###########################################################################
###########################################################################

class GadflyQueuesStorage(QueuesStorageBase):
    def __init__(self, directory, filename):
        if os.path.isfile(os.path.join(directory, filename + ".gfd")):
            self.conn = gadfly.gadfly(filename, directory)
            self.crs = self.conn.cursor()
        else:
            self.conn = gadfly.gadfly()
            self.conn.startup(filename, directory)
            self.crs = self.conn.cursor()
            self.create_structures()

    ####################################################

    def close(self):
        if self.crs:
            self.crs.close()
            self.crs = None
        if self.conn:
            self.conn.close()
            self.conn = None

    ####################################################

    def create_structures(self):
        # UUID is stored as hex
        self.crs.execute("""CREATE TABLE items (queue_name VARCHAR(%i),
                                                uuid VARCHAR(%i),
                                                data VARCHAR,
                                                ttl FLOAT,
                                                flags INTEGER)""" %
                                (MAX_IDENT_LENGTH, MAX_UUID_LENGTH * 2))
        self.conn.commit()

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
            uuid = a2b_hex(res[0])
            data = res[1]
            items.append(Message(uuid=uuid,
                                data=data,
                                ttl=res[2],
                                flags=res[3]))
        return items

    ####################################################

    def push(self, queue_name, item):
        self.crs.execute("""INSERT INTO items
                                (queue_name, uuid, data, ttl, flags)
                                VALUES (?, ?, ?, ?, ?)""",
                      (queue_name, b2a_hex(item.uuid), item.data,
                      item.ttl, item.flags))
        self.conn.commit()

    ####################################################

    def delete_items(self, items):
        for item in items:
            self.crs.execute("""DELETE FROM items WHERE uuid = ?""",
                          (b2a_hex(item.uuid),))
        self.conn.commit()

    ####################################################

    def delete_all(self):
        self.crs.execute("DELETE FROM items")
        self.conn.commit()

    ####################################################

    def update_items_ttl(self, items):
        for item in items:
            self.crs.execute("""UPDATE items SET ttl = ? WHERE uuid = ?""",
                              (item.ttl, b2a_hex(item.uuid)))
        self.conn.commit()
