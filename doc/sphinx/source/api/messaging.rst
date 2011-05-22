Messaging
=========

.. autoclass:: snakemq.message.Message
  :members: __init__

.. autoclass:: snakemq.messaging.Messaging
  :members: __init__, send_message

Callbacks
---------

.. autoinstanceattribute:: snakemq.messaging.Messaging.on_connect
.. autoinstanceattribute:: snakemq.messaging.Messaging.on_disconnect
.. autoinstanceattribute:: snakemq.messaging.Messaging.on_message_recv

Message flags
-------------
.. autodata:: snakemq.message.FLAG_PERSISTENT
