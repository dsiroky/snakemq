Changelog
=========
1.2 (2014-03-28)
  * Python support versions 3.3, 3.4
  * Messaging.on_message_drop() callback
  * listener - allow choosing any available port number
  * logging to any file instead of just stdout
  * fix shebangs

1.1 (2013-04-30)
  * simple bandwidth throttle
  * maintain call order in callbacks
  * RPC - req_id logging on server side
  * more SSL examples
  * persistent queue examples
  * fix unittests missing asserts
  * fix failed SSL handshake cleanup
  * fix PyPy sqlite storage VACUUM
  * fix handle_close() on SSL handshake failure
  * fix SocketPoll socket to file descriptor conversion
  * fix TestBell.test_bell_pipe nonblocking failure

1.0 (2012-05-18)
  * fixed documentation

0.5.10 (2011-12-20)
  * messaging

    * new on_message_sent() callback
    * fix on_packet_sent() callback

  * fix packeter queuing
  * RPC

    * API change - as_signal() moved to RemoteMethod
    * timeout for regular calls
    * custom pickler
    * exception traceback as a string

0.5.9 (2011-09-12)
  * winpoll.py renamed to poll.py and substitutes epoll() when missing
  * fix failing on a short connection which is closed by OS immediately
    after creation
  * fix buffer/memory python compatibility issues
  * fix ttl=None/infinite TTL

0.5.8 (2011-08-19)
  * keep-alive - ping/pong to test if the peer connection is alive
  * fix MSW poll bell nonblocking issue
  * fix message without previous identification
  * fix link connect ENETUNREACH

0.5.7 (2011-07-29)
  * fix multiple connecting peers with the same identification

0.5.6 (2011-07-01)
  * SQLAlchemy storage
  * MongoDB queue ordering fix

0.5.5 (2011-06-09)
  * fix MS Windows SSL
  * messaging example with SSL
  * fix Python 3 syntax
  * updated documentation, RPC
  * RPC module moved from package snakemq.contrib to snakemq
  * message TTL can be set to None (infinity)
  * Link.send() does not return amount of sent bytes, moved to Link.on_ready_to_send
  * removed snakemq.init()
  * internal refactorizations

0.5.4 (2011-05-22)
  * SSL
  * MongoDB storage

0.5.3 (2011-05-18
  * Python3 adaptation

0.5.2 (2011-05-15)
  * all callbacks can be bound to more then 1 callable
  * more examples

0.5.1 (2011-05-12)
  * fix poll and bell for MS Windows
  * fix RPC example

0.5 (2011-05-04)
  * initial release
