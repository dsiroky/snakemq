Tutorial
========

-----------
Terminology
-----------

**listener**
  Somebody must listen for incoming connections. Similar to TCP server.

**connector**
  Similar to TCP client.

**peer**
  Program running a snakeMQ stack.

----------
Connection
----------
The stack can have multiple connectors and listeners. Once the connection is
made between a connector and a listener then there is internally no difference
on both sides. You can send and receive on both sides.

It does not matter who is listening and who is connecting (but obviously there
must be a pair connector-listener). Who will be who depends on the network
topology and the application design. E.g. if peer A is somewhere on the
internet and peer B is behind NAT then A must have a listener and B must have a
connector.

----------------------
Simple messaging peers
----------------------
Import modules::

  import snakemq.link
  import snakemq.packeter
  import snakemq.messaging
  import snakemq.message

Build stack::

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

SnakeMQ supports various storage types but SQLite is recommended for its speed and
availability as a default library module.

.. note::
  Persistent are only **outgoing** messages. Once it is delivered it is up to the
  other side to make sure that the message will not be lost.

  It does not matter if the sending side is a connector or a listener.

-------
Logging
-------
If you want to see what is going on inside::

  import logging
  import snakemq

  snakemq.init_logging()
  logger = logging.getLogger("snakemq")
  logger.setLevel(logging.DEBUG)

-----------
SSL context
-----------
To make the link secure add :class:`~.snakemq.link.SSLConfig`::

  import ssl

  sslcfg = snakemq.link.SSLConfig("testpeer.key", "testpeer.crt",
                                  ca_certs="testroot.crt",
                                  cert_reqs=ssl.CERT_REQUIRED)

  # peer A
  my_link.add_listener(("", 4000), ssl_config=sslcfg)

  # peer B
  my_link.add_connector(("localhost", 4000), ssl_config=sslcfg)

Get peer's certificate
--------------------------
To get the peer's certificate use method
:meth:`~.snakemq.link.LinkSocket.getpeercert()`. For example your link's
``on_connect()`` might look like::

  def on_connect(conn):
      sock = slink.get_socket_by_conn(conn)
      print sock.getpeercert()

See ``examples/ssl_*.py``.

---------------------
Remote Procedure Call
---------------------
SnakeMQ's RPC implementation has a huge advantage - you don't need to take care
of connectivity/reconnections. Register your objects and call their
methods whenever it is needed. Since the messaging is symmetrical then both
peers can act as server and client at the same time.

Two kinds of calls:
  - `Regular call with response` - calling will be blocking until the remote
    side connects and returns result. Remote exceptions can be propagated as well.
    If the connection is broken during the call then the client will attempt to
    perform the call again until it gets any result. This may lead to
    starvation on the client side (TODO).
  - `Signal call without response` - calling is not blocking and returns
    ``None``. You can set TTL of the signal.

Call kinds can't be combined. If a method is marked as a signal then it can be
called only as a signal.

Build stack for messaging and add::

    import snakemq.rpc

    # following class is needed to route messages to RPC
    rh = snakemq.messaging.ReceiveHook(my_messaging)

Server::

    class MyClass(object):
        def get_fo(self):
            return "fo value"

        @snakemq.rpc.as_signal  # mark method as a signal
        def mysignal(self):
            print("signal")

    srpc = snakemq.rpc.RpcServer(rh)
    srpc.register_object(MyClass(), "myinstance")
    my_link.loop()

Client::

    crpc = snakemq.rpc.RpcClient(rh)
    proxy = crpc.get_proxy(REMOTE_IDENT, "myinstance")
    proxy.mysignal.as_signal(10)  # 10 seconds TTL
    my_link.loop()

    # in a different thread:
    proxy.mysignal()  # not blocking
    proxy.get_fo()  # blocks until server responds

Exceptions
----------
Propagation of remote exceptions is turned on by default. It can be disabled on
the server side::

    srpc.transfer_exceptions = False

If the exception is transfered and raised on the client side then it has local
traceback. Remote traceback is stored in attribute
``exception.__remote_traceback__``.

--------------------
Bandwidth throttling
--------------------
Very simple bandwidth throttling per connection. Place a throttle between link
and packeter::

    import snakemq.throttle

    my_link = snakemq.link.Link()
    my_throttle = snakemq.throttle.Throttle(my_link, 10000) # ~10 kB/s
    my_packeter = snakemq.packeter.Packeter(my_throttle)
