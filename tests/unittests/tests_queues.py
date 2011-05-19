#! -*- coding: utf-8 -*-
"""
@author: David Siroky (siroky@dasir.cz)
@license: MIT License (see LICENSE.txt or 
          U{http://www.opensource.org/licenses/mit-license.php})
"""

import os
import warnings

import mock

from snakemq.queues import QueuesManager
from snakemq.storage import MemoryQueuesStorage 
from snakemq.storage.sqlite import SqliteQueuesStorage
from snakemq.message import Message, FLAG_PERSISTENT

try:
    from snakemq.storage.mongodb import MongoDbQueuesStorage
    has_mongodb = True
except ImportError:
    has_mongodb = False
    warnings.warn("missing MondoDB support", RuntimeWarning)

import utils

############################################################################
############################################################################

class TestQueue(utils.TestCase):
    def setUp(self):
        self.storage = MemoryQueuesStorage()
        self.queues_manager = QueuesManager(self.storage)

    def tearDown(self):
        self.queues_manager.close()

    ##################################################################

    def queue_manager_restart(self):
        self.queues_manager.close()
        self.queues_manager = QueuesManager(self.storage)

    ##################################################################

    def test_simple_put_get(self):
        """
        Few puts, few gets, no TTL or persistency
        """
        queue = self.queues_manager.get_queue("testqueue")
        queue.connect()
        queue.push(Message(b"data a", "a"))
        queue.push(Message(b"data b", "b"))
        self.assertEqual(len(queue), 2)
        self.assertEqual(queue.get().uuid, "a")
        self.assertEqual(queue.get().uuid, "a") # must be the same
        queue.pop()
        self.assertEqual(len(queue), 1)
        self.assertEqual(queue.get().uuid, "b")
        queue.pop()
        self.assertEqual(len(queue), 0)
        self.assertEqual(queue.get(), None)

    ##################################################################

    def test_ttl(self):
        """
        Push 2 items, one will expire on connect.
        """
        queue = self.queues_manager.get_queue("testqueue")
        with mock.patch("time.time") as time_mock:
            time_results = iter([0, 3])
            time_mock.side_effect = lambda: next(time_results)
            queue.disconnect()
            queue.push(Message(b"data a", "a", ttl=1))
            queue.push(Message(b"data b", "b", ttl=5))
            queue.connect()
            self.assertEqual(len(queue), 1)
            self.assertEqual(queue.get().uuid, "b")

    ##################################################################

    def test_zero_ttl(self):
        """
        Push item with ttl=0 into a connected or disconnected queue.
        """
        queue = self.queues_manager.get_queue("testqueue")

        # disconnected
        queue.push(Message(b"data a", "a", ttl=0))
        self.assertEqual(len(queue), 0)

        queue.connect()
        queue.push(Message(b"data a", "a", ttl=0))
        self.assertEqual(len(queue), 1)

    ##################################################################

    def test_persistency(self):
        """
        Without TTL.
        """
        queue = self.queues_manager.get_queue("testqueue")
        queue.connect()
        queue.push(Message(b"data a", "a", ttl=1, flags=FLAG_PERSISTENT))
        queue.push(Message(b"data b", "b"))
        queue.push(Message(b"data c", "c", ttl=1, flags=FLAG_PERSISTENT))
        self.assertEqual(len(queue), 3)
        stored_items = self.queues_manager.storage.get_items("testqueue")
        self.assertEqual(len(stored_items), 2)
        self.assertEqual(stored_items[0].uuid, "a")
        self.assertEqual(stored_items[1].uuid, "c")

        # remove "a"
        queue.pop()
        stored_items = self.queues_manager.storage.get_items("testqueue")
        self.assertEqual(len(stored_items), 1)
        self.assertEqual(stored_items[0].uuid, "c")

        # remove "b", "c" remains
        queue.pop()
        stored_items = self.queues_manager.storage.get_items("testqueue")
        self.assertEqual(len(stored_items), 1)

    ##################################################################

    def test_persistency_restart(self):
        """
        Test of persistent items load.
        """
        queue1 = self.queues_manager.get_queue("testqueue1")
        queue1.connect()
        queue1.push(Message(b"data a", "a", ttl=1, flags=FLAG_PERSISTENT))
        queue1.push(Message(b"data b", "b", ttl=1, flags=FLAG_PERSISTENT))
        queue1.push(Message(b"data c", "c", ttl=1, flags=FLAG_PERSISTENT))
        queue2 = self.queues_manager.get_queue("testqueue2")
        queue2.connect()
        queue2.push(Message(b"data d", "d", ttl=1, flags=FLAG_PERSISTENT))
        queue2.push(Message(b"data e", "e", ttl=1, flags=FLAG_PERSISTENT))

        self.queue_manager_restart()

        self.assertEqual(len(self.queues_manager), 2)
        queue = self.queues_manager.get_queue("testqueue1")
        self.assertEqual(len(queue), 3)
        self.assertEqual(queue.get().uuid, "a")
        queue = self.queues_manager.get_queue("testqueue2")
        self.assertEqual(len(queue), 2)
        self.assertEqual(queue.get().uuid, "d")

    ##################################################################

    def test_persistency_ttl(self):
        queue = self.queues_manager.get_queue("testqueue")
        queue.connect()
        queue.push(Message(b"data a", "a", ttl=1, flags=FLAG_PERSISTENT))
        queue.push(Message(b"data b", "b"))
        queue.push(Message(b"data c", "c", ttl=5, flags=FLAG_PERSISTENT))
        self.assertEqual(len(queue), 3)

        self.queue_manager_restart()
        queue = self.queues_manager.get_queue("testqueue")

        with mock.patch("time.time") as time_mock:
            time_results = iter([0, 3])
            time_mock.side_effect = lambda: next(time_results)
            queue.disconnect()
            self.assertEqual(len(queue), 2)
            queue.connect()
            self.assertEqual(len(queue), 1)
            
############################################################################
############################################################################

class BaseTestStorageMixin(object):
    """
    Generic tests for L{QueuesStorage} derivatives.
    """
    # TODO test delete

    def setUp(self):
        self.storage = None
        self.delete_storage()
        self.storage_factory()

    ####################################################

    def tearDown(self):
        if self.storage:
            self.storage.delete_all()
            self.storage.close()
        self.delete_storage()

    ####################################################

    def storage_factory(self):
        """
        Open (or create and open) storage.
        """
        raise NotImplementedError

    ####################################################

    def delete_storage(self):
        """
        Close and delete storage.
        """
        raise NotImplementedError

    ####################################################

    def test_get_queues_grouping(self):
        self.storage.push("q1", Message(b"a"))
        self.storage.push("q1", Message(b"a"))
        self.storage.push("q2", Message(b"a"))
        self.storage.push("q2", Message(b"a"))
        self.storage.push("q1", Message(b"a"))
        queues = self.storage.get_queues()
        self.assertEqual(len(queues), 2)
        self.assertEqual(set(queues), set(("q1", "q2")))

    ####################################################

    def test_persistency(self):
        self.assertEqual(len(self.storage.get_queues()), 0)
        self.storage.push("q1", Message(b"a"))
        self.assertEqual(len(self.storage.get_queues()), 1)
        self.assertEqual(len(self.storage.get_items("q2")), 0)
        self.assertEqual(len(self.storage.get_items("q1")), 1)
        self.storage.close()

        self.storage_factory()
        self.assert_(len(self.storage.get_queues()) >= 1)  # at least q1
        self.assertEqual(len(self.storage.get_items("q2")), 0)
        self.assertEqual(len(self.storage.get_items("q1")), 1)

    ####################################################

    def test_message_attributes_persistency(self):
        old_msg = Message(b"a", ttl=100, flags=1234)
        self.storage.push("q1", old_msg)
        self.storage.close()

        self.storage_factory()
        cur_msg = self.storage.get_items("q1")[0]
        self.assertEqual(old_msg.data, cur_msg.data)
        self.assertEqual(old_msg.ttl, cur_msg.ttl)
        self.assertEqual(old_msg.uuid, cur_msg.uuid)
        self.assertEqual(old_msg.flags, cur_msg.flags)

############################################################################
############################################################################

class TestMemoryStorage(BaseTestStorageMixin, utils.TestCase):
    """
    Only "fake" persistency can be tested.
    """

    perm_storage = None  #: fake permanent storage

    def storage_factory(self):
        TestMemoryStorage.perm_storage = (TestMemoryStorage.perm_storage or 
                                    MemoryQueuesStorage())
        self.storage = TestMemoryStorage.perm_storage

    def delete_storage(self):
        TestMemoryStorage.perm_storage = None

############################################################################
############################################################################

class TestSqliteStorage(BaseTestStorageMixin, utils.TestCase):
    STORAGE_FILENAME = "/tmp/snakemq_testqueue.storage"

    def storage_factory(self):
        self.storage = SqliteQueuesStorage(TestSqliteStorage.STORAGE_FILENAME)

    def delete_storage(self):
        if os.path.isfile(TestSqliteStorage.STORAGE_FILENAME):
            os.unlink(TestSqliteStorage.STORAGE_FILENAME)

############################################################################
############################################################################

class TestMongoDbStorage(BaseTestStorageMixin, utils.TestCase):
    __test__ = has_mongodb

    def storage_factory(self):
        self.storage = MongoDbQueuesStorage()

    def delete_storage(self):
        # nothing to delete
        pass
