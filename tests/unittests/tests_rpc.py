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
                  "exception": (TestException(), None)}

        def wait(exc):
            self.client.store_result(result)

        with mock.patch.object(snakemq.rpc.Wait, "__call__") as wait_mock:
            wait_mock.side_effect = wait

            # respond is OK
            result["ok"] = True
            self.assertEqual(result["return"],
                  self.client.remote_request(self.proxy.some_method, "some ident",
                                              params))
            self.assertEqual(self.client.waiting_for_result, set())
            self.assertEqual(self.client.results, {})

            # respond is an exception
            result["ok"] = False
            self.assertRaises(TestException, self.client.remote_request,
                                  self.proxy.some_method, "some ident", params)
            self.assertEqual(self.client.waiting_for_result, set())
            self.assertEqual(self.client.results, {})

    ##############################################################

    def test_call_timeout_not_connected(self):
        method = self.proxy.some_method
        timeout = 1
        method.set_timeout(timeout)
        self.assertEqual(timeout, method.call_timeout)
        
        with mock.patch("snakemq.rpc.get_time") as time_mock:
            time_results = iter([0.0, timeout * 1.1])
            time_mock.side_effect = lambda: next(time_results)
            self.assertRaises(snakemq.rpc.NotConnected, method)
        self.assertEqual(self.client.cond.wait.call_count, 1)
        self.assertEqual(self.client.waiting_for_result, set())

    ##############################################################

    def test_call_timeout_partial_call(self):
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

        # subsequent reception of result must not be saved
        req_id = self.client.send_params.call_args[0][1]["req_id"]
        self.assertEqual(self.client.waiting_for_result, set())
        result = {"req_id": req_id}
        self.client.store_result(result)
        self.assertEqual(self.client.results, {})
