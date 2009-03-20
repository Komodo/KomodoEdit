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

"""jQuery JavaScript support for Code Intelligence.

    Command line tool that parses up jQuery XML API, which is already produced
    by the third-party 'createjQueryXMLDocs.py' script, to produce a Komodo
    CIX file. Parses the xml file to produce a "jquery.cix".

    createjQueryXMLDocs.py info is:
      * http://dev.jquery.com/browser/trunk/tools/wikiapi2xml

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
    "1.3.2": {
        "download_url": "http://www.exfer.net/jquery/createjQueryXMLDocs.py?version=1.3.2",
        "xml_filename": "jquery-docs-xml_v132.xml",
    },
    "1.2.3": {
        "download_url": "http://www.exfer.net/jquery/createjQueryXMLDocs.py?version=1.2.3",
        "xml_filename": "jquery-docs-xml_v123.xml",
    },
}

library_name = "jQuery"
library_version = "1.3.2"
library_major_minor_version = library_version.rsplit(".", 1)[0]
library_info = library_alternatives[library_version]
base_filepath = os.path.dirname(os.path.abspath(__file__))
library_filepath = os.path.join(base_filepath, library_info["xml_filename"])


def getContent():
    # Gets the file contents, downloading from the website if necessary.
    if not os.path.exists(library_filepath):
        urlOpener = urllib.urlopen(library_info["download_url"])
        file(library_filepath, "w").write(urlOpener.read())
    return file(library_filepath).read()


# Search for information about the argument name given
def findTypeInfo(name, docsplit):
    for text in docsplit[:-1]:  # Last one is the rest of the documentation
        sp = text.split(" ", 1)
        if len(sp) == 2:
            if sp[0].strip() == name:
                return (None, sp[1])
    return (None, None)

def generateCIXFromXML(root):
    # Find all main doc namespaces
    cix = createCixRoot(name="%s_v%s" % (library_name,
                                         library_version.replace(".", "")),
                        description="%s JavaScript library - version %s" % (
                                         library_name, library_version))
    cixfile = createCixFile(cix, "", lang="JavaScript")
    cixmodule = createCixModule(cixfile,
                                "%s_v%s" % (library_name,
                                            library_version.replace(".", "")),
                                lang="JavaScript")

    # For jQuery, everything is an operation using the jQuery object.
    # Create this jQuery object now, everything will be assigned to it!
    cixscope = createCixClass(cixmodule, "jQuery")
    ctor = createCixFunction(cixscope, "jQuery", attributes="__ctor__")
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
    for categoryElem in root.getchildren():
        if categoryElem.tag != "cat":
            print "Unknown category tag: %r" % (categoryElem.tag, )
            continue
        category = categoryElem.get("value")
        print "%r" % (category, )
        for subCategoryElem in categoryElem.getchildren():
            if subCategoryElem.tag != "subcat":
                print "Unknown subcategory tag: %r" % (subCategoryElem.tag, )
                continue
            subcategory = subCategoryElem.get("value")
            print "  %r" % (subcategory, )
            for element in subCategoryElem.getchildren():
                elementname = element.get("name")
                scope = cixscope
                if element.tag in ("function", "property"):
                    print "    %r: %r" % (element.tag, element.get("name"), )
                    sp = elementname.split(".")
                    if sp[0] == "jQuery":
                        if len(sp) == 1:
                            print "      ** Ignoring this function: %r **" % (sp[0], )
                            continue
                        sp = sp[1:]
                    elementname = sp[0]
                    if len(sp) > 1:
                        # Example navigator.language
                        if len(sp) > 2:
                            raise "Namespace too long: %r" % elementname
                        subname = sp[0]
                        if subname not in cixscope.names:
                            print "      ** Ignoring this function: %r **" % (subname, )
                            #print sorted(cixscope.names.keys())
                            continue
                        scope = cixscope.names[subname]
                        elementname = sp[1]

                    if elementname in scope.names:
                        print "      ** Element already exists in scope, ignoring **"

                    isFunction = False
                    if element.tag == "property":
                        createCixMethod = createCixVariable
                    else:
                        isFunction = True
                        createCixMethod = createCixFunction
                    cixelement = createCixMethod(scope, elementname)

                    # Add the documentation.
                    descnodes = element.findall('./desc')
                    if descnodes:
                        if len(descnodes) != 1:
                            raise "Too many docnodes for: %r" % elementname
                        if descnodes[0].text:
                            setCixDoc(cixelement, descnodes[0].text, parse=True)

                    if element.get("private") is not None:
                        cixelement.set("attributes", "private __hidden__")

                    citdl = standardizeJSType(element.get("return"))
                    if citdl:
                        if citdl in ("Any", ):
                            citdl = None
                        #else:
                        #    print "        citdl: %r" % (citdl, )
                    if isFunction:
                        if citdl:
                            cixelement.set("returns", citdl)
                        # See if there are arguments.
                        params = element.findall('./params')
                        param_names = [ x.get("name") for x in params ]
                        signature = "%s(%s)" % (elementname, ", ".join(param_names))
                        if citdl:
                            signature += " -> %s" % (citdl, )
                        setCixSignature(cixelement, signature)
                        for param in params:
                            addCixArgument(cixelement,
                                           param.get("name"),
                                           standardizeJSType(param.get("type")),
                                           param.findall("desc")[0].text)
                    else:
                        # It's a variable.
                        if citdl:
                            cixelement.set("citdl", citdl)
                elif element.tag == "selector":
                    pass    # Not much we can do here...
                else:
                    print "Unknown tag: %r" % (element.tag, )
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
    parser.add_option("-u", "--update", dest="update_scc_catalog",
                      action="store_true", help="edit perforce cix for this file")
    (opts, args) = parser.parse_args()

    cix_filename = "%s_%s.cix" % (library_name.lower(),
                                library_major_minor_version)
    if opts.update_scc_catalog:
        # The generated cix will go inside the codeintel2/catalogs dir.
        scriptpath = os.path.dirname(sys.argv[0])
        if not scriptpath:
            scriptpath = "."
        scriptpath = os.path.abspath(scriptpath)

        cix_directory = scriptpath
        # Get main codeintel directory
        for i in range(4):
            cix_directory = os.path.dirname(cix_directory)
        cix_filename = os.path.join(cix_directory, "lib", "codeintel2", "catalogs", cix_filename)
    else:
        cix_filename = os.path.join(base_filepath, cix_filename)
    main(cix_filename)
