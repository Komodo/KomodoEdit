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

"""Dojo documentation to Komodo CIX parser.

    Command line tool that parses up dojo's own XML documentation to
    produce a Komodo CIX file. Works by grabbing latest copy of dojo from
    subversion and then parsing the "api.xml" file to produce "dojo.cix".
    
    Requirements:
      * cElementTree    (http://effbot.org/downloads/#cElementTree)
      * svn command line client on the users path
    
    Tested with dojo versions:
      * 0.9.0           (trunk)
"""

import os
import sys
import string
import glob
from pprint import pprint
from optparse import OptionParser

from codeintel2.gencix_utils import *


library_alternatives = {
    "0.9.0": {
        "checkout_url": "http://svn.dojotoolkit.org/dojo/tags/release-0.9.0/util/docscripts",
        "xml_filename": "api.xml"
    },
}

library_name = "Dojo"
library_version = "0.9.0"
library_info = library_alternatives[library_version]

def verifyType(name, typename, DEBUG=False):
    """Ensure the type is a known JS type or a dojo member"""
    typename = typename.lower()
    t = known_javascript_types.get(typename, None)
    if not t:
        # Some types are represented as combinations: "string||dojo.uri.Uri"
        sp = typename.split("||")
        if len(sp) > 0:
            # Just take frist one
            typename = sp[0].strip()
            t = known_javascript_types.get(typename, None)
            if t:
                return t
        if typename.startswith("dojo."):
            return typename
        elif typename and DEBUG:
            print "    %s: Unknown type: %r" % (name, typename)
    return t

def findOrCreateCixNamespace(cixmodule, namespace_items):
    scope = cixmodule
    for name in namespace_items:
        if name not in scope.names:
            # Create it then
            #print "Creating scope: %r, namespace: %r" % (name, namespace_items)
            scope = createCixVariable(scope, name, "Object")
        else:
            scope = scope.names[name]
    return scope

def sortElement(elem1, elem2):
    name1_split = elem1.get("name").split(".")
    name2_split = elem2.get("name").split(".")
    # Use the number of namespaces first.
    if len(name1_split) != len(name2_split):
        return len(name1_split) - len(name2_split)
    # Now compare against the names.
    return cmp(elem1.get("name"), elem2.get("name"))

def processVars(cixmodule, varsElement):
    for elem in sorted(varsElement.getchildren(), sortElement):
        name = elem.get("name")
        if not name:
            print "No name for var element: %r" % (elem, )
            continue
        namespace = name.split(".")
        name = namespace[-1]
        if name[0].lower() not in string.ascii_lowercase and name[0] != "_":
            print "Ignoring invalid element name: %r" % (namespace, )
            continue
        elemType = elem.get("type")
        citdl = None
        summary = None
        if elemType == "Function":
            parentClass = None
            chains = [x for x in elem.getchildren() if x.tag == "chains"]
            for chain_group in chains:
                for chain in chain_group.getchildren():
                    if chain.get("type") == "prototype":
                        parentClass = chain.get("parent")
                        elemType = "Class"
        summaryElem = elem.findall("./summary")
        if summaryElem:
            summaryElem = summaryElem[0]
            summary = summaryElem.text
        if elemType == None:
            elemType = "Variable"
        elif elemType not in ("Function", "Class", "Variable", "Object"):
            citdl = known_javascript_types.get(elemType.lower())
            if elemType.startswith("dojo."):
                citdl = elemType
            elif elemType.lower().startswith("true|"):
                citdl = "Boolean"
            if citdl is None:
                print "Unknown type %r for %r, marking as variable" % (elemType,
                                                           namespace)
            elemType = "Variable"

        scope = findOrCreateCixNamespace(cixmodule, namespace[:-1])
        if name in scope.names:
            continue
        if elemType == "Function":
            cixItem = createCixFunction(scope, name)
            returns = elem.get("returns")
            if returns:
                returns = verifyType(name, returns)
                addCixReturns(cixItem, returns)
        elif elemType == "Class":
            cixItem = createCixClass(scope, name)
        elif elemType == "Variable":
            cixItem = createCixVariable(scope, name, citdl)
        elif elemType == "Object":
            cixItem = createCixVariable(scope, name, "Object")
        else:
            raise Exception("Unknown cix element type %r for %r" % (elemType,
                                                                    namespace))
        if summary:
            setCixDoc(cixItem, summary, parse=True)
        #print "%-10s %s" % (elemType, name)

def generateCIXFromXML(root):
    # Find all main doc namespaces
    cix = createCixRoot(name="%s_v%s" % (library_name,
                                         library_version.replace(".", "")),
                        description="%s JavaScript library - version %s" % (
                                         library_name, library_version))
    cixfile = createCixFile(cix, "", lang="JavaScript")

    # Add the module namespaces.
    for element in root.getchildren():
    #for group in root.findall('./method'):
        if element.tag != "resource":
            print "Ignoring xml element: %r" % (element, )
            continue
        module_name = element.get("project")
        cixmodule = createOrFindCixModule(cixfile, module_name, lang="JavaScript")
        for child in element.getchildren():
            if child.tag == "requires":
                # Ignore the require elements.
                continue
            assert(child.tag == "vars")
            processVars(cixmodule, child)
    return cix

def updateCix(filename, content, updatePerforce=False):
    if updatePerforce:
        print os.popen("p4 edit %s" % (filename)).read()
    file(filename, "w").write(content)
    if updatePerforce:
        diff = os.popen("p4 diff %s" % (filename)).read()
        if len(diff.splitlines()) <= 1 and diff.find("not opened on this client") < 0:
            print "No change, reverting: %s" % os.popen("p4 revert %s" % (filename)).read()

# Main function
def main(cix_filename, updatePerforce=False):
    # 
    # svn checkout of dojo trunk
    co_dir = os.path.abspath("dojo_svn")
    remove_directory(co_dir)
    p = os.popen("svn co %s dojo_svn" % (library_info["checkout_url"], ))
    # Read, to ensure we don't get a broken pipe before everything is done
    svn_output = p.read()
    try:
        api_filename = os.path.join(co_dir, library_info["xml_filename"])
        tree = ElementTree()
        tree.parse(api_filename)
        root = tree.getroot()
        cixroot = generateCIXFromXML(root)
    finally:
        # Finally, remove the temporary svn directory
        remove_directory(co_dir)
        #pass

    updateCix(cix_filename, get_cix_string(cixroot), updatePerforce)

# When run from command line
if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-u", "--update", dest="update_perforce",
                      action="store_true", help="edit perforce cix for this file")
    (opts, args) = parser.parse_args()

    cix_filename = "dojo.cix"
    if opts.update_perforce:
        scriptpath = os.path.dirname(sys.argv[0])
        if not scriptpath:
            scriptpath = "."
        scriptpath = os.path.abspath(scriptpath)

        cix_directory = scriptpath
        # Get main codeintel directory
        for i in range(4):
            cix_directory = os.path.dirname(cix_directory)
        cix_filename = os.path.join(cix_directory, "lib", "codeintel2", "catalogs", cix_filename)
    main(cix_filename, opts.update_perforce)
