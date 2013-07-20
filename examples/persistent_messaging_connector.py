#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.path.insert(0, "../")

import snakemq
import snakemq.link
import snakemq.packeter
import snakemq.messaging
import snakemq.message
import snakemq.storage.sqlite

def on_sent(conn, ident, message):
    print("sent to", conn, ident, message)

s = snakemq.link.Link()
s.add_connector(("localhost", 4000))

pktr = snakemq.packeter.Packeter(s)

storage = snakemq.storage.sqlite.SqliteQueuesStorage("storage.db")
m = snakemq.messaging.Messaging("xconnector", "", pktr, storage)
m.on_message_sent.add(on_sent)

if "send" in sys.argv:
    TTL = 60 # 1 minute
    msg = snakemq.message.Message(b"hello", ttl=TTL,
                                  flags=snakemq.message.FLAG_PERSISTENT)
    m.send_message("xlistener", msg)
    print("message with %i seconds TTL queued (UUID:%r)" % (TTL, msg.uuid))
else:
    print("if you want to queue a message then run this program with argument 'send':")
    print("./persistent_messaging_connector.py send")
    print()

print("trying to deliver queued messages")
s.loop()
