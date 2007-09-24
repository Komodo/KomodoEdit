#!/usr/bin/env python
import os
from xml.dom import pulldom
import logging
import re

log = logging.getLogger("xml2dtd")
log.setLevel(logging.DEBUG)

from elementtree import XMLTreeBuilder
try:
    import cElementTree as ET # effbot's C module
except ImportError:
    log.error("using element tree and not cElementTree, performace will suffer")
    import elementtree.ElementTree as Et # effbot's pure Python module

def dirwalker(dirname, pat=None):
    """Generate all subdirectories of the given directory."""
    import fnmatch
    try:
        contents = os.listdir(os.path.normpath(dirname))
    except OSError, e:
        if e.errno != 13: # permission denied
            raise
        contents = []
    for f in contents:
        fullpath = os.path.join(dirname, f)
        if os.path.isdir(fullpath):
            for path in dirwalker(fullpath, pat):
                yield path
        else:
            if not pat or fnmatch.filter([fullpath], pat):
                yield fullpath

class NamespaceParser(XMLTreeBuilder.FancyTreeBuilder):
    _qname = re.compile("{(.*?)}(.*)")
    def start(self, element):
        element.namespaces = self.namespaces[:]
        qn = self._qname.match(element.tag)
        try:
            element.ns = qn.group(1)
            element.tagName = qn.group(2)
        except:
            element.ns = ""
            element.tagName = element.tag

class DTDinst:
    def __init__(self, filename):
        self.filename = filename
        self.elements = {}
        
    def write(self):
        el = "<!ELEMENT %s %s>"
        al = "<!ATTLIST %s\n%s\n>"
        attr = "%s CDATA #IMPLIED"
        for tag, elements in self.elements.items():
            celem = set()
            for e in elements:
                celem.update(list(e))
            if not celem:
                ctags = "EMPTY"
            else:
                ctags = {}
                for c in celem:
                    ctags[c.tagName] = 0
                children = "(%s)*" % " | ".join(ctags.keys())
            print el % (tag, children)
            
            attrs = {}
            attlist = []
            for c in celem:
                attrs.update(c.attrib)
            for attrib in attrs.keys():
                attlist.append(attr % attrib)
            if attlist:
                print al % (tag, "\n".join(attlist))
            
    
    def parsexml(self, xmlfile):
        tree = ET.parse(xmlfile, NamespaceParser())
        for e in tree.getiterator():
            if not e.tagName in self.elements:
                self.elements[e.tagName] = []
            self.elements[e.tagName].append(e)
    
if __name__=="__main__":
    import sys
    path = os.path.expanduser(os.path.expandvars(sys.argv[2]))
    if path[0] != "/" and path[1] != ":":
        path = os.path.join(os.getcwd(), path)
    path = os.path.normpath(path)
    pattern = None
    if len(sys.argv) > 3:
        pattern = sys.argv[3]
    dtd = DTDinst(sys.argv[1])
    for xmlFile in dirwalker(path, pattern):
        dtd.parsexml(xmlFile)
    dtd.write()
        