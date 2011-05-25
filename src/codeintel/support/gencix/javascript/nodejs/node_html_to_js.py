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
  * http://nodejs.org/docs/v0.4.2/api/all.html

Tested with NodeJS version:
  * 1.4.2           (default)
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
#log.setLevel(logging.DEBUG)

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
    def __init__(self, name, doc=None, signature=None):
        self.name = name
        self.doc = doc
        self.signature = signature
        self.items = {}
        self.events = []
    def addItem(self, item, doc=None, tag=None):
        if not isinstance(item, NodeItem):
            if item[0].isupper():
                return self.addClass(item, doc=doc)
            elif tag and "(" in tag.string:
                assert ")" in tag.string
                return self.addFunction(item, doc=doc, signature=tag.string)
            item = NodeVariable(item, doc)
        self.items[item.name] = item
        return item
    def addVariable(self, item, doc=None):
        if not isinstance(item, NodeVariable):
            item = NodeVariable(item, doc)
        self.items[item.name] = item
        return item
    def addFunction(self, item, doc=None, signature=None):
        if not isinstance(item, NodeFunction):
            item = NodeFunction(item, doc)
        self.items[item.name] = item
        return item
    def addClass(self, item, doc=None):
        if not isinstance(item, NodeClass):
            item = NodeClass(item, doc)
        self.items[item.name] = item
        return item
    def addEvent(self, event, doc=None):
        if not isinstance(event, NodeEvent):
            event = NodeEvent(event, doc)
        self.events.append(event)
        return event
    def merge(self, other):
        for key, item in other.items.items():
            self.addItem(item)
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
    def __init__(self, name, doc=None):
        NodeItem.__init__(self, name, doc=doc)

class NodeVariable(NodeItem):
    type = "Variable"
    def __init__(self, name, doc=None, citdl=None):
        NodeItem.__init__(self, name, doc=doc)
        self.citdl = citdl
    def stringify(self, ns):
        result = ""
        citdl = self.citdl 
        if self.doc:
            if not citdl:
                if self.doc.lower().startswith("a boolean"):
                    citdl = "Boolean"
            doclines = textwrap.wrap(self.doc, width=72)
            result += "/**\n * %s\n" % ("\n * ".join(doclines))
            if citdl:
                result += " *\n * @type {%s}\n" % (citdl, )
            result += " */\n"
        result += "%s.%s;\n" % (ns, self.name)
        return result

class NodeFunction(NodeItem):
    type = "Function"
    def __init__(self, name, doc=None):
        NodeItem.__init__(self, name, doc=doc)
    def stringify(self, ns):
        result = ""
        if self.doc:
            doclines = textwrap.wrap(self.doc, width=72)
            result += "/**\n * %s\n */\n" % ("\n * ".join(doclines))
        result += "%s.%s = function() {}\n" % (ns, self.name)
        return result

class NodeClass(NodeItem):
    type = "Class"
    def __init__(self, name, doc=None):
        NodeItem.__init__(self, name, doc=doc)
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
    def __init__(self, name):
        NodeItem.__init__(self, name, doc=None)
        self._checkedName = False
        self.current = None
        self._merging = False

    def parse_tag(self, tag):
        if tag.name in ('p'):
            if self.doc is None:
                self.doc = getSubElementText(tag)
            if self.current:
                if self.current.doc is None:
                    #if "<code>" not in str(tag):
                        self.current.doc = getSubElementText(tag)
                elif self._merging:
                    self._merging = False
                    self.current.doc += "\n\n" + getSubElementText(tag)
            return
            
        if tag.name in ('h2', 'h3', 'h4'):
            id = tag.get('id')
            if id.startswith('event_') and id.endswith('_'):
                self.current = self.addEvent(id[6:].strip("_"))
            elif id.startswith('new_') and getSubElementText(tag).startswith("new "):
                # constructor function
                sp = id[len('new_'):].split(".")
                log.debug('  sp: %r', sp)
                assert len(sp) == 1
                name = sp[0]
                if name in self.items:
                    # alternative form of the constructor
                    self.current = self.items[name]
                    self._merging = True
                else:
                    self.current = self.addItem(name, tag=tag)
            elif "." in id:
                sp = id.split(".")
                log.debug('  sp: %r', sp)
                assert len(sp) == 2
                ns = sp[0]
                name = sp[1]
                if not self._checkedName:
                    if ns != self.name and self.name != "global_objects" and \
                       ns not in ('s_tls'):
                        log.warning('  ** renaming module ** %r to %r (%s)', self.name, ns, id)
                        self.name = ns
                    self._checkedName = True
                ns_mappings = {
                    'server': 'Server',
                    'request': 'ServerRequest',
                    'response': 'ServerResponse',
                }
                if ns in ns_mappings:
                    ns = ns_mappings.get(ns)
                if ns in self.items:
                    # this is a property of an item
                    self.current = self.items[ns].addItem(name, tag=tag)
                else:
                    self.current = self.addItem(name, tag=tag)
            elif self.name == "global_objects":
                log.debug('  global: %r', tag)
                self.current = self.addItem(id, tag=tag)
            else:
                log.warning('  ** unhandled tag **: %r', tag)

        if self.name == "process":
            log.debug("process says: %s", tag)

    def write(self):
        if not os.path.exists("raw"):
            os.mkdir("raw")
        f = file(join("raw", "%s.js" % (self.name, )), "w")
        try:
            if self.doc:
                doclines = textwrap.wrap(self.doc, width=72)
                f.write("/**\n * %s\n */\n" % ("\n * ".join(doclines)))
            f.write("var %s = {};\n\n" % (self.name))
            for item_name, item in self.items.items():
                f.write("%s\n" % (item.stringify(self.name)))
            f.write("\n");
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
                    if ns in self.modules:
                        current_module = self.modules[ns]
                        current_name = current_module.name
                        current_module.parse_tag(tag)
                        continue

                    name = ".".join(sp)
                    if name == "timers":
                        current_module = self.modules.get("global_objects")
                    else:
                        log.debug("Module name: %s", name)
                        current_module = NodeModule(name)
                        current_name = name
                        self.modules[name] = current_module
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
        for mod in self.modules.values():
            mod.write()

def getDocsFromWebpage():
    if os.path.exists("docs_042_all.html"):
        return file("docs_042_all.html").read()
    urlOpener = urllib.urlopen("http://nodejs.org/docs/v0.4.2/api/all.html")
    return urlOpener.read()

# Soup parsing of API documentation from webpage
def main():
    htmldata = getDocsFromWebpage()
    processor = NodeProcessor(htmldata)
    processor.parse_docs()
    processor.write_docs()

    #ref_tag = soup.html.body.div.findAll(attrs={'name':"Reference"}, limit=1)[0]
    ##print ref_tag
    #processRefTags(cix_module, ref_tag)

if __name__ == '__main__':
    main()
