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

    CIX builder for DOM0 codeintel creation. Code Intelligence XML format. See:
        http://specs.tl.activestate.com/kd/kd-0100.html#xml-based-import-export-syntax-cix

    Command line tool that parses up DOM0 XML specs to produce a Komodo
    CIX file. Works by parsing the xml file of host/browser information
    to produce "dom0.cix". I think this is Firefox at the moment.

    Requirements:
      * cElementTree    (http://effbot.org/downloads/#cElementTree)
"""

import os
import string

# Shared code for cix generation
from codeintel2.gencix_utils import *
#from cix_utils import *

# Search for information about the argument name given
def findTypeInfo(name, docsplit):
    for text in docsplit[:-1]:  # Last one is the rest of the documentation
        sp = text.split(" ", 1)
        if len(sp) == 2:
            if sp[0].strip() == name:
                return (None, sp[1])
    return (None, None)

# Get method information from the documentation text
def getMethodInformation(doctext):
    signature = None
    arguments = {}
    returns = {}
    sp = doctext.split("Syntax: ")
    if len(sp) > 1:
        returnname = None
        s = sp[1]
        begin = s.find("(")
        end = s.find(")")
        if begin < end and end > 0:
            # See if there is a return typ
            returnText = s[:begin]
            rsp = returnText.split("=")
            if len(rsp) > 1:
                returnname = rsp[0].strip()
            # Get argument text
            argsText = s[begin+1:end]
            # Work out the signature
            pos = len(returnText) - 1
            signature = ""
            while pos >=0:
                c = returnText[pos]
                if c not in string.letters and c not in string.digits and \
                   c not in "_":
                    signature = "%s(%s)" % (returnText[pos+1:], argsText)
                    if returnname:
                        signature = "%s => %s" % (signature, returnname)
                    break
                pos -= 1
            # Work out the arguments
            args = [ x.strip() for x in argsText.split(",") ]
            leftover = s[end+1:]
            psplit = leftover.split("Parameters: ")
            if len(psplit) > 1:
                leftover = psplit[1]
                maxsplits = len(args)
                if returnname:
                    maxsplits += 1
                lsplit = leftover.split(". ", maxsplits)
                # See if we can work out the type info
                for arg in args:
                    arguments[arg] = findTypeInfo(arg, lsplit)
                returns[returnname] = findTypeInfo(returnname, lsplit)
                doctext = sp[0] + lsplit[-1]
            else:
                doctext = sp[0] + psplit[0]
    return arguments, returns, signature, doctext

def generateCIXFromXML(root):
    # Find all main doc namespaces
    cix = createCixRoot()
    cixfile = createCixFile(cix, "javascript_dom0", lang="JavaScript")
    cixmodule = createCixModule(cixfile, "*", lang="JavaScript")

    for group in root.findall('./group'):
        namespace = group.attrib["name"]
        if namespace not in ("window", ):
            print "Not writing information for: %r" % (namespace)
            continue

        print "Generating CIX for: %r" % (namespace)
        namespaceDot = namespace + "."
        if namespace == "window":
            createCixVariable(cixmodule, namespace, vartype="Window")
            cixscope = createCixClass(cixmodule, "Window")
        else:
            cixscope = createCixVariable(cixmodule, namespace)
            

        # subnamespaces is used to hold a sub namespace
        # Example: in the window namespace, then there is a navigator namespace
        subnamespaces = {}

        for subgroup in group.findall('./group'):
            groupname = subgroup.attrib["name"]
            #print "  %s:" % (subgroup.attrib["name"])
            if groupname == "Properties":
                createCixMethod = createCixVariable
            elif groupname == "Methods":
                createCixMethod = createCixFunction
            elif groupname == "Event Handlers":
                continue
            else:
                raise "Unknown subgroup name: %s" % (groupname)
                # These are functions:
            for element in subgroup.findall('./element'):
                elementname = element.attrib["name"].replace(namespaceDot, "")
                elementname = elementname.rstrip(" ()")
                sp = elementname.split()
                if len(sp) != 1:
                    if len(sp) == 3 and sp[1] == "and":
                        # Two names in one
                        print "Double element name found: %r" % (elementname)
                        elementnames = (sp[0], sp[2])
                    else:
                        print "Wierd element name, ignoring... %r" % (elementname)
                        continue
                else:
                    elementnames = (elementname, )

                descnodes = element.findall('./description')
                doctext = None
                if descnodes:
                    if len(descnodes) != 1:
                        raise "Too many docnodes for: %r" % elementname
                    doctext = descnodes[0].text

                cixelement = None
                for elementname in elementnames:
                    sp = elementname.split(".")
                    if len(sp) > 1:
                        # Example navigator.language
                        if len(sp) > 2:
                            raise "Namespace too long: %r" % elementname
                        subname = sp[0]
                        cixvariable = subnamespaces.get(subname, None)
                        if cixvariable is None:
                            cixvariable = createCixMethod(cixscope, subname)
                            subnamespaces[subname] = cixvariable
                        cixelement = createCixMethod(cixvariable, sp[1])
                    else:
                        if elementname == "document":
                            cixelement = createCixMethod(cixscope, elementname, vartype="HTMLDocument")
                        else:
                            cixelement = createCixMethod(cixscope, elementname)
                        subnamespaces[elementname] = cixelement
                if cixelement is not None:
                    if groupname == "Methods" and doctext:
                        # See if the documentation shows the arguments
                        #print "elementname: %r" % (elementname)
                        args, ret, sig, doctext = getMethodInformation(doctext)
                        if sig:
                            setCixSignature(cixelement, sig)
                        for argName, argDetails in args.items():
                            if argName:
                                # Remove quotes: bug 58268
                                argName = argName.strip('"\'')
                                argType = standardizeJSType(argDetails[0])
                                argDoc = argDetails[1]
                                addCixArgument(cixelement, argName, argType, argDoc)
                    if doctext:
                        setCixDoc(cixelement, doctext, parse=True)

                #print "    %r" % element.attrib["name"]
                #for desc in element.findall('./description'):
                #    print "      Doc: %r" % desc.text
    return cix

def main():
    tree = ElementTree()
    tree.parse(os.path.join(os.path.dirname(__file__), "dom.xml"))
    root = tree.getroot()

    cix_dom1 = generateCIXFromXML(root)
    # Write out the cix
    f = file(os.path.join(os.path.dirname(__file__), "dom0.cix"), "w").write(get_cix_string(cix_dom1))

# When run from command line
if __name__ == '__main__':
    main()
