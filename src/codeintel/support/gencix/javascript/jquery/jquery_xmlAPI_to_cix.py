#!/usr/bin/env python
# Copyright (c) 2010 ActiveState Software Inc.
# See LICENSE.txt for license details.
#
# Contributers (aka Blame):
#  - Todd Whiteman
#

"""jQuery JavaScript support for Code Intelligence.

    Command line tool that parses up jQuery XML API to produce a Komodo
    CIX file. Works by parsing the xml file to produce "jQuery.cix".

    Requirements:
      * cElementTree    (http://effbot.org/downloads/#cElementTree)
"""

import os
import string
import urllib
from optparse import OptionParser

# Shared code for cix generation
from codeintel2.gencix_utils import *


library_alternatives = {
    "1.12.1": {
        "download_url": "http://api.jquery.com/resources/api.xml",
        "xml_filename": "jquery-docs-xml_v1.12.1.xml",
    },
    "1.9.1": {
        "download_url": "http://api.jquery.com/resources/api.xml",
        "xml_filename": "jquery-docs-xml_v191.xml",
    },
    "1.6.1": {
        "download_url": "http://api.jquery.com/api/",
        "xml_filename": "jquery-docs-xml_v161.xml",
    },
    "1.5.1": {
        "download_url": "http://api.jquery.com/api/",
        "xml_filename": "jquery-docs-xml_v151.xml",
    },
}

library_name = "jQuery"
library_version = "1.12.1"
library_info = library_alternatives[library_version]
base_filepath = os.path.dirname(os.path.abspath(__file__))
library_filepath = os.path.join(base_filepath, library_info["xml_filename"])


def getContent():
    # Gets the file contents, downloading from the website if necessary.
    if not os.path.exists(library_filepath):
        urlOpener = urllib.urlopen(library_info["download_url"])
        file(library_filepath, "w").write(urlOpener.read())
    return file(library_filepath).read()

def getTextFromNode(node):
    text = []
    if node.text:
        text.append(node.text.strip())
    for elem in node:
        print "  here"
        text.append(getTextFromNode(elem))
    if node.tail:
        text.append(node.tail.strip())
    return ' '.join(text)

# Search for information about the argument name given
def findTypeInfo(name, docsplit):
    for text in docsplit[:-1]:  # Last one is the rest of the documentation
        sp = text.split(" ", 1)
        if len(sp) == 2:
            if sp[0].strip() == name:
                return (None, sp[1])
    return (None, None)

def fixupJQueryScope(scope):
    # Bug 75112 - noConflict returns the jQuery object itself.
    noConflict = scope.names.get("noConflict")
    if noConflict is not None:
        noConflict.set("returns", "$")
    else:
        print "fixups:: couldn't find 'noConflict' element"

def generateCIXFromXML(root):
    # Find all main doc namespaces
    cix = createCixRoot(name=library_name,
                        description="%s JavaScript library - version %s" % (
                                         library_name, library_version))
    cixfile = createCixFile(cix, "", lang="JavaScript")
    cixmodule = createCixModule(cixfile,
                                "%s_v%s" % (library_name,
                                            library_version.replace(".", "")),
                                lang="JavaScript")

    # For jQuery, everything is an operation using the jQuery object.
    # Create this jQuery object now, everything will be assigned to it!
    jqueryScope = createCixClass(cixmodule, "jQuery")
    ctor = createCixFunction(jqueryScope, "jQuery", attributes="__ctor__")
    ctor.set("signature", "jQuery(arg <String|Element|Array of Elements|Function|jQuery>, context <Element|jQuery>) -> jQuery")
    ctor.set("doc", """\
String: Create DOM elements on-the-fly from the provided String of raw HTML.
Element|Array: Wrap jQuery functionality around single or multiple DOM Element(s).
Function: To be executed when the DOM document has finished loading.

If 'context' is specified, accepts a string containing a CSS or basic XPath selector
which is then used to match a set of elements.""")

    # "$" is a reference to the jQuery class.
    alt_scope = createCixVariable(cixmodule, "$", )
    alt_scope.set("citdl", "jQuery")

    # Add the methods.
    #for element in root.getchildren():
    for element in root.findall('./entries/entry'):
        elementname = element.get("name")
        if element.get("type") in ("method", "property", "selector"):
            cixscope = jqueryScope
            print "Generating CIX for %s: %r" % (element.get("type"), elementname)
            sp = elementname.split(".")
            if len(sp) > 1 and sp[0] in ("$", "jQuery"):
                sp = sp[1:]
                elementname = sp[0]
            if len(sp) > 1:
                okay = False
                # Example navigator.language
                for subname in sp[:-1]:
                    cixscope = cixscope.names.get(subname)
                    if cixscope is None:
                        break
                else:
                    okay = True
                if not okay:
                    print ("Ignoring namespace: %r" % (elementname, ))
                    continue
                elementname = sp[-1]

            isFunction = False
            if element.get("type") == "property":
                createCixMethod = createCixVariable
            else:
                createCixMethod = createCixFunction
                isFunction = True
            cixelement = createCixMethod(cixscope, elementname)

            # Add the documentation.
            descnodes = element.findall('./desc')
            if descnodes:
                if len(descnodes) != 1:
                    raise "Too many docnodes for: %r" % elementname
                doc = getTextFromNode(descnodes[0])
                if doc:
                    setCixDoc(cixelement, doc, parse=True)

            if element.get("private") is not None:
                cixelement.set("attributes", "private __hidden__")

            citdl = standardizeJSType(element.get("return"))
            if isFunction:
                if citdl:
                    if citdl == "jQuery":
                        # Use "$" instead of "jQuery" to better support method
                        # chaining, see bug 88129.
                        citdl = "$"
                    cixelement.set("returns", citdl)
                # See if there are arguments.
                argElements = element.findall('./signature/argument')
                param_names = [ x.get("name") for x in argElements ]
                signature = "%s(%s)" % (elementname, ", ".join(param_names))
                if citdl:
                    signature += " -> %s" % (citdl, )
                setCixSignature(cixelement, signature)
                for argElement in argElements:
                    addCixArgument(cixelement,
                                   argElement.get("name"),
                                   standardizeJSType(argElement.get("type")),
                                   getTextFromNode(argElement.findall("desc")[0]))
            else:
                # It's a variable.
                if citdl:
                    cixelement.set("citdl", citdl)
        else:
            print "Unknown entry type: %r" % (element.get('type'), )

    fixupJQueryScope(jqueryScope)

    return cix

def main(cix_filename):
    getContent()
    tree = ElementTree()
    tree.parse(library_filepath)
    root = tree.getroot()

    cixtree = generateCIXFromXML(root)
    file(cix_filename, "w").write(get_cix_string(cixtree))

# When run from command line
if __name__ == '__main__':
    parser = OptionParser()
    (opts, args) = parser.parse_args()

    cix_filename = "%s.cix" % (library_name.lower(), )
    main(cix_filename)
