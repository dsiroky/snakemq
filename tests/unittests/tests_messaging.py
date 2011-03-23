#! -*- coding: utf-8 -*-
"""
@author: David Siroky (siroky@dasir.cz)
@license: MIT License (see LICENSE.txt or 
          U{http://www.opensource.org/licenses/mit-license.php})
"""

import snakemq.messaging

import mocker

import utils

#############################################################################
#############################################################################

class MockMessaging(object):
    def __init__(self):
        self.on_message_receive = None

#############################################################################
#############################################################################

class TestReceiveHook(utils.TestCase):
    def setUp(self):
        self.messaging = MockMessaging()
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
