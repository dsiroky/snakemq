#! -*- coding: utf-8 -*-
"""
@author: David Siroky (siroky@dasir.cz)
@license: MIT License (see LICENSE.txt or
          U{http://www.opensource.org/licenses/mit-license.php})
"""

import threading
import time

import snakemq.buffers

import utils

class TestBuffers(utils.TestCase):
    def setUp(self):
        self.buf = snakemq.buffers.StreamBuffer()

    def tearDown(self):
        del self.buf

    ##########################################################

    def test_empty_buffer(self):
        self.assertEqual(self.buf.get(1, True), b"")
        self.assertEqual(self.buf.get(1, False), b"")

    ##########################################################

    def test_put(self):
        self.buf.put(b"abc")
        self.assertEqual(len(self.buf), 3)
        self.buf.put(b"defg")
        self.assertEqual(len(self.buf), 7)

    ##########################################################

    def test_get_cut(self):
        self.buf.put(b"abcd")
        self.buf.put(b"efgh")
        self.assertEqual(self.buf.get(3, cut=True), b"abc")
        self.assertEqual(self.buf.get(3, cut=True), b"def")
        self.assertEqual(len(self.buf), 2)
        self.assertEqual(self.buf.get(3, cut=True), b"gh")
        self.assertEqual(len(self.buf), 0)
        self.buf.put(b"abcd")
        self.buf.put(b"efgh")
        self.assertEqual(self.buf.get(10, cut=True), b"abcdefgh")

    ##########################################################

    def test_get(self):
        self.buf.put(b"abcd")
        self.buf.put(b"efgh")
        self.assertEqual(self.buf.get(3, cut=False), b"abc")
        self.assertEqual(self.buf.get(5, cut=False), b"abcde")
        self.assertEqual(self.buf.get(10, cut=False), b"abcdefgh")

    ##########################################################

    def test_large_put(self):
        SIZE = snakemq.buffers.MAX_BUF_CHUNK_SIZE * 3
        HALF = SIZE // 2
        self.buf.put(b"x" * SIZE)
        self.assertEqual(len(self.buf), SIZE)
        self.assertEqual(self.buf.get(HALF, cut=False), b"x" * HALF)
        self.assertEqual(self.buf.get(HALF, cut=True), b"x" * HALF)

    ##########################################################

    def test_cut(self):
        self.buf.put(b"abcd")
        self.buf.put(b"efgh")
        self.buf.cut(3)
        self.assertEqual(len(self.buf), 5)
        self.buf.cut(3)
        self.assertEqual(len(self.buf), 2)
        self.buf.cut(3)
        self.assertEqual(len(self.buf), 0)

############################################################################
############################################################################

class TestBuffersMaxSize(utils.TestCase):
    def setUp(self):
        self.buf = snakemq.buffers.StreamBuffer()
        self.buf.set_max_size(100)

    def tearDown(self):
        del self.buf

    ##########################################################

    def test_simple(self):
        self.buf.put(b"a" * self.buf.max_size, 0.01) # no block
        self.buf.clear()

        self.assertRaises(snakemq.buffers.BufferTooLarge,
                self.buf.put, b"a" * (self.buf.max_size + 1), 0.01)

        self.buf.put(b"a" * (self.buf.max_size // 2), 0.01)
        self.assertRaises(snakemq.buffers.BufferTimeout,
                self.buf.put, b"a" * (self.buf.max_size // 2 + 2), 0.01)

