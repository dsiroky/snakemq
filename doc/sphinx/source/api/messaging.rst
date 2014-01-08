Messaging
=========

.. autoclass:: snakemq.messaging.Messaging
  :members: __init__, send_message

Callbacks
---------

.. autoinstanceattribute:: snakemq.messaging.Messaging.on_connect
.. autoinstanceattribute:: snakemq.messaging.Messaging.on_disconnect
.. autoinstanceattribute:: snakemq.messaging.Messaging.on_message_recv
.. autoinstanceattribute:: snakemq.messaging.Messaging.on_message_sent
.. autoinstanceattribute:: snakemq.messaging.Messaging.on_message_drop

Keep-alive
----------

.. autoinstanceattribute:: snakemq.messaging.Messaging.keepalive_interval
.. autoinstanceattribute:: snakemq.messaging.Messaging.keepalive_wait

Message
-------
.. autoclass:: snakemq.message.Message
  :members: __init__

.. autodata:: snakemq.message.FLAG_PERSISTENT
