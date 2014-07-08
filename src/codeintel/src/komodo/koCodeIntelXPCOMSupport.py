#!/usr/bin/env python
# Copyright (c) 2013 ActiveState
# See the file LICENSE.txt for licensing information.

"""KoCodeIntelXPCOMSupport
This file handles doing code intelligence for XPCOM interfaces"""

import json
import logging
import operator
import Queue
import socket
import threading
from os.path import basename, dirname, splitext
from xpcom import components, COMException, ServerException, nsError
from xpcom.components import classes as Cc, interfaces as Ci
from xpcom.server import UnwrapObject
from xpcom import xpt

log = logging.getLogger("codeintel.xpcom-completer")

class KoCodeIntelXPCOMSupport(threading.Thread):
    _com_interfaces_ = []
    _reg_clsid_ = "{8e774b2b-f3b3-4b5e-a0e6-bd32ffca9f30}"
    _reg_contractid_ = "@activestate.com/codeintel/xpcom;1"
    _reg_desc_ = "Komodo XPCOM Code Intelligence Backend"

    _host = None
    _port = None
    _pipe = None
    _read_buffer = None

    def __init__(self):
        threading.Thread.__init__(self,
                                  name="CodeIntel XPCOM Helper")
        self._ready_to_connect = threading.Event()
        self.daemon = True
        self.start()

    def send_connection_request(self):
        """Send the request over codeintel for the remote process to connect to
        this process (so it can ask for completions)"""
        self._ready_to_connect.set()

    def run(self):
        """Background thread to handle code intelligence queries"""
        while True:
            if socket is None:
                break # in the middle of shut down
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.bind(("127.0.0.1", 0))
            self._sock.listen(0)
            self._read_buffer = ""

            self._ready_to_connect.wait()
            mgr = UnwrapObject(Cc["@activestate.com/koCodeIntelService;1"]
                                 .getService())
            host, port = self._sock.getsockname()
            log.debug("Requesting connection... (to %s %s)", host, port)
            mgr.send(command="xpcom-connect", host=host, port=port)

            try:
                conn = self._sock.accept()
                self._pipe = conn[0]
                log.debug("Connected from %s:%i to %s:%i",
                          *(list(self._pipe.getsockname()) + list(conn[1])))
                continue_reading = True
                while continue_reading:
                    # Read a request
                    size = ""
                    while True:
                        if not self._read_buffer:
                            try:
                                self._read_buffer = self._pipe.recv(4096)
                            except socket.error:
                                log.debug("Connection closed")
                                continue_reading = False
                                break # connection closed
                            else:
                                if not self._read_buffer:
                                    # EOF
                                    continue_reading = False
                                    break
                        log.debug("buffer: %s", self._read_buffer)
                        char = self._read_buffer[0]
                        if char in "0123456789":
                            size += char
                            self._read_buffer = self._read_buffer[1:]
                        else:
                            break
                    if not continue_reading:
                        break
                    log.debug("got size %r, remaining %s", size, self._read_buffer)
                    size = int(size)
                    while len(self._read_buffer) < size:
                        try:
                            self._read_buffer += self._pipe.recv(4096)
                        except socket.error:
                            log.debug("Connection closed reading data")
                            continue_reading = False
                            break
                    if not continue_reading:
                        break
                    data = self._read_buffer[:size]
                    self._read_buffer = self._read_buffer[size:]
                    log.debug("<< %s", data)
                    request = json.loads(data)
                    try:
                        meth = getattr(self, "do_" + request.get("command").replace("-", "_"))
                        meth(**request)
                    except:
                        log.exception("Failed to call method")
                        break
            except Exception as ex:
                if not log:
                    break # log can be None on shutdown
                log.exception(ex)

    def send(self, **kwargs):
        assert not isinstance(threading.current_thread(),
                              threading._MainThread), \
            "should not be sending on main thread"
        data = json.dumps(kwargs)
        self._pipe.sendall("%i%s" % (len(data), data))
        log.debug(">> %s", data)

    def do_list_interface_names(self, **kwargs):
        """List the available XPCOM interfaces"""
        self.send(names=Ci.keys())

    def do_list_contract_ids(self, **kwargs):
        """List the available contract ids"""
        self.send(ids=Cc.keys())

    _LANG_TYPE_FROM_XPT_TAG = {
        "JavaScript": {
            xpt.T_I8                : "Number",
            xpt.T_I16               : "Number",
            xpt.T_I32               : "Number",
            xpt.T_I64               : "Number",
            xpt.T_U8                : "Number",
            xpt.T_U16               : "Number",
            xpt.T_U32               : "Number",
            xpt.T_U64               : "Number",
            xpt.T_FLOAT             : "Number",
            xpt.T_DOUBLE            : "Number",
            xpt.T_BOOL              : "Boolean",
            xpt.T_CHAR              : "String",
            xpt.T_WCHAR             : "String",
            xpt.T_VOID              : "void",
            xpt.T_IID               : None,
            xpt.T_DOMSTRING         : "DOMString",
            xpt.T_CHAR_STR          : "String",
            xpt.T_WCHAR_STR         : "String",
            xpt.T_INTERFACE         : None,
            xpt.T_INTERFACE_IS      : None,
            xpt.T_ARRAY             : "Array",
            xpt.T_PSTRING_SIZE_IS   : None,
            xpt.T_PWSTRING_SIZE_IS  : None,
            xpt.T_UTF8STRING        : "String",
            xpt.T_CSTRING           : "String",
            xpt.T_ASTRING           : "String",
        },
    }

    def _process_method_argument(self, method, language):
        """Process a XPCOM method description
        @param method {xpcom.xpt.Method} The method to process
        @returns (args, returntype)
            args {list of str} The arguments' citdl
            returntype {str} The return type citdl
        """
        args = []
        returntype = None
        param_count = 1
        for param in method.params:
            t = xpt.TypeDescriber(param.type_desc[0], param)
            if t.tag in (xpt.T_INTERFACE, ):
                arg_type = t.Describe()
            elif t.tag in (xpt.T_ARRAY, ):
                arg_type = "Array"
            else:
                arg_type = self._LANG_TYPE_FROM_XPT_TAG\
                               .get(language, {})\
                               .get(t.tag, "unknown")

            if param.IsIn():
                args.append("in %s" % (arg_type))
                param_count += 1
            elif param.IsRetval():
                if t.tag in (xpt.T_INTERFACE, ):
                    returntype = "Components.interfaces.%s" % (arg_type)
                else:
                    returntype = arg_type
            elif param.IsOut():
                args.append("out %s" % (arg_type))
                param_count += 1
        return args, returntype

    def do_describe_interface(self, name=None, language=None, **kwargs):
        assert not isinstance(threading.current_thread(),
                              threading._MainThread), \
            "Should not be describing interfaces on the main thread"
        if not name:
            name = "nsISupports"
        methods = {}
        attributes = {}
        constants = {}
        try:
            iface = xpt.Interface(name)
        except:
            pass
        else:
            attributes = {}
            methods = {}
            for thing in iface.methods:
                if thing.IsNotXPCOM():
                    continue
                args, returntype = self._process_method_argument(thing, language)
                if thing.IsGetter() or thing.IsSetter():
                    if thing.name in attributes and not returntype:
                        continue # don't override getters with setters
                    attributes[thing.name] = {"tag": "variable",
                                              "name": thing.name,
                                              "citdl": returntype}
                else:
                    # XPCOM things that are not getters or setters... it's a method
                    result = {"tag": "scope",
                              "name": thing.name,
                              "ilk": "function"}
                    signature = "%s(%s)" % (thing.name, ", ".join(args))
                    if returntype is not None:
                        result["returns"] = returntype
                        signature += " => %s" % (returntype,)
                    result["signature"] = signature
                    methods[thing.name] = result
            const_citdl = self._LANG_TYPE_FROM_XPT_TAG\
                              .get(language, {})\
                              .get(xpt.T_U32, "Number")
            for constant in iface.constants:
                constants[constant.name] = {"tag": "variable",
                                            "name": constant.name,
                                            "citdl": const_citdl,
                                            "attributes": "constant"}

        name_getter = operator.itemgetter("name")
        results = methods.values() + attributes.values() + constants.values()
        self.send(results=sorted(results, key=name_getter))

class KoCodeIntelXPCOMSupportReigstrationHelper(object):
    """Helper class for codeintel command extension registration; See kd290 /
    KoCodeIntelManager._send_init_requests.initialization_completed"""
    _com_interfaces_ = []
    _reg_clsid_ = "{3ae458a3-b767-47d8-a5a6-1731d415c54b}"
    _reg_contractid_ = "@activestate.com/codeintel/xpcom/registration-helper;1"
    _reg_desc_ = "Komodo XPCOM Code Intelligence Backend Registration Helper"
    _reg_categories_ = [
        ("codeintel-command-extension", _reg_contractid_),
    ]
    def __init__(self):
        self.completer = \
            UnwrapObject(Cc[KoCodeIntelXPCOMSupport._reg_contractid_]
                           .getService())
        self.data = [
            (dirname(__file__), "xpcomJSElements"),
        ]
    def __iter__(self):
        """Iteration for codeintel command extension registration"""
        return self
    def next(self):
        try:
            return self.data.pop(0)
        except IndexError:
            self.completer.send_connection_request()
            raise StopIteration
