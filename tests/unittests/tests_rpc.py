#! -*- coding: utf-8 -*-
"""
@author: David Siroky (siroky@dasir.cz)
@license: MIT License (see LICENSE.txt or
          U{http://www.opensource.org/licenses/mit-license.php})
"""

from collections import defaultdict

import mock

import snakemq.rpc

import utils

#############################################################################
#############################################################################

class TestException(Exception):
    pass

#############################################################################
#############################################################################

class UnpickableData(object):
    def __getstate__(self):
        raise TypeError("I'm not pickable")

#############################################################################
#############################################################################

class TestRpc(utils.TestCase):
    def test_remote_method_clone(self):
        m1 = snakemq.rpc.RemoteMethod("a", "b")
        m2 = m1.clone()
        self.assertNotEqual(m1, m2)
        for attr in ("iproxy", "name", "call_timeout", "signal_timeout"):
            self.assertEqual(getattr(m1, attr), getattr(m2, attr))

#############################################################################
#############################################################################

class TestRpcClient(utils.TestCase):
    def setUp(self):
        self.client = snakemq.rpc.RpcClient(mock.Mock())
        self.client.cond = mock.MagicMock()
        self.proxy = self.client.get_proxy("peer", "some_proxy")

    ##############################################################

    def test_regular_call(self):
        """
        This test simulates situation when the peer is already connected.
        """
        self.client.connected = mock.Mock()
        self.client.connected.get = mock.Mock(side_effect=lambda ident: True)
        self.client.send_params = mock.Mock()

        req_id = b"some id"
        params = defaultdict(lambda: None, req_id=req_id, command="call")
        result = {"req_id": req_id, "return": "x",
                  "exception": TestException(), "exception_format": ""}

        def wait(exc):
            self.assertEqual(exc, snakemq.rpc.PartialCall)
            self.client.store_result(result)

        with mock.patch.object(snakemq.rpc.Wait, "__call__") as wait_mock:
            wait_mock.side_effect = wait

            # respond is OK
            result["ok"] = True
            self.assertEqual(result["return"],
                  self.client.remote_request("some ident", self.proxy.some_method,
                                              params))
            self.assertEqual(self.client.waiting_for_result, set())
            self.assertEqual(self.client.results, {})

            # respond is an exception
            result["ok"] = False
            self.assertRaises(TestException, self.client.remote_request,
                                  "some ident", self.proxy.some_method, params)
            self.assertEqual(self.client.waiting_for_result, set())
            self.assertEqual(self.client.results, {})

    ##############################################################

    def test_call_timeout_not_connected(self):
        self.client.connected = mock.Mock()
        self.client.connected.get = mock.Mock(side_effect=lambda ident: False)

        method = self.proxy.some_method
        timeout = 1
        method.set_timeout(timeout)
        self.assertEqual(timeout, method.call_timeout)

        with mock.patch("snakemq.rpc.get_time") as time_mock:
            time_results = iter([0.0, timeout * 1.1])
            time_mock.side_effect = lambda: next(time_results)
            self.assertRaises(snakemq.rpc.NotConnected, method)
        self.assertEqual(self.client.cond.wait.call_count, 1)
        self.assertEqual(self.client.connected.get.call_count, 2)
        self.assertEqual(self.client.waiting_for_result, set())

    ##############################################################

    def test_call_timeout_partial_call(self):
        """
        Timeout is caused by long reply time from the connected peer.
        """
        self.client.connected = mock.Mock()
        self.client.connected.get = mock.Mock(side_effect=lambda ident: True)
        self.client.send_params = mock.Mock()

        method = self.proxy.some_method
        timeout = 1
        method.set_timeout(timeout)

        with mock.patch("snakemq.rpc.get_time") as time_mock:
            time_results = iter([0.0, timeout * 1.1])
            time_mock.side_effect = lambda: next(time_results)
            self.assertRaises(snakemq.rpc.PartialCall, method)
        self.assertEqual(self.client.cond.wait.call_count, 1)
        self.assertEqual(self.client.connected.get.call_count, 2)

        # subsequent reception of result must not be saved
        req_id = self.client.send_params.call_args[0][1]["req_id"]
        self.assertEqual(self.client.waiting_for_result, set())
        result = {"req_id": req_id}
        self.client.store_result(result)
        self.assertEqual(self.client.results, {})

#############################################################################
#############################################################################

class TestRpcServer(utils.TestCase):
    def setUp(self):
        self.server = snakemq.rpc.RpcServer(mock.Mock())

    ##############################################################

    def test_send_unpickable(self):
        self.assertRaises(self.server.pickler.PickleError,
                          self.server.send, "some ident", UnpickableData())

    ##############################################################

    def test_send_exception(self):
        self.server.send = mock.Mock(wraps=self.server.send)

        # --- send pickable exception, no exception is raised
        # no traceback
        exc = TestException()
        self.server.send_exception("some ident", "req id", exc)
        exc_value = self.server.send.call_args[0][1]["exception"]
        exc_format = self.server.send.call_args[0][1]["exception_format"]
        self.assertEqual(exc_value, exc)
        self.assertEqual(exc_format, "")

        # with traceback
        try:
            raise exc
        except TestException:
            self.server.send_exception("some ident", "req id", exc)
            exc_value = self.server.send.call_args[0][1]["exception"]
            exc_format = self.server.send.call_args[0][1]["exception_format"]
            self.assertEqual(exc_value, exc)
            self.assertNotEqual(exc_format, "")
            self.assertTrue(isinstance(exc_format, str), exc_format.__class__)

        # --- send unpickable exception, original exception must be raised
        exc = TestException(UnpickableData())
        self.assertRaises(exc.__class__,
                          self.server.send_exception, "some ident", "req id", exc)
