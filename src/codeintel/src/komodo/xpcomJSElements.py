#!/usr/bin/env python
# Copyright (c) 2013 ActiveState
# See the file LICENSE.txt for licensing information.

"""Python side for XPCOM code intelligence support

XPCOM code intelligence is implemented as a XPCShell subprocess.  Requests are
sent to the subprocess via a TCP stream, and read back from the same.  The
request and response format is similar to the main codeintel oop format
(kd 290), with a different set of commands and no unsolicited responses.  All
commands are processed synchronously; the transport is used only as a RPC
mechanism.
"""

import json
import logging
import os
import Queue
import socket
import subprocess
import sys
import threading

from codeintel2.common import CodeIntelError
from codeintel2.oop.driver import Driver, CommandHandler, RequestFailure
from os.path import basename, dirname, join, splitext
from xml.etree import ElementTree as ET
from zope.cachedescriptors.property import Lazy as LazyProperty

log = logging.getLogger("codeintel.xpcom-completer")
class Element(ET.Element):
    """ciElementTree-lookalike version of ElementTree.Element
    This is necessary because we want to use Python-faked elements for XPCOM
    code completion (because of the flexibility it offers)."""

    def __init__(self, tag, attrib={}, **extra):
        ET.Element.__init__(self, tag, attrib, **extra)

        # See ciElementTree-4-cache.patch
        self.cache = {}

    # See ciElementTree-2-names.patch
    @LazyProperty
    def names(self):
        names = {}
        for child in self:
            name = child.get("name")
            if name:
                names[name] = child
        return names

    # See ciElementTree-1-repr.patch
    def __repr__(self):
        if self.tag == "import":
            symbol = self.get("symbol") # from ... import <symbol>
            alias = self.get("alias") # import ... as <alias>
            import_as = " as %s" % (alias,) if alias is not None else ""
            if symbol is None:
                return "<import %s%s>" % (self.get("module"), import_as)
            return "<from %s import %s%s>" (self.get("module"), symbol, import_as)
        tag = self.get("ilk", self.tag)
        name = self.get("name")
        if name is not None:
            return "<%s %s (%s)>" % (tag, name, self.__class__.__name__)
        return "<%s>" % (tag,)

def SubElement(parent, tag, attrib={}, **extra):
    elem = Element(tag, attrib=attrib, **extra)
    parent.append(elem)
    return elem

class XPCOMInterfaceElement(Element):
    """ET.Element object that dynamically loads interface details as needed"""

    __inited = False
    __children = []
    def __init__(self, name=None, send_fn=None):
        """Create a new XPCOMInterfaceElement
        @param name {str} The name of the interface; e.g. "nsISupports"
        @param send_fn {callable} The function to call to (synchronously) look
            up interface information; should be XPCOMSupport.send
        """
        if not name:
            raise RuntimeError("no name for interface")
        Element.__init__(self, "scope", ilk="class", name=name)
        self.__iface_name = self.get("name")
        self.__send = send_fn

    def makeelement(self, tag, attrib):
        """Override Element.makeelement to always use the Element constructor;
        we do not intend to create fake elements for our children, plus we need
        the ciElement patches"""
        return Element(tag, attrib)

    def _ensure_interface(self):
        """Fetch the XPCOM interface definition for this interface"""
        if self.__inited:
            return # Already have the data

        results = self.__send(command="describe-interface",
                              name=self.__iface_name,
                              language="JavaScript")
        for attrs in results["results"]:
            tag = attrs["tag"]
            del attrs["tag"]
            # avoid touching self._children (infinite recursion)
            if self.__iface_name == "nsIJSCID" and attrs["name"] in (
                    "createInstance", "getService"):
                child = CreateInstanceElement(tag, attrib=attrs)
            else:
                child = Element(tag, attrib=attrs)
            self.__children.append(child)
        self.__inited = True

    @property
    def _children(self):
        self._ensure_interface()
        return self.__children
    @_children.setter
    def _children(self, val):
        self.__children = val
        self.__inited = False

class CreateInstanceElement(Element):
    def resolve(self, evlr, action, scoperef, param):
        evlr.log("Resolve! creating %r (scoperef %r)", param, scoperef)
        if not isinstance(param, basestring):
            return None # Unexpected arguments
        try:
            hits = evlr._hits_from_citdl(param, scoperef)
        except CodeIntelError:
            return None # no valid hits
        accepted_hits = []
        for elem, scoperef in hits:
            if isinstance(elem, XPCOMInterfaceElement):
                accepted_hits.append((elem, scoperef))
        if accepted_hits:
            return accepted_hits

class XPCOMSupport(CommandHandler, threading.Thread):
    # Caches for the XPCOM CIX information.  The base XPCOM structure is
    # generated once per process, then interface details are added on demand.
    xpcom_interfaces_elem = None
    xpcom_components_elem = None
    # The map of IID to XPCOM CIX element.
    xpcom_cix_for_iid = {}
    _socket = None
    _dbfile = None

    supportedCommands = ["xpcom-connect"]

    def __init__(self):
        CommandHandler.__init__(self)
        threading.Thread.__init__(self, name="CodeIntel XPCOM Support Sending")
        self._queue = Queue.Queue()
        self._read_buffer = ""
        self.daemon = True
        self.start()

        catalogs_zone = Driver.getInstance().mgr.db.get_catalogs_zone()
        self._real_get_blob = catalogs_zone.get_blob
        catalogs_zone.get_blob = self.get_blob

    def canHandleRequest(self, request):
        return request.command in self.supportedCommands

    def handleRequest(self, request, driver):
        meth = getattr(self, "do_" + request.command.replace("-", "_"), None)
        if not meth:
            raise RequestFailure("Unexpected command %s" % (request.command,))
        return meth(request, driver)

    def do_xpcom_connect(self, request, driver):
        self._socket = socket.create_connection((request.host, request.port),
                                                source_address=("127.0.0.1", 0))
        log.debug("connected from %s:%i to %s:%i",
                  *(list(self._socket.getsockname()) + list(self._socket.getpeername())))
        driver.send(request=request)

    def add_components_elem(self, blob):
        if self.xpcom_components_elem is None:
            try:
                # Create the blob to hold XPCOM data
                components = Element("variable", citdl="Object", name="Components")
                xpcComponents = self._iid_to_cix("nsIXPCComponents")

                elem_classes = None
                for elem in xpcComponents:
                    if elem.get("name") == "classes":
                        log.debug("Found the classes elem: %r", elem)
                        elem.attrib["citdl"] = "Object"
                        elem_classes = elem
                    elif elem.get("name") == "interfaces":
                        log.debug("Found the interfaces elem: %r", elem)
                        elem.attrib["citdl"] = "Object"
                        self.xpcom_interfaces_elem = elem
                    components.append(elem)

                # Add Components.interfaces data
                for interface in self.send(command="list-interface-names")["names"]:
                    elem = XPCOMInterfaceElement(name=interface, send_fn=self.send)
                    self.xpcom_interfaces_elem.append(elem)

                # Add Components.classes data
                for klass in self.send(command="list-contract-ids")["ids"]:
                    elem = SubElement(elem_classes, "variable", name=klass,
                                      citdl="Components.interfaces.nsIJSCID")

                self.xpcom_components_elem = components
            except:
                log.exception("Failed to init xpcom")

        # Some times we get passed in a cached blob which already has a
        # Components object; don't add the element in that case.
        if blob.get("Components") is None:
            blob.append(self.xpcom_components_elem)

            # Add some common aliases
            for alias_name, citdl in {
                "CI": "Components.interfaces",
                "Ci": "Components.interfaces",
                "CC": "Components.classes",
                "Cc": "Components.classes",
                "CU": "Components.utils",
                "Cu": "Components.utils",
            }.items():
                if blob.get(alias_name) is None:
                    SubElement(blob, "variable", citdl=citdl, name=alias_name)

    def _iid_to_cix(self, iid):
        try:
            return self.xpcom_cix_for_iid[iid]
        except KeyError:
            elem = XPCOMInterfaceElement(name=iid, send_fn=self.send)
            self.xpcom_cix_for_iid[iid] = elem
            return elem

    _read_buffer = ""
    def send(self, **kwargs):
        self._queue.put(kwargs)
        # immediately attempt to read the results back
        try:
            size = ""
            log.debug("... reading frame size...")
            while True:
                self._read_buffer += self._socket.recv(4096)
                log.debug("Got buffer %s (%s bytes)", self._read_buffer[:10], len(self._read_buffer))
                for i, ch in enumerate(self._read_buffer):
                    if ch not in "0123456789":
                        break
                else:
                    continue
                size += self._read_buffer[:i]
                self._read_buffer = self._read_buffer[i:]
                log.debug("buffer: %s, %s", size, self._read_buffer)
                if not self._read_buffer:
                    continue
                break
            size = int(size)
            log.debug("reading %s bytes for frame", size)
            while len(self._read_buffer) < size:
                self._read_buffer += self._socket.recv(4096)
            data = self._read_buffer[:size]
            self._read_buffer = self._read_buffer[size:]
            log.debug("<< %s", data)
            return json.loads(data)
        except:
            log.exception("Failed to send")
        return None

    def run(self):
        """Thread used for sending data to the XPCOM process.
        Reading from the XPCOM process is synchronous."""
        while True:
            item = self._queue.get()
            try:
                data = json.dumps(item)
                log.debug(">> %s", data)
                self._socket.sendall("%i%s" % (len(data), data))
                log.debug("wrote to %s:%s (%s:%s): %s",
                          *(list(self._socket.getpeername()) +
                            list(self._socket.getsockname()) +
                            [data]))
            except:
                log.exception("Failed to write to pipe")
            finally:
                self._queue.task_done()

    def get_blob(self, lang, blobname, look_in_cache_only=False):
        """Wrapper around CatalogsZone.get_blob to fetch our shim blob; we do it
        this way so we can look look up interface definitions only as necessary,
        instead of doing it eagerly at start."""

        if lang != "JavaScript" or blobname != "xpcom" or look_in_cache_only:
            return self._real_get_blob(lang, blobname, look_in_cache_only)

        blob = Element("scope", ilkd="blob", lang="JavaScript", name="xpcom")
        self.add_components_elem(blob)
        return blob

def registerExtension():
    """JavaScript XPCOM component hooks"""
    log.debug("Registering XPCOM component library information")

    supporter = XPCOMSupport()
    Driver.registerCommandHandler(supporter)
