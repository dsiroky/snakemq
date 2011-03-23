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

MESSAGE_PREFIX = "rpc"

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
    def __init__(self, receive_hook):
        self.receive_hook = receive_hook
        receive_hook.register(MESSAGE_PREFIX, self.on_recv)
        self.instances = {}
        self.raise_remote_exception = True # raise RunError or the real exception

    ######################################################

    def register_object(self, instance, name):
        self.instances[name] = instance

    ######################################################

    def on_recv(self, conn_id, ident, message):
        try:
            params = pickle.loads(message.data[len(MESSAGE_PREFIX):])
            cmd = params["command"]
            if cmd == "call":
                self.call_method(ident, params)
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
        message = Message(data=MESSAGE_PREFIX + data)
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
                  "private": self.iproxy._private,
                  "object": self.iproxy._name,
                  "method": self.name, 
                  "args": args,
                  "kwargs": kwargs
                }
            return self.iproxy._client.remote_request(params)
        except Exception, e:
            eh = self.iproxy._client.exception_handler
            if eh is None: 
                raise
            else: 
                eh(e)

#########################################################################
#########################################################################

class RpcInstProxy(object):
    def __init__(self, client, name, private=False):
        self._client = client
        self._name = name
        self._private = private

    def __getattr__(self, name):
        key = self._name + name
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
    def __init__(self, remote_ident, receive_hook):
        self.remote_ident = remote_ident
        self.receive_hook = receive_hook
        receive_hook.register(MESSAGE_PREFIX, self.on_recv)
        self.method_proxies = {}
        self.exception_handler = None
        self.remote_tb = None
        self.results = {}
        self.lock = threading.Lock()
        self.cond = threading.Condition(self.lock)
    
    ######################################################

    def send_params(self, params):
        raw = pickle.dumps(params)
        message = Message(data=MESSAGE_PREFIX + raw)
        self.receive_hook.messaging.send_message(self.remote_ident, message)

    ######################################################

    def on_recv(self, conn_id, ident, message):
        res = pickle.loads(message.data[len(MESSAGE_PREFIX):])
        with self.cond:
            self.results[res["req_id"]] = res
            self.cond.notify_all()

    ######################################################

    def remote_request(self, params):
        with self.cond:
            req_id = params["req_id"]
            self.send_params(params)
            while req_id not in self.results:
                self.cond.wait()
            res = self.results[req_id]
        
        if res["ok"]:
            return res["return"]
        else:
            (exc, tb) = res["exception"]
            self.remote_tb = tb
            raise exc

    ######################################################

    def get_proxy(self, name):
        """
        @return: instance registered with register_object()
        """
        return RpcInstProxy(self, name)

