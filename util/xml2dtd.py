#!/usr/bin/env python

# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
# 
# The contents of this file are subject to the Mozilla Public License
# Version 1.1 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
# 
# Software distributed under the License is distributed on an "AS IS"
# basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
# License for the specific language governing rights and limitations
# under the License.
# 
# The Original Code is Komodo code.
# 
# The Initial Developer of the Original Code is ActiveState Software Inc.
# Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
# ActiveState Software Inc. All Rights Reserved.
# 
# Contributor(s):
#   ActiveState Software Inc
# 
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
# 
# ***** END LICENSE BLOCK *****

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
        