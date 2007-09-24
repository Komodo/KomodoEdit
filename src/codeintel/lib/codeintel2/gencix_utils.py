#!/usr/bin/env python
# Copyright (c) 2006 ActiveState Software Inc.
# See LICENSE.txt for license details.

"""Shared CIX tools for Code Intelligence

    CIX helpers for codeintel creation. Code Intelligence XML format. See:
        http://specs.tl.activestate.com/kd/kd-0100.html#xml-based-import-export-syntax-cix
"""

import os
import sys
import re
import shutil
from cStringIO import StringIO
import warnings

from ciElementTree import Element, ElementTree, SubElement
from codeintel2.util import parseDocSummary

# Dictionary of known js types and what they map to
known_javascript_types = {
    "object":       "Object",
    "obj":          "Object",
    "function":     "Function",
    "array":        "Array",
    "string":       "String",
    "text":         "String",
    "int":          "Number",
    "integer":      "Number",
    "number":       "Number",
    "numeric":      "Number",
    "decimal":      "Number",
    "short":        "Number",
    "unsigned short": "Number",
    "long":         "Number",
    "unsigned long":"Number",
    "float":        "Number",
    "bool":         "Boolean",
    "boolean":      "Boolean",
    "true":         "Boolean",
    "false":        "Boolean",
    "date":         "Date",
    "regexp":       "RegExp",
    # Dom elements
    "element":      "Element",
    "node":         "Node",
    "domnode":      "DOMNode",
    "domstring":    "DOMString",
    "widget":       "Widget",
    "domwidget":    "DOMWidget",
    "htmlelement":  "HTMLElement",
    "xmldocument":  "XMLDocument",
    "htmldocument": "HTMLDocument",
    # Special
    "xmlhttprequest": "XMLHttpRequest",
    "void":          "",
    # Mozilla special
    "UTF8String":    "String",
    "AString":       "String",
}

def standardizeJSType(vartype):
    """Return a standardized name for the given type if it is a known type.

    Example1: given vartype of "int", returns "Number"
    Example2: given vartype of "YAHOO.tool", returns "YAHOO.tool"
    """

    if vartype:
        typename = known_javascript_types.get(vartype.lower(), None)
        if typename is None:
            #print "Unknown type: %s" % (vartype)
            return vartype
        return typename

spacere = re.compile(r'\s+')
def condenseSpaces(s):
    """Remove any line enedings and condense multiple spaces"""

    s = s.replace("\n", " ")
    s = spacere.sub(' ', s)
    return s.strip()

def remove_directory(dirpath):
    """ Recursively remove the directory path given """

    if os.path.exists(dirpath):
        shutil.rmtree(dirpath, ignore_errors=True)

def getText(elem):
    """Return the internal text for the given ElementTree node"""

    l = []
    for element in elem.getiterator():
        if element.text:
            l.append(element.text)
        if element.tail:
            l.append(element.tail)
    return " ".join(l)

def getAllTextFromSubElements(elem, subelementname):
    descnodes = elem.findall(subelementname)
    if len(descnodes) == 1:
        return getText(descnodes[0])
    return None

def setCixDoc(cixelement, doctext, parse=False):
    if parse:
        doclines = parseDocSummary(doctext.splitlines(0))
        doctext = "\n".join(doclines)
    elif sys.platform.startswith("win"):
        doctext = doctext.replace("\r\n", "\n")
    #TODO: By default clip doc content down to a smaller set -- just
    #      enough for a good calltip. By then also want an option to
    #      *not* clip, for use in documentation generation.
    #if len(doctext) > 1000:
    #    warnings.warn("doctext for cixelement: %r has length: %d" % (
    #                    cixelement.get("name"), len(doctext)))
    cixelement.attrib["doc"] = doctext

def setCixDocFromNodeChildren(cixelement, node, childnodename):
    doctext = getAllTextFromSubElements(node, childnodename)
    if doctext:
        setCixDoc(cixelement, condenseSpaces(doctext), parse=True)

def addCixArgument(cixelement, argname, argtype=None, doc=None):
    cixarg = SubElement(cixelement, "variable", ilk="argument", name=argname)
    if argtype:
        addCixType(cixarg, argtype)
    if doc:
        setCixDoc(cixarg, doc)
    return cixarg

def addCixReturns(cixelement, returntype=None):
    if returntype and returntype != "void":
        cixelement.attrib["returns"] = returntype

def addCixType(cixobject, vartype):
    if vartype:
        cixobject.attrib["citdl"] = vartype

def addCixAttribute(cixobject, attribute):
    attrs = cixobject.get("attributes")
    if attrs:
        sp = attrs.split()
        if attribute not in sp:
            attrs = "%s %s" % (attrs, attribute)
    else:
        attrs = attribute
    cixobject.attrib["attributes"] = attrs

def addClassRef(cixclass, name):
    refs = cixclass.get("classrefs", None)
    if refs:
        if name not in refs.split(" "):
            cixclass.attrib["classrefs"] = "%s %s" % (refs, name)
    else:
        cixclass.attrib["classrefs"] = "%s" % (name)

def addInterfaceRef(cixinterface, name):
    refs = cixinterface.get("interfacerefs", None)
    if refs:
        if name not in refs.split(" "):
            cixinterface.attrib["interfacerefs"] = "%s %s" % (refs, name)
    else:
        cixinterface.attrib["interfacerefs"] = "%s" % (name)

def setCixSignature(cixelement, signature):
    cixelement.attrib["signature"] = signature

def createCixVariable(cixobject, name, vartype=None, attributes=None):
    if attributes:
        v = SubElement(cixobject, "variable", name=name,
                       attributes=attributes)
    else:
        v = SubElement(cixobject, "variable", name=name)
    if vartype:
        addCixType(v, vartype)
    return v

def createCixFunction(cixmodule, name, attributes=None):
    if attributes:
        return SubElement(cixmodule, "scope", ilk="function", name=name,
                          attributes=attributes)
    else:
        return SubElement(cixmodule, "scope", ilk="function", name=name)

def createCixInterface(cixmodule, name):
    return SubElement(cixmodule, "scope", ilk="interface", name=name)

def createCixClass(cixmodule, name):
    return SubElement(cixmodule, "scope", ilk="class", name=name)

def createCixModule(cixfile, name, lang, src=None):
    if src is None:
        return SubElement(cixfile, "scope", ilk="blob", name=name, lang=lang)
    else:
        return SubElement(cixfile, "scope", ilk="blob", name=name, lang=lang, src=src)

def createOrFindCixModule(cixfile, name, lang, src=None):
    for module in cixfile.findall("./scope"):
        if module.get("ilk") == "blob" and module.get("name") == name and \
           module.get("lang") == lang:
            return module
    return createCixModule(cixfile, name, lang, src)

def createCixFile(cix, path, lang="JavaScript", mtime="1102379523"):
    return SubElement(cix, "file",
                        lang=lang,
                        #mtime=mtime,
                        path=path)

def createCixRoot(version="2.0", name=None, description=None):
    cixroot = Element("codeintel", version=version)
    if name is not None:
        cixroot.attrib["name"] = name
    if description is not None:
        cixroot.attrib["description"] = description
    return cixroot

# Add .text and .tail values to make the CIX output pretty. (Only have
# to avoid "doc" tags: they are the only ones with text content.)
def prettify(elem, level=0, indent='  ', youngestsibling=0):
    if elem and elem.tag != "doc":
        elem.text = '\n' + (indent*(level+1))
    for i in range(len(elem)):
        prettify(elem[i], level+1, indent, i==len(elem)-1)
    elem.tail = '\n' + (indent*(level-youngestsibling))

def get_cix_string(cix, prettyFormat=True):
    # Get the CIX.
    if prettyFormat:
        prettify(cix)
    cixstream = StringIO()
    cixtree = ElementTree(cix)
    cixstream.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    cixtree.write(cixstream)
    cixcontent = cixstream.getvalue()
    cixstream.close()
    return cixcontent

def remove_cix_line_numbers_from_tree(tree):
    for node in tree.getiterator():
        node.attrib.pop("line", None)
        node.attrib.pop("lineend", None)
