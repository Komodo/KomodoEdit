#!/usr/bin/env python
# Copyright (c) 2011 ActiveState Software Inc.
# See LICENSE.txt for license details.
#
# Contributers (aka Blame):
#  - Todd Whiteman
#

""" NodeJS documentation to Komodo CIX parser.

Command line tool that parses up node's own HTML documentation to
produce a JavaScript files. Works by grabbing latest copy of online
documentation and then parsing the html to produce js files.

Requirements:
  * BeautifulSoup   (http://www.crummy.com/software/BeautifulSoup/)

Webpage used for documentation:
  * http://nodejs.org/docs/v0.4.8/api/all.html

Tested with NodeJS version:
  * 0.4.8           (default)
"""

import logging
import os
from os.path import join
import re
import sys
import urllib
import textwrap
from pprint import pprint

from BeautifulSoup import BeautifulSoup, NavigableString, Tag

logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.DEBUG)

spacere = re.compile(r'\s+')
def condenseSpaces(s):
    """Remove any line enedings and condense multiple spaces"""

    s = s.replace("\n", " ")
    s = spacere.sub(' ', s)
    return s.strip()

#def getSubElementText(elem):
#    result = []
#    for i in elem:
#        result.append(i.string)
#    return condenseSpaces("".join(result))
def getSubElementText(elem):
    """Return all the text of elem child elements"""

    return condenseSpaces(''.join([e for e in elem.recursiveChildGenerator()
                                   if isinstance(e,unicode)]))

class NodeItem(object):
    type = "Item"
    citdl = None
    def __init__(self, name, doc=None, signature=None, parent=None):
        self.name = name
        self.doc = doc
        self.extra_docs = set()
        self.signature = signature
        self.parent = parent
        self.items = {}
        self.events = []
    def addItem(self, item, doc=None, tag=None, parent=None):
        if not isinstance(item, NodeItem):
            if item[0].isupper():
                self.last_class = self.addClass(item, doc=doc, parent=parent)
                return self.last_class
            elif tag and isinstance(tag, Tag) and "(" in tag.string:
                assert ")" in tag.string
                return self.addFunction(item, doc=doc, parent=parent, signature=tag.string)
            elif tag and isinstance(tag, str) and "(" in tag:
                assert ")" in tag
                return self.addFunction(item, doc=doc, parent=parent, signature=tag)
            item = NodeVariable(item, doc=doc, parent=parent)
        self.items[item.name] = item
        if parent is not None:
            item.parent = self
        return item
    def addVariable(self, item, doc=None, parent=None):
        if not isinstance(item, NodeVariable):
            item = NodeVariable(item, doc=doc, parent=parent)
        self.items[item.name] = item
        return item
    def addFunction(self, item, doc=None, parent=None, signature=None):
        if not isinstance(item, NodeFunction):
            item = NodeFunction(item, doc=doc, parent=parent, signature=signature)
        self.items[item.name] = item
        return item
    def addClass(self, item, doc=None, parent=None):
        if not isinstance(item, NodeClass):
            item = NodeClass(item, doc=doc, parent=parent)
        self.items[item.name] = item
        return item
    def addEvent(self, event, doc=None, parent=None):
        if not isinstance(event, NodeEvent):
            event = NodeEvent(event, doc=doc, parent=parent)
        self.events.append(event)
        return event
    def merge(self, other):
        for key, item in other.items.items():
            self.addItem(item, parent=parent)
        for event in other.events:
            self.addEvent(event)
    def __repr__(self):
        if self.items:
            return "  <%s %s: [%s]>" % (self.type, self.name, ", ".join(self.items.keys()))
        elif self.type == "Class":
            return "<%s %s>" % (self.type, self.name)
        elif self.type == "Function":
            return "%s()" % (self.name)
        else:
            return "%s" % (self.name)
    def __str__(self):
        return "%s" % (self.name)
    def __cmp__(self, other):
        return cmp(self.name, other.name)

class NodeEvent(NodeItem):
    type = "Event"
    def __init__(self, name, **kwargs):
        # note that we add "event:" to the name here and remove it on stringify
        # this is needed to avoid clashes, e.g. http.request vs the event
        NodeItem.__init__(self, "event:" + name, **kwargs)
        log.debug("event %r: %r", name, kwargs)
    def parse_args(self, code, real_module=None, module=None, scope=None):
        """Parse the arguments for an event.
        Unfortunately, the Node documentation for events is not machine-parsable
        for the types of the parameters, so we might as well just ship a hard
        coded list instead.
        @param real_module {str} The original name of the module
        @param module {str} The current name of the module
        @param scope {str|None} The name of the current scope, or None
        """
        scope = getattr(scope, "name", None)
        params = {

            ('process', 'process', None, 'exit'): {},
            ('process', 'process', None, 'uncaughtException'): {
                'err': 'Object'},

            ('events', 'events', 'EventEmitter', 'newListener'): {
                'event': 'String',
                'listener': 'Function'},

            ('readable_stream', 'stream', None, 'data'): {
                'data': 'buffer.Buffer'},
            ('readable_stream', 'stream', None, 'end'): {},
            ('readable_stream', 'stream', None, 'error'): {
                'exception': 'Error'},
            ('readable_stream', 'stream', None, 'close'): {},
            ('readable_stream', 'stream', None, 'fd'): {
                'fd': 'Number'},
            
            ('writable_stream', 'stream', 'ReadableStream', 'drain'): {},
            ('writable_stream', 'stream', 'ReadableStream', 'error'): {
                'exception': 'Error'},
            ('writable_stream', 'stream', 'ReadableStream', 'close'): {},
            ('writable_stream', 'stream', 'ReadableStream', 'pipe'): {
                'src': 'stream.ReadableStream'},
            
            ('tls', 'tls', 'Server', 'secureConnection'): {
                'cleartextStream': 'stream.Stream'},
            
            ('fs', 'fs', 'WriteStream', 'open'): {
                'fd': 'Number'},
 
            ('net', 'net', 'Server', 'connection'): {
                'socket': 'net.Socket'},
            ('net', 'net', 'Server', 'close'): {},
            ('net', 'net', 'Socket', 'connect'): {},
            ('net', 'net', 'Socket', 'data'): {
                'data': 'buffer.Buffer'},
            ('net', 'net', 'Socket', 'end'): {},
            ('net', 'net', 'Socket', 'timeout'): {},
            ('net', 'net', 'Socket', 'drain'): {},
            ('net', 'net', 'Socket', 'error'): {
                'exception': 'Error'},
            ('net', 'net', 'Socket', 'close'): {
                'had_error': 'Boolean'},

            ('udp_datagram_sockets', 'dgram', None, 'message'): {
                'msg': 'buffer.Buffer',
                'rinfo': 'Object'}, # there's no class for this
            ('udp_datagram_sockets', 'dgram', None, 'listening'): {},
            ('udp_datagram_sockets', 'dgram', None, 'close'): {},

            ('http', 'http', 'Server', 'request'): {
                'request': 'http.ServerRequest',
                'response': 'http.ServerResponse'},
            ('http', 'http', 'Server', 'connection'): {
                'stream': 'net.Stream'},
            ('http', 'http', 'Server', 'close'): {
                'errno': 'Number'},
            ('http', 'http', 'Server', 'checkContinue'): {
                'request': 'http.ServerRequest',
                'response': 'http.ServerResponse'},
            ('http', 'http', 'Server', 'upgrade'): {
                'request': 'http.ServerRequest',
                'socket': 'net.Socket',
                'head': 'buffer.Buffer'},
            ('http', 'http', 'Server', 'clientError'): {
                'exception': 'Error'},
            ('http', 'http', 'ServerRequest', 'data'): {
                'chunk': 'String'},
            ('http', 'http', 'ServerRequest', 'end'): {},
            ('http', 'http', 'ServerRequest', 'close'): {
                'err': 'Error'},
            ('http', 'http', 'Agent', 'upgrade'): {
                'response': 'http.ServerResponse',
                'socket': 'net.Socket',
                'head': 'buffer.Buffer'},
            ('http', 'http', 'Agent', 'continue'): {},
            ('http', 'http', 'ClientRequest', 'response'): {
                'response': 'http.ClientResponse'},
            ('http', 'http', 'ClientResponse', 'data'): {
                'chunk': 'String'},
            ('http', 'http', 'ClientResponse', 'end'): {},

            ('child_processes', 'child_process', None, 'exit'): {
                'code': 'Number',
                'signal': 'String'}

        }.get((real_module, module, scope, self.name[len("event:"):]))
        if params is None:
            log.warn("Event %r has unknown parameters",
                     (str(real_module), str(module), str(scope),
                      str(self.name[len("event:"):])))
            params = {}
        self.args = params.keys()
        for arg, argtype in params.items():
            self.extra_docs.add("@param %s {%s}" % (arg, argtype))
        
    def stringify(self, ns):
        result = ""
        name = self.name[len("event:"):]
        if self.doc:
            doclines = textwrap.wrap(self.doc, width=72)
            doclines.extend(sorted(self.extra_docs))
            result += "/**\n * %s\n" % ("\n * ".join(doclines))
            result += " */\n"
        result += "__events__.%s = function(%s) {};" % (name, ", ".join(self.args))
        return result

class NodeVariable(NodeItem):
    type = "Variable"
    def __init__(self, name, citdl=None, **kwargs):
        NodeItem.__init__(self, name, **kwargs)
        self.citdl = citdl
    def stringify(self, ns):
        result = ""
        citdl = self.citdl 
        if self.doc:
            if not citdl:
                if self.doc.lower().startswith("a boolean"):
                    citdl = "Boolean"
            doclines = textwrap.wrap(self.doc, width=72)
            doclines.extend(sorted(self.extra_docs))
            result += "/**\n * %s\n" % ("\n * ".join(doclines))
            if citdl:
                result += " *\n * @type {%s}\n" % (citdl, )
            result += " */\n"
        result += "%s.%s = 0;\n" % (ns, self.name)
        return result

class NodeFunction(NodeItem):
    type = "Function"
    def __init__(self, name, signature=None, **kwargs):
        NodeItem.__init__(self, name, **kwargs)
        self.args = []
        if signature is not None:
            args = signature.split("(", 1)[-1].split(")", 1)[0]
            if args:
                for arg in args.split(","):
                    arg = arg.strip()
                    info = {"raw": arg}
                    if arg.startswith("[") and arg.endswith("]"):
                        # optional argument
                        arg = arg[1:-1]
                        info["optional"] = True
                    # default value
                    sep = arg.find("=")
                    if sep > -1:
                        info["default"] = arg[sep + 1:]
                        arg = arg[:sep]
                    # rest arguments (foo, bar, rest...)
                    if arg.endswith("..."):
                        arg = arg[:-3]
                        if arg == "":
                            # (foo, bar, ...)
                            continue
                    info["name"] = arg
                    self.args.append(info)
        self.fixup_args()

    def fixup_args(self):
        """Fix up the arguments where we have manually hard-coded information
        beyond what can be scraped from the Node.js documentation"""
        data = {
            (None, 'http', 'createServer'): {
                "requestListener": {"type": "__events__.request"}}
        }.get((self.parent.parent and self.parent.parent.name or None,
               self.parent.name, self.name), {})
        for name, info in data.items():
            for arg in self.args:
                if arg["name"] == name:
                    break
            else:
                arg = {"name": name}
                self.args.append(arg)
            arg.update(info)

    def stringify(self, ns):
        result = ""
        if self.doc:
            doclines = textwrap.wrap(self.doc, width=72)
            for arg in self.args:
                doc = arg["name"]
                if "default" in arg:
                    doc = "%s=%s" % (arg["name"], arg["default"])
                # can't do optional args, we failed to parse the docs
                #if arg.get("optional"):
                #    doc = "[%s]" % (doc)
                if "type" in arg:
                    # this argument has hand-written type information
                    doc = "%s {%s}" % (doc, arg["type"])
                doclines.append(u"@param %s" % (doc,))
            doclines.extend(sorted(self.extra_docs))
            result += "/**\n * %s\n */\n" % ("\n * ".join(doclines))
        args = ", ".join([arg["name"] for arg in self.args])
        result += "%s.%s = function(%s) {}\n" % (ns, self.name, args)
        return result

class NodeClass(NodeItem):
    type = "Class"
    def __init__(self, name, **kwargs):
        NodeItem.__init__(self, name, **kwargs)
    def stringify(self, ns):
        result = ""
        if self.doc:
            doclines = textwrap.wrap(self.doc, width=72)
            result += "/**\n * %s\n */\n" % ("\n * ".join(doclines))
        result += "%s.%s = function() {}\n" % (ns, self.name)
        result += "%s.%s.prototype = {}\n" % (ns, self.name)
        for item in self.items.values():
            result += item.stringify("%s.%s.prototype" % (ns, self.name))
        return result

class NodeModule(NodeItem):
    type = "Module"
    def __init__(self, name, real_name=None):
        # Node.js documentation sometimes have headings that don't match the
        # module names
        NodeItem.__init__(self, name, doc=None)
        self.current = None
        self._mergingDocs = False
        self.last_class = None

        self.extra_code = []
        module_extra_doc = ({
            "fs": """\
                /* see http://nodejs.org/docs/v0.4.2/api/fs.html#fs.Stats */
                fs.Stats.prototype = {
                    isFile: function() {},
                    isDirectory: function() {},
                    isBlockDevice: function() {},
                    isCharacterDevice: function() {},
                    isSymbolicLink: function() {},
                    isFIFO: function() {},
                    isSocket: function() {}
                };
                /* required for createReadStream() / createWriteStream() */
                var stream = require('stream');
                """,
            "stream": """\
                /* all streams inherit from EventEmitter */
                var events = require('events');
                stream.ReadableStream.prototype = new events.EventEmitter();
                stream.WritableStream.prototype = new events.EventEmitter();
                """,
            "net": """\
                /* net.Server inherits from EventEmitter */
                var events = require('events');
                net.Server.prototype = new events.EventEmitter();
                net.Socket.prototype = new events.EventEmitter();
                """,
            "http": """\
                var events = require('events');
                http.Server.prototype = new events.EventEmitter();
                http.ServerRequest.prototype = new events.EventEmitter();
                http.ClientRequest.prototype = new events.EventEmitter();
                http.ClientResponse.prototype = new events.EventEmitter();
                var stream = require('stream');
                http.ServerResponse.prototype = new stream.WritableStream();
                """,
            "https": """\
                var http = require('http');
                https.Server.prototype = new http.Server();
                """,
            "url": """\
                /* see http://nodejs.org/docs/v0.4.2/api/url.html#uRL */
                function URL() {}
                URL.prototype = {
                    "href": 0,
                    "protocol": 0,
                    "host": 0,
                    "auth": 0,
                    "hostname": 0,
                    "port": 0,
                    "pathname": 0,
                    "search": 0,
                    "query": 0,
                    "hash": 0,
                };
                """,
            "child_process": """\
                /* used for giving types to ChildProcess.std* */
                var stream = require('stream');
                """,
            "tty": """\
                /* return value of tty.open */
                var child_process = require('child_process');
                """,
        }).get(name)
        if module_extra_doc is not None:
            self.extra_code.append(module_extra_doc)

        self.real_name = real_name or name

    def parse_tag(self, tag):
        if tag.name in ('p'):
            if self.doc is None:
                self.doc = getSubElementText(tag)
            if self.current:
                if self.current.doc is None:
                    if isinstance(self.current, NodeEvent) and \
                       not hasattr(self.current, "args") and \
                        str(tag).startswith("<p><code>function ("):
                        # for an event, the args show up as the first paragraph
                        self.current.parse_args(tag.getText(),
                                                real_module=self.real_name,
                                                module=self.current.parent.name,
                                                scope=self.last_class)
                        return
                    #if "<code>" not in str(tag):
                    self.current.doc = getSubElementText(tag)
                elif self._mergingDocs:
                    self._mergingDocs = False
                    self.current.doc += "\n\n" + getSubElementText(tag)
                assert self.current.parent is not None, \
                    "%r has no parent" % self.current
                # note that self.current.parent might be self (i.e. self.current
                # is a module-level item directly exported)
                extra_docs = ({
                    ('crypto', 'crypto', 'createHash'):
                        "@returns Hash",
                    ('crypto', 'crypto', 'createHmac'):
                        "@returns Hmac",
                    ('crypto', 'crypto', 'createCipher'):
                        "@returns Cipher",
                    ('crypto', 'crypto', 'createDecipher'):
                        "@returns Decipher",
                    ('crypto', 'crypto', 'createSign'):
                        "@returns Sign",
                    ('crypto', 'crypto', 'createVerify'):
                        "@returns Verify",
                    ('file_system', 'fs', 'statSync'):
                        "@returns Stats",
                    ('file_system', 'fs', 'lstatSync'):
                        "@returns Stats",
                    ('file_system', 'fs', 'fstatSync'):
                        "@returns Stats",
                    ('fs', 'fs', 'createReadStream'):
                        "@returns stream.ReadableStream",
                    ('fs', 'fs', 'createWriteStream'):
                        "@returns stream.WritableStream",
                    ('tls', 'tls', 'createServer'):
                        "@returns tls.Server",
                    ('net', 'net', 'createServer'):
                        "@returns net.Server",
                    ('udp_datagram_sockets', 'dgram', 'createSocket'):
                        "@returns dgram.Socket",
                    ('http', 'http', 'createServer'):
                        "@returns http.Server",
                    ('http', 'http', 'getAgent'):
                        "@returns http.Agent",
                    ('http', 'http', 'request'):
                        "@returns http.ClientRequest",
                    ('http', 'http', 'get'):
                        "@returns http.ClientRequest",
                    ('https', 'https', 'createServer'):
                        "@returns https.Server",
                    ('https', 'https', 'request'):
                        "@returns http.ClientRequest",
                    ('https', 'https', 'get'):
                        "@returns http.ClientRequest",
                    ('url', 'url', 'parse'):
                        "@returns URL", # not exported
                    ('executing_javascript', 'vm', 'createScript'):
                        "@return vm.Script",
                    ('child_processes', 'child_process', 'spawn'):
                        "@return child_process.ChildProcess",
                    ('child_processes', 'child_process', 'exec'):
                        "@return child_process.ChildProcess",
                    ('child_processes', 'ChildProcess', 'stdin'):
                        "@type stream.WritableStream",
                    ('child_processes', 'ChildProcess', 'stdout'):
                        "@type stream.ReadableStream",
                    ('child_processes', 'ChildProcess', 'stderr'):
                        "@type stream.ReadableStream",
                    ('tty', 'tty', 'open'):
                        "@returns child_process.ChildProcess",
                }).get((self.real_name, self.current.parent.name, self.current.name))
                if extra_docs is not None:
                    self.current.extra_docs.add(extra_docs)
                else:
                    log.debug("no extra docs for %r, %r, %r",
                              self.real_name, self.current.parent.name, self.current.name)
            return
            
        if tag.name in ('h2', 'h3', 'h4'):
            id = tag.get('id')
            if id.startswith('event_') and id.endswith('_'):
                self.current = self.addEvent(id[6:].strip("_"), parent=self)
            elif id.startswith('new_') and getSubElementText(tag).startswith("new "):
                # constructor function
                sp = id[len('new_'):].split(".")
                if len(sp) > 1 and sp[0] == self.name:
                    sp = sp[1:]
                log.debug('  sp: %r', sp)
                assert len(sp) == 1
                name = sp[0]
                if name in self.items:
                    # alternative form of the constructor
                    self.current = self.items[name]
                    self._mergingDocs = True
                else:
                    self.current = self.addItem(name, tag=tag, parent=self)
            elif "." in id:
                fullname = getSubElementText(tag).split("(", 1)[0]
                if fullname.endswith("("):
                    fullname += ")"
                sp = fullname.split(".")
                log.debug('  sp: %r', sp)
                assert len(sp) == 2
                ns = sp[0]
                name = sp[1]
                # sometimes the documentation uses what looks to be an example
                # variable to describe what properties a class has.  Use a
                # (module, variable-name, [property-name]) -> class-name mapping
                # to fix it up.
                ns_mappings = {
                    ('http', 'server'): 'Server',
                    ('net', 'server'): 'Server',
                    ('tls', 'server'): 'Server',
                    ('buffers', 'buffer'): 'Buffer',
                    ('crypto', 'hash'): 'Hash',
                    ('crypto', 'hmac'): 'Hmac',
                    ('crypto', 'cipher'): 'Cipher',
                    ('crypto', 'decipher'): 'Decipher',
                    ('crypto', 'signer'): 'Sign',
                    ('crypto', 'verifier'): 'Verify',
                    ('events', 'emitter'): 'EventEmitter',
                    ('readable_stream', 'stream'): 'ReadableStream',
                    ('writable_stream', 'stream'): 'WritableStream',
                    ('net', 'socket'): 'Socket',
                    ('udp_datagram_sockets', 'dgram'): 'Socket',
                    ('udp_datagram_sockets', 'dgram', 'createSocket'): 'createSocket', # Node.js documentation is horrible
                    ('http', 'request'): {
                        'ServerRequest': 'ServerRequest',
                        'ClientRequest': 'ClientRequest'},
                    ('http', 'response'): {
                        'ServerResponse': 'ServerResponse',
                        'ClientResponse': 'ClientResponse'},
                    ('http', 'agent'): 'Agent',
                    ('https', 'https', 'createServer'): 'createServer(requestListener)',
                    ('query_string', 'querystring', 'escape'): 'escape(str)',
                    ('query_string', 'querystring', 'unescape'): 'unescape(str)',
                    ('executing_javascript', 'script'): 'Script',
                    ('child_processes', 'child'): 'ChildProcess',
                }
                # try for (module, variable-name, property-name)
                match = ns_mappings.get((self.real_name, ns, name))
                if match is None:
                    # try just (module, variable-name) instead?
                    match = ns_mappings.get((self.real_name, ns))
                if isinstance(match, dict):
                    # some variables are context-dependent, where the last class
                    # defined determines what it's for
                    match = match.get(self.last_class and self.last_class.name)
                if match is not None:
                    # we have match, override.
                    if "(" in match:
                        # override into a method
                        tag = match
                        ns = match[:match.index("(")]
                    else:
                        ns = match
                    if not ns in self.items and ns[0].isupper():
                        # If the first letter is uppercase, assume this is a
                        # class constructor. Sometimes
                        # (e.g. ReadableStream/WritableStream) the class
                        # constructors themselves are not documented, but we
                        # need the class to exist so we can tack things on it.
                        self.addItem(ns, tag=tag, parent=self)
                log.debug('   mod: %r ns: %r name: %r', self.real_name, ns, name)
                if ns in self.items:
                    # this is a property of an item
                    parent = self.items[ns]
                    self.current = parent.addItem(name, tag=tag, parent=parent)
                else:
                    self.current = self.addItem(name, tag=tag, parent=self)
                    if self.name == 'crypto' and name.startswith("create"):
                        # in this module, there's a bunch of create* methods
                        # with matching classes. The docs on the return type
                        # are done in <p> parsing.
                        class_name = name[len('create'):]
                        self.addItem(class_name, tag=tag, parent=self)
            elif "(" in getSubElementText(tag):
                # This is a module-level-and-global method
                name = getSubElementText(tag).split("(", 1)[0]
                self.current = self.addItem(name, tag=tag, parent=self)
            elif self.name == "global_objects":
                log.debug('  global: %r', tag)
                self.current = self.addItem(id, tag=tag, parent=self)
            else:
                log.warning('  ** unhandled tag **: %r', tag)

        if self.name == "process":
            log.debug("process says: %s", tag)

    def write(self, directory="raw"):
        if not os.path.exists(directory):
            os.makedirs(directory, 0755)
        f = file(join(directory, "%s.js" % (self.name, )), "w")
        try:
            # module documentation
            if self.doc:
                doclines = textwrap.wrap(self.doc, width=72)
                f.write("/**\n * %s\n */\n" % ("\n * ".join(doclines)))
            f.write("var %s = {};\n\n" % (self.name))

            # items
            for item_name, item in self.items.items():
                f.write("%s\n" % (item.stringify(self.name)))
            f.write("\n");

            # events
            if self.events:
                f.write("/** @__local__ */ var __events__ = {};\n")
                for event in self.events:
                    f.write("%s\n" % (event.stringify(self.name),))
                f.write("\n");

            # extra module-specific hacks
            if self.extra_code:
                f.write("\n".join(self.extra_code))

            # all done, export things
            f.write("exports = %s;\n\n" % (self.name))
        finally:
            f.close()

    def __repr__(self):
        if self.events:
            return """
%s
    Events: %r
    Items: %r
""" % (self.name, sorted(self.events), sorted(self.items.values()))
        else:
            return """
%s
    Items: %r
""" % (self.name, sorted(self.items.values()))


class NodeProcessor(object):
    def __init__(self, htmldata):
        self.htmldata = htmldata
        self.modules = {}

    def parse_docs(self):
        soup = BeautifulSoup(self.htmldata)
        current_name = None
        current_module = None
        for tag in soup.html.body():
            #if not isinstance(tag, Tag):
            #    continue
            if tag.name == 'h2':
                name = tag.get('id')
                if name in (None, 'synopsis', 'modules',
                            'addenda_Package_Manager_Tips', 'addons') \
                   or name.startswith('appendix_'):
                    # non-module headings
                    current_module = None
                    current_name = None
                else:
                    sp = name.strip("_").split(".")
                    ns = sp[0] = sp[0].lower()

                    ns = ({
                        "buffers": "buffer",
                        "file_system": "fs",
                        "os_module": "os",
                        "streams": "stream",
                        "readable_stream": "stream",
                        "writable_stream": "stream",
                        "udp_datagram_sockets": "dgram",
                        "query_string": "querystring",
                        "executing_javascript": "vm",
                        "child_processes": "child_process",
                        }).get(ns, ns)
                    if (ns != sp[0]):
                        log.warning('  ** renaming module ** %r to %r', sp[0], ns)

                    if ns in self.modules:
                        current_module = self.modules[ns]
                        current_module.real_name = sp[0]
                        current_name = current_module.name
                        current_module.parse_tag(tag)
                        continue

                    log.debug("Module name: %s", ns)
                    current_module = NodeModule(ns, real_name=sp[0])
                    current_name = ns
                    self.modules[ns] = current_module
            elif current_module:
                current_module.parse_tag(tag)
                # parse_tag can cause the module to be renamed - check that now.
                if current_module.name != current_name:
                    self.modules.pop(current_name)
                    current_name = current_module.name
                    self.modules[current_name] = current_module

        self.merge_modules()

        log.info("Modules found: %s",
                 ", ".join([str(x) for x in sorted(self.modules.values())]))

    def merge_modules(self):
        seen_modules = {}
        for key, item in self.modules.items()[:]:
            if item.name in seen_modules:
                log.info("Merging %r namespaces", item.name)
                seen_modules[item.name].merge(item)
                self.modules.pop(key)
            else:
                seen_modules[item.name] = item

    def write_docs(self):
        directory = os.sep.join(os.path.abspath(__file__).split(os.sep)[:-5] +
                                ["lib", "codeintel2", "lib_srcs", "node.js"])
        for mod in self.modules.values():
            mod.write(directory)

def getDocsFromWebpage():
    if os.path.exists("docs_048_all.html"):
        return file("docs_048_all.html").read()
    urlOpener = urllib.urlopen("http://nodejs.org/docs/v0.4.8/api/all.html")
    return urlOpener.read()

# Soup parsing of API documentation from webpage
def main():
    htmldata = getDocsFromWebpage()
    processor = NodeProcessor(htmldata)
    processor.parse_docs()
    processor.write_docs()

if __name__ == '__main__':
    main()
