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
#
# Contributers (aka Blame):
#  - Todd Whiteman
#

"""JavaScript support for Code Intelligence

    CIX builder for DOM2 codeintel creation. Code Intelligence XML format. See:
        http://specs.tl.activestate.com/kd/kd-0100.html#xml-based-import-export-syntax-cix

    Command line tool that parses up DOM2 XML specs to produce a Komodo
    CIX file. Works by grabbing latest copy of DOM2 specs from online
    and then parsing the XML documentation to produce "dom2.cix".
    
    Requirements:
      * cElementTree    (http://effbot.org/downloads/#cElementTree)

    Website download from:
      * http://www.w3.org/TR/2000/REC-DOM-Level-2- ...
"""

import os
import glob
import string
import urllib
import zipfile
from cStringIO import StringIO

# Shared code for cix generation
from codeintel2.gencix_utils import *

def generateCIXFromXML(root, filepath):
    # Find all main doc namespaces

    cix = createCixRoot()
    cixfile = createCixFile(cix, filepath, lang="JavaScript")
    cixmodule = createCixModule(cixfile, os.path.basename(filepath), lang="JavaScript")

    if os.path.basename(filepath) in ("exceptions.xml",
                                      "eventexception.xml"):
        # Requires special handling
        #print "Root tag: %r" % (root.tag)
        if root.tag == "exception":
            exceptionnodes = [root]
        else:
            exceptionnodes = root.findall('.//exception')

        for exceptionnode in exceptionnodes:
            exceptionName = exceptionnode.attrib["name"]
            #print "exceptionName: %r" % (exceptionName)

            cixclass = createCixClass(cixmodule, exceptionName)
            setCixDocFromNodeChildren(cixclass, exceptionnode, './descr')

            for componentnode in exceptionnode.findall('./component'):
                componentname = componentnode.get("name")
                typenode = componentnode.findall("typename")
                typename = None
                if typenode:
                    typename = standardizeJSType(getText(typenode[0]))
                cixelement = createCixVariable(cixclass, componentname, typename)
                setCixDocFromNodeChildren(cixelement, componentnode, './descr')

            for groupnode in root.findall('.//group'):
                for constantnode in groupnode.findall('./constant'):
                    constname = constantnode.get("name")
                    #print "Constant: %s" % (constname)
                    typename = constantnode.get("type")
                    if typename:
                        typename = standardizeJSType(typename)
                    cixelement = createCixVariable(cixclass, constname, vartype=typename, attributes="static")
                    setCixDocFromNodeChildren(cixelement, constantnode, './descr')

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

            cixclass = createCixClass(cixmodule, interface)
            inherits = interfacenode.get("inherits")
            if inherits:
                addClassRef(cixclass, inherits)
            setCixDocFromNodeChildren(cixclass, interfacenode, './descr')

            groupnodes = interfacenode.findall('.//group')
            for groupnode in groupnodes:
                for constantnode in groupnode.findall('./constant'):
                    constname = constantnode.get("name")
                    #print "Constant: %s" % (constname)
                    typename = constantnode.get("type")
                    if typename:
                        typename = standardizeJSType(typename)
                    cixelement = createCixVariable(cixclass, constname, vartype=typename, attributes="static")
                    setCixDocFromNodeChildren(cixelement, constantnode, './descr')

            for attrnode in interfacenode.findall('.//attribute'):
                attrname = attrnode.get("name")
                typename = attrnode.get("type")
                if typename:
                    typename = standardizeJSType(typename)
                cixelement = createCixVariable(cixclass, attrname, vartype=typename)
                setCixDocFromNodeChildren(cixelement, attrnode, './descr')

            # Get the known functions
            # XXX : Functions returns have a doc section... what to do with this
            # XXX : Functions have a raise section... what to do with this
            for methodnode in interfacenode.findall('.//method'):
                methodname = methodnode.get("name")
                cixelement = createCixFunction(cixclass, methodname)
                arguments = []
                for paramnode in methodnode.findall('./parameters/param'):
                    if paramnode.get("attr") == "in":
                        argname = paramnode.get("name")
                        addCixArgument(cixelement, argname, standardizeJSType(paramnode.get("type")))
                        arguments.append(argname)
                signature = "%s(%s)" % (methodname, ", ".join(arguments))
                setCixSignature(cixelement, signature)
                for returnsnode in methodnode.findall('./returns'):
                    addCixReturns(cixelement, standardizeJSType(returnsnode.get("type")))
                setCixDocFromNodeChildren(cixelement, methodnode, './descr')

    return cix

def fixXMLEntities(data):
    """Remove some fields/characters that stuff up xml parsing"""

    data = data.replace(r"&xml-ns;", "")
    data = data.replace(r"&xmlns-ns;", "")
    data = data.replace("&xml-spec;", "")
    data = data.replace("&html40;", "")
    data = data.replace("&css2;", "")
    data = data.replace("&xml-stylesheet;", "")
    data = data.replace("&core.latest.url;", "")
    data = data.replace("\xa8", "a")
    data = data.replace("\xa9", "a")
    data = data.replace("\xe4", "e")
    data = data.replace("\xe9", "e")
    data = data.replace("\xfc", "a")
    return data

def getDom2XMLFilesFromWebpage():
    """Gets the zip file from the website and unpacks the necessary contents"""

    files = {}
    zippath = "xml-source.zip"
    urls = ("http://www.w3.org/TR/2000/REC-DOM-Level-2-Core-20001113/DOM2-Core.zip",
            "http://www.w3.org/TR/2003/REC-DOM-Level-2-HTML-20030109/DOM2-HTML.zip",
            "http://www.w3.org/TR/2000/REC-DOM-Level-2-Traversal-Range-20001113/DOM2-Traversal-Range.zip",
            "http://www.w3.org/TR/2000/REC-DOM-Level-2-Style-20001113/DOM2-Style.zip",
            "http://www.w3.org/TR/2000/REC-DOM-Level-2-Events-20001113/DOM2-Events.zip",
            "http://www.w3.org/TR/2000/REC-DOM-Level-2-Views-20001113/DOM2-Views.zip",
           )
    for url in urls:
        urlOpener = urllib.urlopen(url)
    # When testing using local files
    #urls = ("/home/toddw/downloads/javascript/DOM2-Core.zip",
    #        "/home/toddw/downloads/javascript/DOM2-HTML.zip",
    #        "/home/toddw/downloads/javascript/DOM2-Traversal-Range.zip",
    #        "/home/toddw/downloads/javascript/DOM2-Style.zip",
    #        "/home/toddw/downloads/javascript/DOM2-Events.zip",
    #        "/home/toddw/downloads/javascript/DOM2-Views.zip",
    #       )
    #for url in urls:
    #    urlOpener = file(url)

        try:
            file(zippath, "wb").write(urlOpener.read())
            zf = zipfile.ZipFile(zippath)
            zipdata = ""
            xml_source = ""
            try:
                zipdata = zf.read(zippath)
                print "File %r okay" % (os.path.basename(url))
            except KeyError:
                #print "No %s in file %r" % (zippath, os.path.basename(url))
                xml_source = zf.read("xml-source.xml")
            zf.close()
            if zipdata:
                file(zippath, "wb").write(zipdata)
    
                zf = zipfile.ZipFile(zippath)
                foundDefinitions = False
                possibleFiles = {}
                for zfile in zf.filelist:
                    #print "  File %r" % (zfile.filename)
                    if os.path.dirname(zfile.filename) == "definitions":
                        foundDefinitions = True
                        name = os.path.basename(zfile.filename)
                        # Remove special entities
                        data = fixXMLEntities(zf.read(zfile.filename))
                        if name in ("exceptions.xml", "document.xml", "eventexception.xml"):
                            # These need to be hacked up because they don't have a
                            # single root node, but rather multiple root nodes.
                            lines = data.splitlines(1)
                            lines.insert(3, "<cix_dummy_root>\n")
                            lines.append("</cix_dummy_root>\n")
                            data = "".join(lines)
                        files[name] = StringIO(data)
                    elif zfile.filename[0] in string.letters and \
                         zfile.filename not in ("dom-spec.xml", ):
                        possibleFiles[zfile.filename] = StringIO(fixXMLEntities(zf.read(zfile.filename)))
                    elif zfile.filename == "":
                        pass
                if not foundDefinitions:
                    if len(possibleFiles) > 0:
                        #print "  Possibles: %r" % (possibleFiles.keys())
                        files.update(possibleFiles)
            elif xml_source:
                files[os.path.basename(url)] = StringIO(fixXMLEntities(xml_source))
                print "Special casing for %s" % (os.path.basename(url))
            zf.close()
        finally:
            os.remove(zippath)
    return files

def main():
    cix_dom2 = createCixRoot()
    cix_dom2_file = createCixFile(cix_dom2, "javascript_dom2", lang="JavaScript")
    cix_dom2_module = createCixModule(cix_dom2_file, "*", lang="JavaScript")

    files = getDom2XMLFilesFromWebpage()
    for filename, xml_file in files.items():
        #print "filename: %r" % (filename)
        tree = ElementTree()
        try:
            tree.parse(xml_file)
        except SyntaxError, e:
            message = str(e)
            if message.find("(invalid token)") > 0:
                linesp = message.split("line ", 1)
                linesp = linesp[1].split(",", 1)
                line = int(linesp[0])
                lines_split = xml_file.getvalue().splitlines(0)
                print "Invalid character on line: %r" % (lines_split[line])
            raise e

        root = tree.getroot()

        cix = generateCIXFromXML(root, filename)
        # Append to main cix
        cixmodule = cix.findall("./file/scope")[0]
        for cixelement in cixmodule:
            cix_dom2_module.append(cixelement)

    # Write out the tree
    f = file(os.path.join(os.path.dirname(__file__), "dom2.cix"), "w").write(get_cix_string(cix_dom2))

# When run from command line
if __name__ == '__main__':
    main()
