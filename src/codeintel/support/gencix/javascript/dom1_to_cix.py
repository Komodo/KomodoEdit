#!/usr/bin/env python
# Copyright (c) 2006 ActiveState Software Inc.
# See LICENSE.txt for license details.
#
# Contributers (aka Blame):
#  - Todd Whiteman
#

"""JavaScript support for Code Intelligence

    CIX builder for DOM1 codeintel creation. Code Intelligence XML format. See:
        http://specs.tl.activestate.com/kd/kd-0100.html#xml-based-import-export-syntax-cix

    Command line tool that parses up DOM1 XML specs to produce a Komodo
    CIX file. Works by grabbing latest copy of DOM1 specs from online
    and then parsing the XML documentation to produce "dom1.cix".

    Requirements:
      * cElementTree    (http://effbot.org/downloads/#cElementTree)

    Website download from:
      * http://www.w3.org/TR/1998/REC-DOM-Level-1-19981001/DOM.zip
"""

import os
import glob
import urllib
import zipfile
from cStringIO import StringIO

# Shared code for cix generation
from cix_utils import *

def generateCIXFromXML(root, filepath):
    # Find all main doc namespaces

    cix = createCixRoot()
    cixfile = createCixFile(cix, filepath, lang="JavaScript")
    cixmodule = createCixModule(cixfile, "dom2", lang="JavaScript")

    if os.path.basename(filepath) == "exception.xml":
        # Requires special handling
        if root.tag == "exception":
            interfacenodes = [root]
        else:
            interfacenodes = root.findall('.//exception')
    else:
        if root.tag == "interface":
            interfacenodes = [root]
        else:
            interfacenodes = root.findall('.//interface')

    for interfacenode in interfacenodes:
        interface = interfacenode.attrib["name"]
        #if interface not in ("Node", "Document"):
        #    continue
        #print "interface: %r" % (interface)

        cixinterface = createCixInterface(cixmodule, interface)
        inherits = interfacenode.get("inherits")
        if inherits:
            addInterfaceRef(cixinterface, inherits)
        setCixDocFromNodeChildren(cixinterface, interfacenode, './descr')

        for groupnode in interfacenode.findall('.//group'):
            for constantnode in groupnode.findall('./constant'):
                constname = constantnode.get("name")
                cixelement = createCixVariable(cixinterface, constname)
                setCixDocFromNodeChildren(cixelement, constantnode, './descr')

        for attrnode in interfacenode.findall('.//attribute'):
            attrname = attrnode.get("name")
            cixelement = createCixVariable(cixinterface, attrname)
            setCixDocFromNodeChildren(cixelement, attrnode, './descr')

        # Get the known functions
        # XXX : Functions returns have a doc section... what to do with this
        # XXX : Functions have a raise section... what to do with this
        for methodnode in interfacenode.findall('.//method'):
            methodname = methodnode.get("name")
            cixelement = createCixFunction(cixinterface, methodname)
            arguments = []
            for paramnode in methodnode.findall('./parameters/param'):
                if paramnode.get("attr") == "in":
                    argname = paramnode.get("name")
                    addCixArgument(cixelement, argname, paramnode.get("type"))
                    arguments.append(argname)
            signature = "%s(%s)" % (methodname, ", ".join(arguments))
            setCixSignature(cixelement, signature)
            for returnsnode in methodnode.findall('./returns'):
                addCixReturns(cixelement, standardizeJSType(returnsnode.get("type")))
            setCixDocFromNodeChildren(cixelement, methodnode, './descr')

    return cix

def getDom1XMLFilesFromWebpage():
    # Gets the zip file from the website and unpacks the necessary contents
    zippath = "DOM.zip"
    if not os.path.exists(zippath):
        urlOpener = urllib.urlopen("http://www.w3.org/TR/1998/REC-DOM-Level-1-19981001/DOM.zip")
        file(zippath, "wb").write(urlOpener.read())

        # Get the xml-source.zip file
        zf = zipfile.ZipFile(zippath)
        zipdata = zf.read("xml-source.zip")
        zf.close()
        file(zippath, "wb").write(zipdata)

    # Now read the sources file
    zf = zipfile.ZipFile(zippath)
    files = {}
    try:
        zf = zipfile.ZipFile(zippath)
        for zfile in zf.filelist:
            #print zfile.filename
            if os.path.dirname(zfile.filename) in ("xml/definitions/level-one-core",
                                                  ):
                                                   #"xml/definitions/level-one-html"):
                name = os.path.basename(zfile.filename)
                data = zf.read(zfile.filename)
                # Remove special entities
                data = data.replace(r"&xml-ns;", "")
                data = data.replace(r"&xmlns-ns;", "")
                data = data.replace("&xml-spec;", "")
                if name in ("exceptions.xml", "document.xml"):
                    # These need to be hacked up because they don't have a
                    # single root node, but rather multiples.
                    lines = data.splitlines(1)
                    lines.insert(3, "<cix_dummy_root>\n")
                    lines.append("</cix_dummy_root>\n")
                    data = "".join(lines)
                files[name] = StringIO(data)
    finally:
        #os.remove(zippath)
        pass
    return files

def main():
    cix_dom1 = createCixRoot()
    cix_dom1_file = createCixFile(cix_dom1, "javascript_dom1", lang="JavaScript")
    cix_dom1_module = createCixModule(cix_dom1_file, "*", lang="JavaScript")

    files = getDom1XMLFilesFromWebpage()
    for filename, xml_file in files.items():
    #for xml_file in glob.glob(os.path.join("dom2_docs", "definitions", "*.xml")):
        print "filename: %r" % (filename)
        tree = ElementTree()
        tree.parse(xml_file)
        root = tree.getroot()

        cix = generateCIXFromXML(root, filename)
        # Append to main cix
        cixinterfaces = cix.findall("./file/module/interface")
        for interface in cixinterfaces:
            cix_dom1_module.append(interface)

    # Write out the tree
    f = file("dom1.cix", "w").write(get_cix_string(cix_dom1))

# When run from command line
if __name__ == '__main__':
    main()
