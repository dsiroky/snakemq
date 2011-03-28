# -*- coding: utf-8 -*-
"""
@author: David Siroky (siroky@dasir.cz)
@license: MIT License (see LICENSE.txt or 
          U{http://www.opensource.org/licenses/mit-license.php})
"""

import struct
import traceback
import cPickle as pickle
import threading
import uuid

from snakemq.message import Message

###############################################################################
###############################################################################
# constants
###############################################################################

REQUEST_PREFIX = "rpcreq"
REPLY_PREFIX = "rpcrep"

WAIT_TIMEOUT = 5

###############################################################################
###############################################################################
# exceptions
###############################################################################

class Error(StandardError):
    pass

class NoInstanceError(Error):
    """ requested object not found """
    pass
    
class NoClassError(Error):
    """ requested class not found """
    pass 

class NoMethodError(Error):
    """ requested method not found """
    pass 

class RunError(Error): 
    """ error in remote method """
    pass

###############################################################################
###############################################################################
# server
###############################################################################

class RpcServer(object):
    """
    Methods of registered objects are called in a different thread other
    than the link loop.
    """

    def __init__(self, receive_hook):
        self.receive_hook = receive_hook
        receive_hook.register(REQUEST_PREFIX, self.on_recv)
        self.instances = {}
        self.raise_remote_exception = True # raise RunError or the real exception

    ######################################################

    def register_object(self, instance, name):
        self.instances[name] = instance

    ######################################################

    def on_recv(self, conn_id, ident, message):
        try:
            params = pickle.loads(message.data[len(REQUEST_PREFIX):])
            cmd = params["command"]
            if cmd == "call":
                # method must not block link loop
                thr = threading.Thread(target=self.call_method,
                                      args=(ident, params))
                thr.setDaemon(True)
                thr.start()
        except Exception, e:
            if self.raise_remote_exception:
                exc = e
            else:
                exc = RunError(e)
            self.send_exception(ident, params["req_id"], exc)

    ######################################################

    def call_method(self, ident, params):
        objname = params["object"]
        try:
            instance = self.instances[objname]
        except KeyError: 
            raise NoInstanceError(objname)

        try:
            method = getattr(instance.__class__,params["method"])
        except KeyError:
            raise NoMethodError(params["method"])
        
        ret = method(instance, *params["args"], **params["kwargs"])

        self.send_return(ident, params["req_id"], ret)

    ######################################################

    def send_exception(self, ident, req_id, exc):
        tb = traceback.format_exc()
        data = {"ok": False, "exception": (exc, tb), "req_id": req_id}
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
        try:
            params = {
                  "req_id": uuid.uuid1().bytes,
                  "command": "call",
                  "object": self.iproxy._name,
                  "method": self.name, 
                  "args": args,
                  "kwargs": kwargs
                }
            ident = self.iproxy._remote_ident
            return self.iproxy._client.remote_request(ident, params)
        except Exception, e:
            eh = self.iproxy._client.exception_handler
            if eh is None: 
                raise
            else: 
                eh(e)

#########################################################################
#########################################################################

class RpcInstProxy(object):
    def __init__(self, client, remote_ident, name):
        self._client = client
        self._remote_ident = remote_ident
        self._name = name

    def __getattr__(self, name):
        key = self._remote_ident + self._name + name
        with self._client.lock:
            if key in self._client.method_proxies:
                return self._client.method_proxies[key]
            else:
                proxy = RemoteMethod(self, name)
                self._client.method_proxies[key] = proxy
                return proxy
        
#########################################################################
#########################################################################

class RpcClient(object):
    def __init__(self, receive_hook):
        self.receive_hook = receive_hook
        self.method_proxies = {}
        self.exception_handler = None
        self.remote_tb = None
        self.results = {}
        self.lock = threading.Lock()
        self.cond = threading.Condition(self.lock)
        self.connected = {} #: remote_ident:bool

        receive_hook.register(REPLY_PREFIX, self.on_recv)
        receive_hook.messaging.on_connect = self.on_connect
        receive_hook.messaging.on_disconnect = self.on_disconnect
    
    ######################################################

    def send_params(self, remote_ident, params):
        raw = pickle.dumps(params)
        message = Message(data=REQUEST_PREFIX + raw)
        self.receive_hook.messaging.send_message(remote_ident, message)

    ######################################################

    def on_connect(self, conn_id, ident):
        with self.cond:
            self.connected[ident] = True
            self.cond.notify_all()

    ######################################################

    def on_disconnect(self, conn_id, ident):
        with self.cond:
            self.connected[ident] = False
            self.cond.notify_all()

    ######################################################

    def on_recv(self, conn_id, ident, message):
        res = pickle.loads(message.data[len(REPLY_PREFIX):])
        with self.cond:
            self.results[res["req_id"]] = res
            self.cond.notify_all()

    ######################################################

    def remote_request(self, remote_ident, params):
        req_id = params["req_id"]

        # repeat request until it is replied
        with self.cond:
            while True:
                if self.connected:
                    self.send_params(remote_ident, params)
                    while (req_id not in self.results) and self.connected:
                        self.cond.wait(WAIT_TIMEOUT)
                if self.connected:
                    res = self.results[req_id]
                    break
                else:
                    self.cond.wait(WAIT_TIMEOUT) # for signal from connect/di
        
        if res["ok"]:
            return res["return"]
        else:
            (exc, tb) = res["exception"]
            self.remote_tb = tb
            raise exc

    ######################################################

    def get_proxy(self, remote_ident, name):
        """
        @return: instance registered with register_object()
        """
        return RpcInstProxy(self, remote_ident, name)

