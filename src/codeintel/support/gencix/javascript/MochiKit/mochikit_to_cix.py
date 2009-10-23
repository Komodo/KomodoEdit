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

""" MochiKit documentation to Komodo CIX parser

Command line tool that parses up MochiKit's own HTML documentation to
produce a Komodo CIX file. Works by grabbing latest copy of mochikit from
svn and then parsing the html documentation to produce "mochikit.cix".

Requirements:
  * BeautifulSoup   (http://www.crummy.com/software/BeautifulSoup/)
  * cElementTree    (http://effbot.org/downloads/#cElementTree)
  * svn command line client on the users path

Tested with MochiKit versions:
  * 1.3.1           (default)
  * trunk - 1.4.0   (change svn co command for this version)
"""

import os
import sys
import urllib
from glob import glob
from pprint import pprint
from optparse import OptionParser
from xml.sax.saxutils import unescape

from BeautifulSoup import BeautifulSoup, NavigableString

from codeintel2.gencix_utils import *

MOCHIKIT_VERSION = "1.4.2"

def getSubElementText(elem):
    """Return all the text of elem child elements"""

    return condenseSpaces(''.join([e for e in elem.recursiveChildGenerator()
                                   if isinstance(e,unicode)]))

def getDocTextFromBlockQuote(blockquote):
    """We only grab the first paragraph if the blockquote has multiples"""

    next = blockquote
    while next and isinstance(next, NavigableString):
        next = next.next
    if next and next.name == "p":
        doc = getSubElementText(next)
    else:
        doc = getSubElementText(blockquote)
    return unescape(doc)

def getReturnTypeFromDocString(docstring, className):
    """Try and interpret the docstring to find a return type"""

    # Case insensitive list of marker strings we look for
    docstring = docstring.lower()
    if docstring.startswith("return"):
        sp = docstring.split(None, 6)
        if len(sp) > 2:
            if sp[0] in ("return", "returns"):
                pos = 1
                while pos < len(sp) and sp[pos] in ("a", "an", "new", "the"):
                    # Skip over this one
                    pos += 1
                if pos < len(sp):
                    returnType = sp[pos]
                    # 50% of the time this is bogus, so we try to be smarter
                    # here by only returning known types
                    if returnType in known_javascript_types:
                        #print "  Found return type: %r" % (returnType)
                        return returnType
                    elif returnType.startswith("MochiKit"):
                        #print "  Found return type: %r, from doc: %r" % (returnType, docstring)
                        return returnType
                    else:
                        for name in className.split("."):
                            if name.lower() == returnType:
                                #print "  Found return type: %r, from doc: %r" % (returnType, docstring)
                                return className
                        #print "  Unrecognized return type: %r, from doc: %r" % (returnType, docstring)

def getReturnTypeFromBlockQuote(blockquote):
    """We try and find a '<dt><em>returns</em>:</dt>' section'"""

    # dl -> dt -> em
    for dl_tag in blockquote.findAll("dl", recursive=False):
        for dt_tag in dl_tag.findAll("dt", recursive=False):
            for em_tag in dt_tag.findAll("em", recursive=False):
                if getSubElementText(em_tag) == "returns":
                    # we have a winner
                    dt_next = dt_tag.nextSibling
                    while dt_next and isinstance(dt_next, NavigableString):
                        dt_next = dt_next.next
                    if dt_next is not None and dt_next.name == "dd":
                        for a_tag in dt_next.findAll("a", recursive=False):
                            return getSubElementText(a_tag)

# Objects, classes, variables already created
cix_scopes = {}

def processSection(cix_blob, cix_module, section_type, div_tag):
    logDebugSeen = False
    for p_tag in div_tag.findAll("p", recursive=False):
        ref_tags = p_tag.findAll(attrs={"class":"mochidef reference"}, recursive=False)
        if not ref_tags:
            continue
        if len(ref_tags) != 1:
            raise "Invalid number of reference tags found: %d" % (len(ref_tags))
        signature = ref_tags[0].string
        nextsib = p_tag.nextSibling
        while isinstance(nextsib, NavigableString):
            nextsib = nextsib.nextSibling
        if nextsib.name == "blockquote":
            # Documentation
            blockquote = nextsib
            doc = getDocTextFromBlockQuote(blockquote)
        else:
            raise "Could not find doc tag: %s" % (nextsib.name)

        if MOCHIKIT_VERSION == "1.3.1" and not logDebugSeen and \
                             signature.find("logDebug") >= 0:
            signature = signature.replace("logDebug", "log")
            logDebugSeen = True
        # We have the signature and the doc, work out the real names
        sig_split = signature.split("(", 1)
        namespace = sig_split[0]
        name_split = namespace.split(".")
        name = name_split[-1]

        if section_type == "Errors":
            print "%s: variable: %r" % (section_type, name)
            cix_element = createCixVariable(cix_module, name)
        elif section_type == "Constructors":
            # A class or prototype function
            if len(name_split) == 1:
                # It's a class
                print "%s: class: %r" % (section_type, name)
                cix_element = createCixClass(cix_module, name)
                cix_scopes[name] = cix_element
                # Add function constructor
                if len(sig_split) > 1:
                    cix_function = createCixFunction(cix_element, name)
                    addCixAttribute(cix_function, "__ctor__")
                    setCixSignature(cix_function, signature)
                    setCixDoc(cix_function, doc, parse=True)
                # else: # It's not really a function signature then
            elif "prototype" in name_split:
                # Class function, find the class it's for
                print "%s: class prototype: %r" % (section_type, name)
                parentname = ".".join(name_split[:-2])
                cix_class = cix_scopes.get(parentname, None)
                if cix_class is None:
                    raise "Could not find scope: %r for: %r" % (parentname, namespace)
                cix_element = createCixFunction(cix_class, name)
                setCixSignature(cix_element, "%s(%s" % (name, sig_split[1]))
            else:
                parentname = ".".join(name_split[:-1])
                cix_class = cix_scopes.get(parentname, None)
                if cix_class is None:
                    raise "Could not find scope: %r for: %r" % (parentname, namespace)
                if len(sig_split) > 1:
                    print "%s: class static function: %r" % (section_type, name)
                    cix_element = createCixFunction(cix_class, name)
                    setCixSignature(cix_element, "%s(%s" % (name, sig_split[1]))
                else:
                    print "%s: class static variable: %r" % (section_type, name)
                    cix_element = createCixVariable(cix_class, name)
        elif section_type in ("DOM Custom Event Object Reference"):
            # Special handling for the MochiKit.Signal.Event documentation
            cix_event = cix_scopes.get("Event", None)
            if cix_event is None:
                print "%s: Event scope" % (section_type)
                cix_event = createCixClass(cix_module, "Event")
                cix_scopes["Event"] = cix_event
            if len(sig_split) > 1:
                print "%s: function: %r" % (section_type, name)
                cix_element = createCixFunction(cix_event, name)
                setCixSignature(cix_element, "%s(%s" % (name, sig_split[1]))
            else:
                print "%s: variable: %r" % (section_type, name)
                cix_element = createCixVariable(cix_event, name)
        #elif section_type in ("Functions", "Signal API Reference", "Objects",
        #                      "Style Functions", "Style Objects"):
        # XXX - "Style Functions" and "Style Objects" have been depreciated,
        #       they were functions in MochiKit 1.3.X and below, but were
        #       moved to MochiKit.Style in 1.4.X 
        else:
            if len(sig_split) > 1:
                print "%s: function: %r" % (section_type, name)
                cix_element = createCixFunction(cix_module, name)
            else:
                print "%s: variable: %r" % (section_type, name)
                cix_element = createCixVariable(cix_module, name)
        #else:
        #    raise "Unhandled section type: %r" % (section_type)
        setCixDoc(cix_element, doc, parse=True)
        if cix_element.get("ilk", None) == "function":
            returnType = getReturnTypeFromBlockQuote(blockquote)
            if not returnType:
                # See if we can't fudge it from the given documentation
                returnType = getReturnTypeFromDocString(doc, cix_module.get("name"))
            # Override these two functions, as we get it wrong, see bug:
            # http://bugs.activestate.com/show_bug.cgi?id=59467
            if cix_element.get("name", None) in ("toRGBString", "toHSLString"):
                returnType = "string"

            if returnType:
                returnType = standardizeJSType(returnType.rstrip("()"))
                addCixReturns(cix_element, returnType)
                setCixSignature(cix_element, "%s(%s => %s" % (name, sig_split[1], returnType))
            else:
                setCixSignature(cix_element, "%s(%s" % (name, sig_split[1]))

        # All done, now we need to create an alias/link from main scope
        # First, find that scope, building up a name list on the way
        scope_path = "MochiKit.%s.%s" % (cix_module.get("name"), cix_element.get("name"))
        createCixVariable(cix_blob, cix_element.get("name"), vartype=scope_path)

def processDivTags(cix_blob, cix_module, h1_tag):
    for div_tag in h1_tag.findNextSiblings("div"):
        section_type = getSubElementText(div_tag.h2)
        # section_type will be on of Errors, Contructors, Functions
        processSection(cix_blob, cix_module, section_type, div_tag)

# Soup parsing of API properties
def parseWithSoup(cix_root, scopename, data):
    soup = BeautifulSoup(data, convertEntities=BeautifulSoup.XML_ENTITIES)
    # <h1><a id="api-reference" name="api-reference">API Reference</a></h1>
    api_references = soup.html.body.findAll(attrs={'id':"api-reference"}, limit=1)
    if api_references:
        ref_tag = api_references[0]
        h1_tag = ref_tag.parent
        #print h1_tag
        #<variable name="MochiKit" citdl="Object">
        cix_file = createCixFile(cix_root, "MochiKit/%s.js" % (scopename), lang="JavaScript")
        cix_blob = createCixModule(cix_file, scopename + ".js", "JavaScript")
        mochikit_variable = createCixVariable(cix_blob, "MochiKit", vartype="Object")
        scope_variable = createCixVariable(mochikit_variable, scopename, vartype="Object")
        processDivTags(cix_blob, scope_variable, h1_tag)

# Main function
def main(cix_filename):
    cix_root = createCixRoot(name="MochiKit", description="A lightweight JavaScript library - v%s" % (MOCHIKIT_VERSION))

    # svn checkout of MochiKit trunk
    co_dir = os.path.abspath("mochikit_svn")
    remove_directory(co_dir)
    p = os.popen("svn co http://svn.mochikit.com/mochikit/tags/MochiKit-%s mochikit_svn" % (MOCHIKIT_VERSION))

    # Read, to ensure we don't get a broken pipe before everything is done
    svn_output = p.read()

    try:
        # parse html
        for filename in glob(os.path.join(co_dir, "doc", "html", "MochiKit", "*.html")):
            scopename = os.path.basename(filename).rsplit(".", 1)
            print "MochiKit." + scopename[0]
            data = file(filename).read()
            filename = filename.replace(".html", ".js")
            parseWithSoup(cix_root, scopename[0], data)
    
        # Write out the tree
        cix_xml = get_cix_string(cix_root)
        file(cix_filename, "w").write(cix_xml)
        #print cix_xml
    finally:
        # Finally, remove the temporary svn directory
        remove_directory(co_dir)
        pass

def _test():
#    soup = BeautifulSoup("""
#<blockquote>
#<p>Do a simple <tt class="docutils literal"><span class="pre">XMLHttpRequest</span></tt> to a URL and get the response
#as a JSON <a class="footnote-reference" href="#id10" id="id5" name="id5">[4]</a> document.</p>
#<dl class="docutils">
#<dt><tt class="docutils literal"><span class="pre">url</span></tt>:</dt>
#<dd>The URL to GET</dd>
#<dt><em>returns</em>:</dt>
#<dd><a class="mochiref reference" href="#fn-deferred">Deferred</a> that will callback with the evaluated JSON <a class="footnote-reference" href="#id10" id="id6" name="id6">[4]</a>
#response upon successful <tt class="docutils literal"><span class="pre">XMLHttpRequest</span></tt></dd>
#</dl>
#</blockquote>
#""")
#    print getReturnTypeFromBlockQuote(soup.findAll("blockquote")[0])
    #print soup.findAll("blockquote")[0]
    #print soup
    pass

# When run from command line
if __name__ == '__main__':

    parser = OptionParser()
    parser.add_option("-u", "--update", dest="update",
                      action="store_true", help="update the catalogs source code")
    (opts, args) = parser.parse_args()

    cix_filename = "mochikit.cix"
    if opts.update:
        scriptpath = os.path.dirname(sys.argv[0])
        if not scriptpath:
            scriptpath = "."
        scriptpath = os.path.abspath(scriptpath)

        cix_directory = scriptpath
        # Get main codeintel directory
        for i in range(4):
            cix_directory = os.path.dirname(cix_directory)
        cix_filename = os.path.join(cix_directory, "lib", "codeintel2", "catalogs", cix_filename)

    main(cix_filename)
