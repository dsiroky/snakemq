Link
====

.. autoclass:: snakemq.link.SSLConfig
  :members: __init__

.. autoclass:: snakemq.link.LinkSocket
  :members: getpeercert

.. autoclass:: snakemq.link.Link
  :members: add_connector, del_connector, add_listener, del_listener, loop, stop, wakeup_poll, send, close, cleanup

Callbacks
---------

.. autoinstanceattribute:: snakemq.link.Link.on_recv
.. autoinstanceattribute:: snakemq.link.Link.on_ready_to_send
.. autoinstanceattribute:: snakemq.link.Link.on_loop_pass
