Tutorial
========

----------------------
Simple messaging peers
----------------------
Import modules::

  import snakemq.link
  import snakemq.packeter
  import snakemq.messaging
  import snakemq.message

Build stack::
    
  snakemq.init()
  my_link = snakemq.link.Link()
  my_packeter = snakemq.packeter.Packeter(my_link)
  my_messaging = snakemq.messaging.Messaging(MY_IDENT, "", my_packeter)

where ``MY_IDENT`` is the peer identifier e.g. ``"bob"`` or ``"alice"``. Second parameter is *domain* used for routing - currently unused.

Since the link is symmetrical it does not matter who is connecting and who is listening. Every link can have arbitrary count of listeners and connectors:
  
* Bob::

    my_link.add_listener(("", 4000))  # listen on all interfaces and on port 4000
    my_link.add_connector(("localhost", 4001))

* Alice::

    my_link.add_connector(("localhost", 4000))
    my_link.add_connector(("localhost", 4001))

* Jack::

    my_link.add_connector(("localhost", 4000))
    my_link.add_listener(("", 4001))

After that connections are defined from everybody to each other.

Run link loop (it drives the whole stack)::

  my_link.loop()

Bob wants to send a message to Alice::

  # drop after 600 seconds if the message can't be delivered
  message = snakemq.message.Message(b"hello", ttl=600)
  my_messaging.send_message("alice", message)

The message is inserted into a queue and it will be delivered as soon as
possible. The message is also transient so it will be lost if the process quits.

.. note::
   Sending message to itself (e.g. ``bob_messaging.send_message("bob",
   message)``) will not work. It will be queued but it will be eventually
   delivered only to another peer with the same identifier (peers with
   identical identifier are not desired).

Receiving callback::

  def on_recv(conn, ident, message):
      print(ident, message)

  my_messaging.on_message_recv.add(on_recv)

-----------------
Persistent queues
-----------------
If you want the messaging system to persist undelivered messages (messages will
survive process shutdowns, they will be loaded on start) then use a storage and mark
messages as persistent::

  from snakemq.storage.sqlite import SqliteQueuesStorage
  from snakemq.message import FLAG_PERSISTENT

  storage = SqliteQueuesStorage("storage.db")
  my_messaging = snakemq.messaging.Messaging(MY_IDENT, "", my_packeter, storage)

  message = snakemq.message.Message(b"hello", ttl=600, flags=FLAG_PERSISTENT)

-------
Logging
-------
If you want to see what is going on inside::

  import logging

  logger = logging.getLogger("snakemq")
  logger.setLevel(logging.DEBUG)

-----------
SSL context
-----------
To make the link secure just add SSL configuration::

  sslcfg = snakemq.link.SSLConfig("testkey.pem", "testcert.pem")

  # peer A
  my_link.add_listener(("", 4000), ssl_config=sslcfg)

  # peer B
  my_link.add_connector(("localhost", 4000), ssl_config=sslcfg)

