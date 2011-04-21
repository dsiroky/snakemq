# -*- coding: utf-8 -*-
"""
@author: David Siroky (siroky@dasir.cz)
@license: MIT License (see LICENSE.txt or
          U{http://www.opensource.org/licenses/mit-license.php})
"""

import traceback
import cPickle as pickle
import threading
import uuid
import warnings
import logging

from snakemq.message import Message

###############################################################################
###############################################################################
# constants
###############################################################################

REQUEST_PREFIX = "rpcreq"
REPLY_PREFIX = "rpcrep"

METHOD_RPC_AS_SIGNAL_ATTR = "__snakemw_rpc_as_signal"

REMOTE_TRACEBACK_ATTR = "__remote_traceback__"

###############################################################################
###############################################################################
# exceptions and warnings
###############################################################################

class Error(StandardError):
    pass

class NoInstanceError(Error):
    """ requested object not found """
    pass

class NoMethodError(Error):
    """ requested method not found """
    pass

class SignalCallWarning(Warning):
    """ signal method called normally or regular method called as signal """
    pass

###############################################################################
###############################################################################
# functions
###############################################################################

def as_signal(method):
    """
    Decorate method as a signal on the server side. On the client side it must
    be marked with L{RpcInstProxy.as_signal} method. This decorator must be "on
    top" because it marks the method with a special attribute. If the method is
    "overdecorated" then the attribute will not be visible.
    """
    setattr(method, METHOD_RPC_AS_SIGNAL_ATTR, True)
    return method

###############################################################################
###############################################################################
# server
###############################################################################

class RpcServer(object):
    """
    Registering and unregistering objects is NOT thread safe.

    Methods of registered objects are called in a different thread other
    than the link loop.
    """

    def __init__(self, receive_hook):
        self.log = logging.getLogger("snakemq.rpc.server")
        self.receive_hook = receive_hook
        receive_hook.register(REQUEST_PREFIX, self.on_recv)
        self.instances = {}
        #: transmit call exception back to client
        self.transmit_exceptions = True

    ######################################################

    def register_object(self, instance, name):
        self.instances[name] = instance

    ######################################################

    def unregister_object(self, name):
        del self.instances[name]

    ######################################################

    def get_registered_objects(self):
        return self.instances

    ######################################################

    def on_recv(self, dummy_conn_id, ident, message):
        params = pickle.loads(message.data[len(REQUEST_PREFIX):])
        cmd = params["command"]
        if cmd in ("call", "signal"):
            # method must not block link loop
            thr = threading.Thread(target=self.call_method, name="mqrpc_call",
                                  args=(ident, params))
            thr.setDaemon(True)
            thr.start()

    ######################################################

    def call_method(self, ident, params):
        self.log.debug("call_method ident=%r obj=%r method=%r" %
                        (ident, params["object"], params["method"]))
        # TODO better exception handling
        try:
            objname = params["object"]
            try:
                instance = self.instances[objname]
            except KeyError:
                raise NoInstanceError(objname)

            try:
                method = getattr(instance, params["method"])
            except KeyError:
                raise NoMethodError(params["method"])

            has_signal_attr = hasattr(method, METHOD_RPC_AS_SIGNAL_ATTR)
            if ((params["command"] == "signal" and not has_signal_attr) or
                (params["command"] == "call" and has_signal_attr)):
                warnings.warn("wrong command match for %r" % method,
                              SignalCallWarning)

            # TODO extra try/except for the call
            ret = method(*params["args"], **params["kwargs"])

            # signals have no return value
            if params["command"] == "call":
                self.send_return(ident, params["req_id"], ret)
        except Exception, exc:
            if self.transmit_exceptions:
                self.send_exception(ident, params["req_id"], exc)
            else:
                raise

    ######################################################

    def send_exception(self, ident, req_id, exc):
        traceb = traceback.format_exc()
        data = {"ok": False, "exception": (exc, traceb), "req_id": req_id}
        self.send(ident, data)

    ######################################################

    def send_return(self, ident, req_id, res):
        data = {"ok": True, "return": res, "req_id": req_id}
        self.send(ident, data)

    ######################################################

    def send(self, ident, data):
        data = pickle.dumps(data)
        message = Message(data=REPLY_PREFIX + data)
        self.receive_hook.messaging.send_message(ident, message)

###############################################################################
###############################################################################
# client
###############################################################################

class RemoteMethod(object):
    def __init__(self, iproxy, name):
        self.iproxy = iproxy
        self.name = name

    def __call__(self, *args, **kwargs):
        # pylint: disable=W0212
        timeout = self.iproxy._as_signal.get(self.name)
        if timeout is None:
            command = "call"
        else:
            command = "signal"

        try:
            params = {
                  "req_id": uuid.uuid4().bytes,
                  "command": command,
                  "object": self.iproxy._name,
                  "method": self.name,
                  "args": args,
                  "kwargs": kwargs
                }
            ident = self.iproxy._remote_ident
            return self.iproxy._client.remote_request(ident, params, timeout)
        except Exception, exc:
            ehandler = self.iproxy._client.exception_handler
            if ehandler is None:
                raise
            else:
                ehandler(exc)

#########################################################################
#########################################################################

class RpcInstProxy(object):
    def __init__(self, client, remote_ident, name):
        self._client = client
        self._remote_ident = remote_ident
        self._name = name
        self._as_signal = {}
        client.log.debug("new proxy %r" % self)

    def __getattr__(self, name):
        key = self._remote_ident + self._name + name
        with self._client.lock:
            if key in self._client.method_proxies:
                return self._client.method_proxies[key]
            else:
                self._client.log.debug("new method %r name=%r" % (self, name))
                proxy = RemoteMethod(self, name)
                self._client.method_proxies[key] = proxy
                return proxy

    def as_signal(self, method_name, timeout=0):
        """
        Method will be called without waiting for a return value.
        @param timeout: messaging TTL
        """
        self._as_signal[method_name] = timeout

    def __repr__(self):
        return ("<%s 0x%x remote_ident=%r name=%r>" %
                (self.__class__.__name__, id(self), self._remote_ident, self._name))

#########################################################################
#########################################################################

class RpcClient(object):
    def __init__(self, receive_hook):
        self.log = logging.getLogger("snakemq.rpc.client")
        self.receive_hook = receive_hook
        self.method_proxies = {}
        self.exception_handler = None
        self.results = {}
        self.lock = threading.Lock()
        self.cond = threading.Condition(self.lock)
        self.connected = {}  #: remote_ident:bool

        receive_hook.register(REPLY_PREFIX, self.on_recv)
        receive_hook.messaging.on_connect.add(self.on_connect)
        receive_hook.messaging.on_disconnect.add(self.on_disconnect)

    ######################################################

    def send_params(self, remote_ident, params, ttl):
        raw = pickle.dumps(params)
        message = Message(data=REQUEST_PREFIX + raw, ttl=ttl)
        self.receive_hook.messaging.send_message(remote_ident, message)

    ######################################################

    def on_connect(self, dummy_conn_id, ident):
        with self.cond:
            self.connected[ident] = True
            self.cond.notify_all()

    ######################################################

    def on_disconnect(self, dummy_conn_id, ident):
        with self.cond:
            self.connected[ident] = False
            self.cond.notify_all()

    ######################################################

    def on_recv(self, dummy_conn_id, dummy_ident, message):
        res = pickle.loads(message.data[len(REPLY_PREFIX):])
        with self.cond:
            self.results[res["req_id"]] = res
            self.cond.notify_all()

    ######################################################

    def remote_request(self, remote_ident, params, signal_timeout):
        self.log.debug("remote_request ident=%r obj=%r method=%r" %
                        (remote_ident, params["object"], params["method"]))
        req_id = params["req_id"]

        if signal_timeout is None:
            # repeat request until it is replied
            with self.cond:
                while True:
                    if self.connected.get(remote_ident):
                        self.send_params(remote_ident, params, 0)
                        while ((req_id not in self.results) and
                                  self.connected.get(remote_ident)):
                            self.cond.wait()
                    if self.connected.get(remote_ident):
                        res = self.results[req_id]
                        break
                    else:
                        self.cond.wait()  # for signal from connect/di

            if res["ok"]:
                return res["return"]
            else:
                (exc, traceb) = res["exception"]
                self.raise_remote_exception(exc, traceb)
        else:
            self.send_params(remote_ident, params, signal_timeout)

    ######################################################

    def raise_remote_exception(self, exc, traceb):
        setattr(exc, REMOTE_TRACEBACK_ATTR, traceb)
        raise exc

    ######################################################

    def get_proxy(self, remote_ident, name):
        """
        @return: instance registered with register_object()
        """
        return RpcInstProxy(self, remote_ident, name)
