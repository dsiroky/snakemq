Messaging
=========

.. autoclass:: snakemq.messaging.Messaging
  :members: __init__, send_message

Callbacks
---------

.. autoinstanceattribute:: snakemq.messaging.Messaging.on_connect
.. autoinstanceattribute:: snakemq.messaging.Messaging.on_disconnect
.. autoinstanceattribute:: snakemq.messaging.Messaging.on_message_recv

Message
-------
.. autoclass:: snakemq.message.Message
  :members: __init__

.. autodata:: snakemq.message.FLAG_PERSISTENT
