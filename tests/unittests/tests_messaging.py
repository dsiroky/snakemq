#! -*- coding: utf-8 -*-
"""
@author: David Siroky (siroky@dasir.cz)
@license: MIT License (see LICENSE.txt or
          U{http://www.opensource.org/licenses/mit-license.php})
"""

import mock
import nose

import snakemq.message
import snakemq.messaging
import snakemq.exceptions

import utils

memview = snakemq.messaging.memview

#############################################################################
#############################################################################

class TestMessaging(utils.TestCase):
    def setUp(self):
        packeter = mock.Mock()
        self.messaging = snakemq.messaging.Messaging("someident", "", packeter)

    ##############################################################

    def test_recv_frame_type(self):
        with mock.patch.object(self.messaging, "parse_protocol_version") as parse_mock:
            self.messaging._on_packet_recv("", self.messaging.frame_protocol_version())
        self.assertEqual(parse_mock.call_count, 1)

    ##############################################################

    def test_two_connecting_same_ident(self):
        """
        Second connecting peer with the same ident must be rejected.
        """
        self.messaging.parse_identification(b"peerident", "conn_id1")
        self.messaging.parse_identification(b"peerident", "conn_id2")
        self.assertEqual(len(self.messaging._ident_by_conn), 1)
        self.assertEqual(len(self.messaging._conn_by_ident), 1)

    ##############################################################

    @nose.tools.raises(snakemq.exceptions.SnakeMQNoIdent)
    def test_message_parse_no_ident(self):
        """
        Peer did not identified itself and sends message.
        """
        self.assertEqual(len(self.messaging._ident_by_conn), 0)
        self.messaging.parse_message(
                          "x" * snakemq.messaging.FRAME_FORMAT_MESSAGE_SIZE,
                          "nonexistent connid")

    ##############################################################

    def test_protocol_version_frame(self):
        frame = self.messaging.frame_protocol_version()
        payload = memview(frame)[snakemq.messaging.FRAME_TYPE_SIZE:]
        self.messaging.parse_protocol_version(payload, "connid")

    ##############################################################

    def test_identification_frame(self):
        frame = self.messaging.frame_identification()
        payload = memview(frame)[snakemq.messaging.FRAME_TYPE_SIZE:]
        self.messaging.parse_identification(payload, "connid")

    ##############################################################

    def test_message_frame(self):
        self.messaging.on_message_recv = mock.Mock()
        # dummy peer
        self.messaging.parse_identification(b"peerident", "conn_id1")

        msg = snakemq.message.Message(b"data", ttl=0x123456)
        frame = self.messaging.frame_message(msg)
        payload = memview(frame)[snakemq.messaging.FRAME_TYPE_SIZE:]
        self.messaging.parse_message(payload, "conn_id1")
        message = self.messaging.on_message_recv.call_args[0][2]
        self.assertTrue(isinstance(message, snakemq.message.Message))
        self.assertEqual(msg.data, message.data)
        self.assertEqual(msg.uuid, message.uuid)
        self.assertEqual(msg.ttl, message.ttl)

    ##############################################################

    def test_message_frame_infinite_ttl(self):
        self.messaging.on_message_recv = mock.Mock()
        # dummy peer
        self.messaging.parse_identification(b"peerident", "conn_id1")

        msg = snakemq.message.Message(b"data", ttl=None)
        frame = self.messaging.frame_message(msg)
        payload = memview(frame)[snakemq.messaging.FRAME_TYPE_SIZE:]
        self.messaging.parse_message(payload, "conn_id1")
        message = self.messaging.on_message_recv.call_args[0][2]
        self.assertEqual(message.ttl, None)

    ##############################################################

    def test_greetings_no_connection(self):
        self.messaging.packeter.send_packet.side_effect = \
                                                snakemq.exceptions.NoConnection
        # must not raise NoConnection
        self.messaging._on_connect("nonexistent_id")
        self.messaging._on_disconnect("nonexistent_id")

    ##############################################################

    def test_on_message_recv(self):
        self.messaging.on_message_sent = mock.Mock()
        packet_id = 123
        self.messaging.packeter.send_packet.side_effect = lambda *args:packet_id

        # dummy peer
        self.messaging.parse_identification(b"peerident", "conn_id1")

        self.assertEqual(self.messaging._message_by_packet, {})
        msg = snakemq.message.Message(b"data", uuid=b"abc")
        self.messaging.send_message_frame("conn_id1", msg)
        self.messaging._on_packet_sent("conn_id1", packet_id)
        self.messaging.on_message_sent.assert_called_with(
                                        "conn_id1", "peerident", msg.uuid)

    ##############################################################

    def test_on_packet_recv_non_message(self):
        # this packet ID is not associated with any message (e.g. generated by
        # sending identification
        self.messaging._on_packet_sent("conn_id1", 123)

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
