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

""" Prototype documentation to Komodo CIX parser.

Command line tool that parses up prototype's own HTML documentation to
produce a Komodo CIX file. Works by grabbing latest copy of prototype online
documentation and then parsing the html to produce "prototype.cix".

Requirements:
  * BeautifulSoup   (http://www.crummy.com/software/BeautifulSoup/)
  * cElementTree    (http://effbot.org/downloads/#cElementTree)

Webpage used for documentation:
  * http://www.sergiopereira.com/articles/prototype.js.html
  * (local copy should be within this directory as well)

Tested with prototype versions:
  * 1.4.0           (default)
"""

import os
import sys
import urllib
from pprint import pprint
from optparse import OptionParser

from BeautifulSoup import BeautifulSoup, NavigableString

from codeintel2.gencix_utils import *


#def getSubElementText(elem):
#    result = []
#    for i in elem:
#        result.append(i.string)
#    return condenseSpaces("".join(result))
def getSubElementText(elem):
    """Return all the text of elem child elements"""

    return condenseSpaces(''.join([e for e in elem.recursiveChildGenerator()
                                   if isinstance(e,unicode)]))

def processTableMethods(cix_element, table_tag):
    # Table rows: [u'Method', u'Kind', u'Arguments', u'Description']
    for table_row in table_tag.findAll("tr"):
        row_tags = table_row.findAll("td")
        if row_tags:
            assert(len(row_tags) == 4)
            method = row_tags[0].string
            msplit = method.split("(", 1)
            method_name = msplit[0]
            isConstructor = False
            if method_name == "[ctor]":
                method_name = cix_element.get("name")
                isConstructor = True
            cix_function = createCixFunction(cix_element, method_name)
            if isConstructor:
                addCixAttribute(cix_function, "__ctor__")
            setCixSignature(cix_function, "%s(%s" % (method_name, msplit[1]))
            setCixDoc(cix_function, getSubElementText(row_tags[3]), parse=True)

def processTableProperties(cix_element, table_tag):
    # Table rows: [u'Property', u'Type', u'Description']
    # Table rows: [u'Property', u'Type', u'Kind', u'Description']
    for table_row in table_tag.findAll("tr"):
        row_tags = table_row.findAll("td")
        if row_tags:
            assert(len(row_tags) in (3, 4))
            name = row_tags[0].string
            #print "name: %r" % name
            #print "type: %r" % getSubElementText(row_tags[1]).split("(")[0]
            #print "doc: %r" % getSubElementText(row_tags[-1])
            cix_variable = createCixVariable(cix_element, name)
            vartype = standardizeJSType(getSubElementText(row_tags[1]).split("(")[0])
            addCixType(cix_variable, vartype)
            setCixDoc(cix_variable, getSubElementText(row_tags[-1]), parse=True)
            #print

def processTableTag(cix_element, table_tag):
    header_tags = [ tag.string for tag in table_tag.findAll("th") ]
    #print header_tags
    if "Method" in header_tags:
        processTableMethods(cix_element, table_tag)
    elif "Property" in header_tags:
        processTableProperties(cix_element, table_tag)
    else:
        raise "Unknown header tags: %r" % (header_tags)

def processScopeFields(cix_element, h4_tag):
    nextsib = h4_tag
    while 1:
        nextsib = nextsib.nextSibling
        if not nextsib:
            break
        elif isinstance(nextsib, NavigableString):
            pass
        elif nextsib.name in ("h4", "a"):
            break
        elif nextsib.name == "p":
            for table_tag in nextsib.findAll("table"):
                processTableTag(cix_element, table_tag)

# Objects, classes, variables already created
cix_scopes = {}

def processScope(cix_module, h4_tag):
    spans = h4_tag.findAll("span", limit=1)
    if len(spans) == 1:
        h4_text = getSubElementText(h4_tag)
        h4_text_split = h4_text.split()
        scopeName = spans[0].string
        scopeNames = scopeName.split(".")
        if len(scopeNames) > 1:
            # Find the scope for this
            parentScopeName = ".".join(scopeNames[:-1])
            cix_module = cix_scopes.get(parentScopeName, None)
            if cix_module is None:
                raise "Could not find scope: %r for: %r" % (parentScopeName, scopeName)
        if h4_text_split[0] == "The" and h4_text_split[-1] == "class":
            print "Class:",
            cix_element = createCixClass(cix_module, scopeNames[-1])
        else:
            print "Object:",
            cix_element = createCixVariable(cix_module, scopeNames[-1])
        cix_scopes[scopeName] = cix_element
        print "%s - %s" % (scopeName, h4_text)
        processScopeFields(cix_element, h4_tag)

def processRefTags(cix_module, p_tag):
    for h4_tag in p_tag.findNextSiblings("h4"):
        #print sibling
        processScope(cix_module, h4_tag)

cix_info_from_name = {
    "$":   { "returnType" : "Element",    # Can also return an Array when called with multiples
             "args" : [("elementId", "String")],
             "signature" : "$(elementId [, ...]) --> Element"
             },
    "$F":  { "returnType" : "String",
             "args" : [("element", "Element")],
             "signature" : "$F(element/elementId]) --> String"
             },
    "$A":  { "returnType" : "Array",
             "args" : [("obj", "Object")],
             "signature" : "$A(obj) --> Array"
             },
    "$H":  { "returnType" : "Hash",
             "args" : [("obj", "Object")],
             "signature" : "$H(obj) --> Hash"
             },
    "$R":  { "returnType" : "ObjectRange",
             "args" : [("lowerBound", "Number"),
                       ("upperBound", "Number"),
                       ("excludeBounds", "Boolean"),],
             "signature" : "$R(lowerBound, upperBound, excludeBounds) --> ObjectRange"
             },
    "Try.these": { "returnType" : None,
                   "args" : [("func1", "Function")],
                   "signature" : "these(func1, [, ...])"
                   },
}

def processH4Tag(cix_module, h4_tag):
    # These are all utility functions:
    # <h4>Using the <span class="functionName">$()</span> function</h4>
    # <p>
    #        The <span class="code">$()</span> function is a handy shortcut to the all-too-frequent <span class="code">document.getElementById()</span> function
    #        of the DOM. Like the DOM function, this one returns the element that has the id passed as an argument.
    # </p>
    span_tags = h4_tag.findAll("span", attrs={"class": "functionName"})
    for span_tag in span_tags:
        nextsib = h4_tag.nextSibling
        while isinstance(nextsib, NavigableString):
            nextsib = nextsib.nextSibling
        p_tag = nextsib
        #print "p_tag:", p_tag
        if p_tag.name == "p":
            cix_element = cix_module
            # We have enough info now
            signature = span_tag.string
            method_name = signature.rstrip("() ")
            # We can probably do better manually here
            info = cix_info_from_name.get(method_name)

            cix_variable = None
            sp = method_name.split(".")
            if len(sp) > 1:
                for name in sp[:-1]:
                    cix_element = createCixVariable(cix_element, name, vartype="Object")
                method_name = sp[-1]
            cix_function = createCixFunction(cix_element, method_name)
            setCixDoc(cix_function, getSubElementText(p_tag), parse=True)

            if info.get("returnType"):
                addCixReturns(cix_function, info.get("returnType"))

            if info.get("signature"):
                setCixSignature(cix_function, info.get("signature"))
            else:
                setCixSignature(cix_function, signature)

            for arg_name, arg_type in info.get("args", []):
                addCixArgument(cix_function, arg_name, arg_type)

def getPrototypeDocsFromWebpage():
    urlOpener = urllib.urlopen("http://www.sergiopereira.com/articles/prototype.js.html")
    return urlOpener.read()
    #return file("prototype.js.html").read()

def updateCix(filename, content, updatePerforce=False):
    if updatePerforce:
        print os.popen("p4 edit %s" % (filename)).read()
    file(filename, "w").write(content)
    if updatePerforce:
        diff = os.popen("p4 diff %s" % (filename)).read()
        if len(diff.splitlines()) <= 1 and diff.find("not opened on this client") < 0:
            print "No change, reverting: %s" % os.popen("p4 revert %s" % (filename)).read()

# Soup parsing of API documentation from webpage
def main(cix_filename, updatePerforce=False):
    data = getPrototypeDocsFromWebpage()
    soup = BeautifulSoup(data)
    cix_root = createCixRoot(name="Prototype", description="JavaScript framework for web development")
    cix_file = createCixFile(cix_root, "prototype", lang="JavaScript")
    cix_module = createCixModule(cix_file, "prototype", lang="JavaScript")

    h4_tags = soup.html.body.div.findAll("h4")
    for h4_tag in h4_tags:
        processH4Tag(cix_module, h4_tag)

    ref_tag = soup.html.body.div.findAll(attrs={'name':"Reference"}, limit=1)[0]
    #print ref_tag
    processRefTags(cix_module, ref_tag)

    # Write out the tree
    updateCix(cix_filename, get_cix_string(cix_root), updatePerforce)

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-u", "--update", dest="update_perforce",
                      action="store_true", help="edit perforce cix for this file")
    (opts, args) = parser.parse_args()

    cix_filename = "prototype.cix"
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
