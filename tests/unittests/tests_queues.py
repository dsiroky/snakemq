# -*- coding: utf-8 -*-
"""
@author: David Siroky (siroky@dasir.cz)
@license: MIT License (see LICENSE.txt or
          U{http://www.opensource.org/licenses/mit-license.php})
"""

import os
import warnings
import glob

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
    warnings.warn("missing MongoDB", RuntimeWarning)

try:
    from snakemq.storage.sqla import SqlAlchemyQueuesStorage
    has_sqlalchemy = True
except ImportError:
    has_sqlalchemy = False
    warnings.warn("missing SQLAlchemy", RuntimeWarning)

try:
    from snakemq.storage.gadfly import GadflyQueuesStorage
    has_gadfly = True
except ImportError:
    has_gadfly = False
    warnings.warn("missing gadfly", RuntimeWarning)

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
        Few puts, few gets, no TTL or persistence
        """
        queue = self.queues_manager.get_queue("testqueue")
        queue.connect()
        queue.push(Message(b"data a", uuid=b"a"))
        queue.push(Message(b"data b", uuid=b"b"))
        self.assertEqual(len(queue), 2)
        self.assertEqual(queue.get().uuid, b"a")
        self.assertEqual(queue.get().uuid, b"a") # must be the same
        queue.pop()
        self.assertEqual(len(queue), 1)
        self.assertEqual(queue.get().uuid, b"b")
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
            queue.push(Message(b"data a", uuid=b"a", ttl=1))
            queue.push(Message(b"data b", uuid=b"b", ttl=5))
            queue.connect()
            self.assertEqual(len(queue), 1)
            msg = queue.get()
            self.assertEqual(msg.uuid, b"b")
            self.assertEqual(msg.ttl, 2)  # 5 - 3

    ##################################################################

    def test_ttl_none(self):
        queue = self.queues_manager.get_queue("testqueue")
        queue.disconnect()
        queue.push(Message(b"data a", uuid=b"a", ttl=None))
        queue.connect()
        self.assertEqual(len(queue), 1)
        msg = queue.get()
        self.assertEqual(msg.uuid, b"a")
        self.assertEqual(msg.ttl, None)

    ##################################################################

    def test_zero_ttl(self):
        """
        Push item with ttl=0 into a connected or disconnected queue.
        """
        queue = self.queues_manager.get_queue("testqueue")

        # disconnected
        queue.push(Message(b"data a", uuid=b"a", ttl=0))
        self.assertEqual(len(queue), 0)

        queue.connect()
        queue.push(Message(b"data a", uuid=b"a", ttl=0))
        self.assertEqual(len(queue), 1)

    ##################################################################

    def test_persistence(self):
        """
        Without TTL.
        """
        queue = self.queues_manager.get_queue("testqueue")
        queue.connect()
        queue.push(Message(b"data a", uuid=b"a", ttl=1, flags=FLAG_PERSISTENT))
        queue.push(Message(b"data b", uuid=b"b"))
        queue.push(Message(b"data c", uuid=b"c", ttl=1, flags=FLAG_PERSISTENT))
        self.assertEqual(len(queue), 3)
        stored_items = self.queues_manager.storage.get_items("testqueue")
        self.assertEqual(len(stored_items), 2)
        self.assertEqual(stored_items[0].uuid, b"a")
        self.assertEqual(stored_items[1].uuid, b"c")

        # remove "a"
        queue.pop()
        stored_items = self.queues_manager.storage.get_items("testqueue")
        self.assertEqual(len(stored_items), 1)
        self.assertEqual(stored_items[0].uuid, b"c")

        # remove "b", "c" remains
        queue.pop()
        stored_items = self.queues_manager.storage.get_items("testqueue")
        self.assertEqual(len(stored_items), 1)

    ##################################################################

    def test_persistence_restart(self):
        """
        Test of persistent items load.
        """
        queue1 = self.queues_manager.get_queue("testqueue1")
        queue1.connect()
        queue1.push(Message(b"data a", uuid=b"a", ttl=1, flags=FLAG_PERSISTENT))
        queue1.push(Message(b"data b", uuid=b"b", ttl=1, flags=FLAG_PERSISTENT))
        queue1.push(Message(b"data c", uuid=b"c", ttl=1, flags=FLAG_PERSISTENT))
        queue2 = self.queues_manager.get_queue("testqueue2")
        queue2.connect()
        queue2.push(Message(b"data d", uuid=b"d", ttl=1, flags=FLAG_PERSISTENT))
        queue2.push(Message(b"data e", uuid=b"e", ttl=1, flags=FLAG_PERSISTENT))

        self.queue_manager_restart()

        self.assertEqual(len(self.queues_manager), 2)
        queue = self.queues_manager.get_queue("testqueue1")
        self.assertEqual(len(queue), 3)
        self.assertEqual(queue.get().uuid, b"a")
        queue = self.queues_manager.get_queue("testqueue2")
        self.assertEqual(len(queue), 2)
        self.assertEqual(queue.get().uuid, b"d")

    ##################################################################

    def test_persistence_ttl(self):
        queue = self.queues_manager.get_queue("testqueue")
        queue.connect()
        queue.push(Message(b"data a", uuid=b"a", ttl=1, flags=FLAG_PERSISTENT))
        queue.push(Message(b"data b", uuid=b"b"))
        queue.push(Message(b"data c", uuid=b"c", ttl=5, flags=FLAG_PERSISTENT))
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

    def test_persistence(self):
        self.assertEqual(len(self.storage.get_queues()), 0)
        self.storage.push("q1", Message(b"a"))
        self.assertEqual(len(self.storage.get_queues()), 1)
        self.assertEqual(len(self.storage.get_items("q2")), 0)
        self.assertEqual(len(self.storage.get_items("q1")), 1)
        self.storage.close()

        self.storage_factory()
        self.assertGreaterEqual(len(self.storage.get_queues()), 1)  # at least q1
        self.assertEqual(len(self.storage.get_items("q2")), 0)
        self.assertEqual(len(self.storage.get_items("q1")), 1)

    ####################################################

    def test_message_attributes_persistence(self):
        old_msg = Message(b"a", ttl=100, flags=1234)
        self.storage.push("q1", old_msg)
        self.storage.close()

        self.storage_factory()
        cur_msg = self.storage.get_items("q1")[0]
        self.assertEqual(old_msg.data, cur_msg.data)
        self.assertEqual(old_msg.ttl, cur_msg.ttl)
        self.assertEqual(old_msg.uuid, cur_msg.uuid)
        self.assertEqual(old_msg.flags, cur_msg.flags)

    ####################################################

    def test_message_ttl_none(self):
        old_msg = Message(b"a", ttl=None)
        self.storage.push("q1", old_msg)
        self.storage.close()

        self.storage_factory()
        cur_msg = self.storage.get_items("q1")[0]
        self.assertEqual(cur_msg.ttl, None)

    ####################################################

    def test_delete_items(self):
        items = (Message(b"a"), Message(b"b"), Message(b"c"))
        for item in items:
            self.storage.push("q1", item)
        self.assertEqual(len(self.storage.get_items("q1")), len(items))
        self.storage.delete_items([items[0]])
        self.assertEqual(len(self.storage.get_items("q1")), len(items) - 1)
        self.storage.delete_items(items[1:])
        self.assertEqual(len(self.storage.get_items("q1")), 0)

    ####################################################

    def test_update_ttl(self):
        msg = Message(b"a", ttl=10)
        self.storage.push("q1", msg)
        self.storage.push("q1", Message(b"b", ttl=5))

        msg.ttl = 20
        self.storage.update_items_ttl([msg])
        items = self.storage.get_items("q1")
        self.assertEqual(items[0].ttl, 20) # only this message must be updated
        self.assertEqual(items[1].ttl, 5) # this must stay unmodified

    ####################################################

    def test_queue_ordering(self):
        self.storage.push("q1", Message(b"a"))
        self.storage.push("q1", Message(b"b"))
        self.assertEqual(self.storage.get_items("q1")[0].data, b"a")

############################################################################
############################################################################

class TestMemoryStorage(BaseTestStorageMixin, utils.TestCase):
    """
    Only "fake" persistence can be tested.
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
    STORAGE_FILENAME = "testqueuestorage.sqlite"

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

############################################################################
############################################################################

class TestSqlAlchemyPgsqlStorage(BaseTestStorageMixin, utils.TestCase):
    __test__ = has_sqlalchemy
    URL = "postgresql://hasan:aaa@localhost/test"

    def storage_factory(self):
        self.storage = SqlAlchemyQueuesStorage(self.URL)
        self.storage.create_structures()

    def delete_storage(self):
        self.storage = SqlAlchemyQueuesStorage(self.URL)
        self.storage.drop_structures()

############################################################################
############################################################################

class TestGadflyStorage(BaseTestStorageMixin, utils.TestCase):
    __test__ = has_gadfly

    def storage_factory(self):
        self.storage = GadflyQueuesStorage(".", "testqueuestoragegadfly")

    def delete_storage(self):
        for ext in ("gfl", "glb", "gfd", "grl"):
            for fn in glob.glob("*." + ext):
                os.unlink(fn)
