#!/usr/bin/env python
# Copyright (c) 2006 ActiveState Software Inc.
# See LICENSE.txt for license details.
#
# Contributers (aka Blame):
#  - Todd Whiteman
#

"""JavaScript support for Code Intelligence

    CIX builder for DOM3 codeintel creation. Code Intelligence XML format. See:
        http://specs.tl.activestate.com/kd/kd-0100.html#xml-based-import-export-syntax-cix

    NOTE: Work in progress.....
"""

import os

# Shared code for cix generation
from cix_utils import *

xml_file = "dom3_w3-xml-source.xml"
out_file = "dom3.cix"

def getText(elem):
    l = []
    for element in elem.getiterator():
        if element.text:
            l.append(element.text)
        if element.tail:
            l.append(element.tail)
    return " ".join(l)

def getDescriptionFromElement(elem):
    descnodes = elem.findall('./descr')
    if len(descnodes) == 1:
        return getText(descnodes[0])
    return None

def setCixDoc(cixelement, node):
    doctext = getDescriptionFromElement(node)
    if doctext:
        cixdoc = SubElement(cixelement, "doc")
        cixdoc.text = doctext

def addCixArgument(cixelement, argname, argtype=None):
    cixarg = SubElement(cixelement, "argument", name=argname)
    if argtype:
        cixarg.attrib["type"] = argtype

def addCixReturns(cixelement, returntype=None):
    if returntype and returntype != "void":
        cixreturns = SubElement(cixelement, "returns")
        SubElement(cixreturns, "type", type=returntype)

def setCixSignature(cixelement, signature):
    cixSignature = SubElement(cixelement, "signature")
    cixSignature.text = signature

def generateCIXFromXML(root):
    # Find all main doc namespaces
    cix = Element("codeintel", version="0.1")
  #<file generator="StdCIX" language="JavaScript" md5="*" mtime="1102379523" path="javascript.cix">
  #  <module name="*">
    cixfile = SubElement(cix, "file",
                         language="JavaScript",
                         generator="JavaScript",
                         md5="*",
                         mtime="1102379523",
                         path=out_file)

    cixmodule = SubElement(cixfile, "module", name="dom3")

    for interfacenode in root.findall('.//interface'):
        interface = interfacenode.attrib["name"]
        #if interface not in ("Node", "Document"):
        #    continue
        print "interface: %r" % (interface)

        cixinterface = SubElement(cixmodule, "interface", name=interface)
        inherits = interfacenode.get("inherits")
        if inherits:
            SubElement(cixinterface, "interfaceref", name=inherits)
        setCixDoc(cixinterface, interfacenode)

        for groupnode in interfacenode.findall('.//group'):
            for constantnode in groupnode.findall('./constant'):
                constname = constantnode.get("name")
                cixelement = SubElement(cixinterface, "variable", name=constname)
                setCixDoc(cixelement, constantnode)

        for attrnode in interfacenode.findall('.//attribute'):
            attrname = attrnode.get("name")
            cixelement = SubElement(cixinterface, "variable", name=attrname)
            setCixDoc(cixelement, attrnode)

        # Get the known functions
        # XXX : Functions returns have a doc section... what to do with this
        # XXX : Functions have a raise section... what to do with this
        for methodnode in interfacenode.findall('.//method'):
            methodname = methodnode.get("name")
            cixelement = SubElement(cixinterface, "function", name=methodname)
            arguments = []
            for paramnode in methodnode.findall('./parameters/param'):
                if paramnode.get("attr") == "in":
                    argname = paramnode.get("name")
                    addCixArgument(cixelement, argname, paramnode.get("type"))
                    arguments.append(argname)
            signature = "%s(%s)" % (methodname, ", ".join(arguments))
            setCixSignature(cixelement, signature)
            for returnsnode in methodnode.findall('./returns'):
                addCixReturns(cixelement, returnsnode.get("type"))
            setCixDoc(cixelement, methodnode)

    return cix


def main():
    tree = ElementTree()
    tree.parse(xml_file)
    root = tree.getroot()

    cix = generateCIXFromXML(root)
    cixtree = ElementTree(cix)
    # Write out the tree
    f = file(out_file, "w")
    f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    cixtree.write(f)
    f.close()

    # tidy
    #os.popen("tidy -xml -m -w 1000 -i %s" % (out_file))
    os.popen("tidy -xml -m -w 1000 -i %s 2> /dev/null" % (out_file))

# When run from command line
if __name__ == '__main__':
    main()
