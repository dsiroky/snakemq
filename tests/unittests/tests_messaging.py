#! -*- coding: utf-8 -*-
"""
@author: David Siroky (siroky@dasir.cz)
@license: MIT License (see LICENSE.txt or 
          U{http://www.opensource.org/licenses/mit-license.php})
"""

import mock

import snakemq.messaging

import utils

#############################################################################
#############################################################################

class TestMessaging(utils.TestCase):
    def test_recv_frame_type(self):
        packeter = mock.Mock()
        messaging = snakemq.messaging.Messaging("someident", "", packeter)
        with mock.patch.object(messaging, "parse_protocol_version") as parse_mock:
            messaging._on_packet_recv("", messaging.frame_protocol_version())
        self.assertEqual(parse_mock.call_count, 1)

#############################################################################
#############################################################################

class TestReceiveHook(utils.TestCase):
    def setUp(self):
        self.messaging = mock.Mock()
        self.hook = snakemq.messaging.ReceiveHook(self.messaging)

    def tearDown(self):
        self.hook.clear()

    ##############################################################

    def test_basic(self):
        self.hook.register("aa", "1")
        self.hook.register("a", "2")
        self.hook.register("ab", "3")
        self.assertEqual(set(self.hook._get_callbacks("aa")), set(["1", "2"]))
        self.assertEqual(set(self.hook._get_callbacks("aax")), set(["1", "2"]))
        self.assertEqual(set(self.hook._get_callbacks("abx")), set(["2", "3"]))
