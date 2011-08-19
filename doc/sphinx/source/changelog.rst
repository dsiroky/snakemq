Changelog
=========
0.5.8
  * keep-alive - ping/pong to test if the peer connection is alive
  * fix MSW poll bell nonblocking issue
  * fix message without previous identification
  * fix link connect ENETUNREACH

0.5.7
  * fix multiple connecting peers with the same identification

0.5.6
  * SQLAlchemy storage
  * MongoDB queue ordering fix

0.5.5
  * fix MS Windows SSL
  * messaging example with SSL
  * fix Python 3 syntax
  * updated documentation, RPC
  * RPC module moved from package snakemq.contrib to snakemq
  * message TTL can be set to None (infinity)
  * Link.send() does not return amount of sent bytes, moved to Link.on_ready_to_send
  * removed snakemq.init()
  * internal refactorizations

0.5.4
  * SSL
  * MongoDB storage

0.5.3
  * Python3 adaptation

0.5.2
  * all callbacks can be bound to more then 1 callable
  * more examples

0.5.1
  * fix poll and bell for MS Windows
  * fix RPC example

0.5
  * initial release
