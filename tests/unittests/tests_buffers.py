#! -*- coding: utf-8 -*-

import unittest

import snakemq.buffers

class TestBuffers(unittest.TestCase):
    def setUp(self):
        self.buf = snakemq.buffers.StreamBuffer()

    def tearDown(self):
        del self.buf

    ##########################################################

    def test_empty_buffer(self):
        self.assertEqual(self.buf.get(1, True), "")
        self.assertEqual(self.buf.get(1, False), "")

    ##########################################################

    def test_put(self):
        self.buf.put("abc")
        self.assertEqual(len(self.buf), 3)
        self.buf.put("defg")
        self.assertEqual(len(self.buf), 7)

    ##########################################################

    def test_get_cut(self):
        self.buf.put("abcd")
        self.buf.put("efgh")
        self.assertEqual(self.buf.get(3, cut=True), "abc")
        self.assertEqual(self.buf.get(3, cut=True), "def")
        self.assertEqual(len(self.buf), 2)
        self.assertEqual(self.buf.get(3, cut=True), "gh")
        self.assertEqual(len(self.buf), 0)
        self.buf.put("abcd")
        self.buf.put("efgh")
        self.assertEqual(self.buf.get(10, cut=True), "abcdefgh")

    ##########################################################

    def test_get(self):
        self.buf.put("abcd")
        self.buf.put("efgh")
        self.assertEqual(self.buf.get(3, cut=False), "abc")
        self.assertEqual(self.buf.get(5, cut=False), "abcde")
        self.assertEqual(self.buf.get(10, cut=False), "abcdefgh")

    ##########################################################

    def test_large_put(self):
        SIZE = snakemq.buffers.MAX_BUF_CHUNK_SIZE * 3
        HALF = SIZE // 2
        self.buf.put("x" * SIZE)
        self.assertEqual(len(self.buf), SIZE)
        self.assertEqual(self.buf.get(HALF, cut=False), "x" * HALF)
        self.assertEqual(self.buf.get(HALF, cut=True), "x" * HALF)

    ##########################################################

    def test_cut(self):
        self.buf.put("abcd")
        self.buf.put("efgh")
        self.buf.cut(3)
        self.assertEqual(len(self.buf), 5)
        self.buf.cut(3)
        self.assertEqual(len(self.buf), 2)
        self.buf.cut(3)
        self.assertEqual(len(self.buf), 0)
        
