#! -*- coding: utf-8 -*-

import os

from snakemq.queues import SqliteQueuesStorage, QueuesManager, Item

import utils

############################################################################
############################################################################

STORAGE_FILENAME = "/tmp/snakemq_testqueue.storage"

############################################################################
############################################################################

class TestQueue(utils.TestCase):
    def setUp(self):
        if os.path.isfile(STORAGE_FILENAME):
            os.unlink(STORAGE_FILENAME)
        storage = SqliteQueuesStorage(STORAGE_FILENAME)
        self.queues_manager = QueuesManager(storage)

    def tearDown(self):
        self.queues_manager.close()

    ##################################################################

    def test_simple_put_get(self):
        queue = self.queues_manager.get_queue("testqueue")
        queue.push(Item("a", "data a", 0))
        queue.push(Item("b", "data b", 0))
        self.assertEqual(len(queue), 2)
        self.assertEqual(queue.get().uuid, "a")
        self.assertEqual(queue.get().uuid, "a") # must be the same
        queue.pop()
        self.assertEqual(len(queue), 1)
        self.assertEqual(queue.get().uuid, "b")
        queue.pop()
        self.assertEqual(len(queue), 0)
        self.assertEqual(queue.get(), None)
