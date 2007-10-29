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

""" Dojo documentation to Komodo CIX parser.

Command line tool that parses up dojo's own JSON documentation to
produce a Komodo CIX file. Works by grabbing latest copy of dojo from subversion
and then parsing the JSON files to produce "dojo.cix".

Requirements:
  * cElementTree    (http://effbot.org/downloads/#cElementTree)
  * svn command line client on the users path

Tested with dojo versions:
  * 0.4.0           (trunk)

Dev notes:
    Uses a customized version of simplejson, which uses an ordered dictionary,
    so it processes values in the same order they are read in. Necessary for
    function arguments. This was done by: Adding odict.py to simplejson, and
    then using OrderedDict in simplejson/decoder.py.
"""

import os
import sys
import string
import glob
from pprint import pprint
from optparse import OptionParser

from codeintel2.gencix_utils import *
import simplejson


def print_keys_values(d, depth=0):
    for key, val in d.items():
        print "%s%s: %r" % (" " * depth, key, val)
        if isinstance(val, dict):
            print_keys_values(val, depth+1)

def print_keys(d, depth=0):
    for key, val in d.items():
        print "%s%s" % (" " * depth, key)
        if isinstance(val, dict):
            print_keys(val, depth+1)

def verifyType(name, typename):
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
        elif typename:
            print "    %s: Unknown type: %r" % (name, typename)
    return t

def parse_functions(cixclass, funcdict):
    for funcname, d in funcdict.items():
        #print "  Function: %s" % (funcname)
        cixfunction = createCixFunction(cixclass, funcname)
        #print_keys(d)
        underscore = d.get("_", None)
        if not underscore:
            underscore = d
        meta = underscore.get("meta", None)
        if not meta:
            continue

        # Meta should contain summary, description, parameters, variables, etc..
        # We prefer summary over description.
        doc = meta.get("summary", "")
        if not doc:
            # Could be under description then
            doc = meta.get("description", "")
        if doc:
            setCixDoc(cixfunction, doc, parse=True)

        # Get function parameters, also determines signature
        paramdict = meta.get("parameters", {})
        sigparams = []
        sigoptionals = []
        #print "function %s parameters: %r" % (funcname, paramdict)
        isOptional = False
        hasNLengthArgs = False # "xyz(a, ...)" style
        for paramname, paramtype in paramdict.items():
            paramtype = paramtype.get("type", None)
            sigparamname = paramname
            if paramtype:
                # See if there are special n length args ", ..."
                sp = paramtype.split(",")
                if len(sp) > 1:
                    paramtype = sp[0].strip()
                    extra = sp[1].strip()
                    if extra == "...":
                        hasNLengthArgs = True
                # See if it's an optional arg that specifies a default value
                sp = paramtype.split("=")
                if len(sp) > 1:
                    paramtype = sp[0].strip()
                    sigparamname += "=%s" % (sp[1])
                # Take first paramtype given
                sp = paramtype.split(" ")
                if len(sp) > 1:
                    #print "      Shortening paramtype from: %r to %r" % (paramtype, sp[0])
                    paramtype = sp[0]
                # Remove optional marker
                if paramtype.endswith("?"):
                    # It's optional
                    #print "      paramtype is optional: %r" % (paramtype)
                    paramtype = paramtype.rstrip("?")
                    isOptional = True
                if paramtype.endswith("[]"):
                    # It's an array
                    paramtype = "Array"
                    sigparamname = "%s[]" % sigparamname

            if isOptional:
                sigoptionals.append(sigparamname)
            else:
                sigparams.append(sigparamname)
            if hasNLengthArgs:
                sigoptionals.append("...")
            #print "    Adding function %r argument: %r, type: %r" % (cixfunction.get("name"), paramname, paramtype)
            addCixArgument(cixfunction, paramname, verifyType(funcname, paramtype))
        # The signature tries to have python style
        sig = ", ".join(sigparams)
        if sigoptionals:
            if sig:
                sigparams = [" [,%s" % (sigoptionals[0])]
            else:
                sigparams = ["[%s" % (sigoptionals[0])]
            for optional in sigoptionals[1:]:
                sigparams.append("[,%s" % (optional))
            sig += " ".join(sigparams)
            sig += "]" * len(sigoptionals)
        signature = "%s(%s)" % (funcname, sig)
        setCixSignature(cixfunction, signature)

        # Return value
        returntype = meta.get("returns", {})
        if returntype:
            # Remove some comments that dojo parsing has missed
            #print "returntype: %r" % (returntype)
            if isinstance(returntype, dict):
                print "Returntype unexpectedly is a dictionary: %r" % (returntype)
            else:
                returntype = returntype.rstrip(" */")
                addCixReturns(cixfunction, verifyType(funcname, returntype))

        # Class members
        member_variables = meta.get("protovariables", {})
        #print "member_variables: %r" % (member_variables)
        # List of tuples (variable name, variable type)
        for varname, vartype in member_variables.items():
            # These go into the class
            createCixVariable(cixclass, varname, verifyType(varname, vartype))

        # Class variables
        variables = meta.get("variables", {})
        #print "member_variables: %r" % (member_variables)
        # List of tuples (variable name, variable type)
        if isinstance(variables, dict):
            for varname, vartype in variables.items():
                # These go into the class
                createCixVariable(cixclass, varname, verifyType(varname, vartype))
        elif isinstance(variables, list):
            for varname in variables:
                # These go into the class
                createCixVariable(cixclass, varname)

        # Local function variables
        function_variables = meta.get("this_variables", [])
        if function_variables:
            # Also denotes this as the constructor for the class
            addCixAttribute(cixfunction, "__ctor__")
        for varname in function_variables:
            # Add variables defined in the function
            if varname not in member_variables:
                # These go into the function
                createCixVariable(cixfunction, varname)

        # Inheritance
        inherits = meta.get("inherits", None)
        if inherits:
            # This is for the class
            #print "  Inherits: %s" % (inherits)
            #if not isinstance(inherits, list):
            #    inherits = [inherits]
            for basename in inherits:
                if basename.startswith("[") and basename.endswith("]"):
                    sp = basename[1:-1].split(", ")
                    for basename in sp:
                        addClassRef(cixclass, basename)
                else:
                    addClassRef(cixclass, basename)

        # We ignore "object_inherits"

        # Print anything we've missed
        for key, val in meta.items():
            if key not in ("this", "src", "summary", "description",
                           "parameters", "returns", "prototype",
                           "prototype_chain",
                           "protovariables", "prototype_variables",
                           "this_variables", "inherits", "this_inherits",
                           "variables", "instance_variables",
                           "object_inherits", "call_chain"):
                print "     Not handled: %s: %r" % (key, val)

        #print_keys_values(meta, depth=3)
        #print_keys_values(meta.get("src", {}), depth=3)

def parse_class(cixclass, meta, namespace):
    # key is the dojo namespace (ex: "dojo.animation.Timer")
    # val is dictionary containing the namespace properties
    for key, val in meta.items():
        if key == "requires":
            pass
        elif key == "functions":
            parse_functions(cixclass, val)
        else:
            print "  Unhandled key: %s" % (key)
            #print val

def parse_classes(cixfile, dojomodule, d):
    # key is the dojo namespace (ex: "dojo.animation.Timer")
    # val is dictionary containing the namespace properties
    for key, val in d.items():
        if key.endswith("._"):
            print "Ingoring: %s" % (key)
            continue
        namespace = key
        namesplit = namespace.split(".")
        classname = namesplit[-1]
        namespace = ".".join(namesplit[:-1])
        # Ensure dojo namespace goes into dojo blob
        if not key or not namespace or \
           (len(namesplit) == 2 and classname[0] in string.uppercase):
            # Create this under dojo module
            print "Placing component %s (%r) under dojo" % (classname, namesplit)
            cixmodule = dojomodule
        else:
            if len(namesplit) == 2:
                cixmodule = createOrFindCixModule(cixfile, key, lang="JavaScript")
            else:
                cixmodule = createOrFindCixModule(cixfile, namespace, lang="JavaScript")
        print "Class: %s in module: %s" % (classname, namespace)
        meta = val.get("meta", None)
        # meta contains package info (description, functions, requires, etc...)
        if meta:
            cixclass = createCixClass(cixmodule, classname)
            parse_class(cixclass, meta, namespace)
        else:
            print "  no meta!"

def parseJSONFile(cixfile, dojomodule, filename):
    f = file(filename, "rb")
    d = simplejson.load(f)
    #pprint(d)
    parse_classes(cixfile, dojomodule, d)

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
    cixroot = createCixRoot()
    cixfile = createCixFile(cixroot, "dojo.js", lang="JavaScript")
    dojomodule = createCixModule(cixfile, "dojo", lang="JavaScript")

    # svn checkout of dojo trunk
    co_dir = os.path.abspath("dojo_svn")
    remove_directory(co_dir)
    p = os.popen("svn co http://svn.dojotoolkit.org/dojo/trunk/docscripts/output/local/json dojo_svn")
    # Read, to ensure we don't get a broken pipe before everything is done
    svn_output = p.read()

    try:
        #for filename in [directory]:
        for filename in glob.glob(os.path.join(co_dir, "dojo*")):
            parseJSONFile(cixfile, dojomodule, filename)
            #if filename.endswith("dojo.string"):
            #    break
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
        cix_filename = "../../../../lib/codeintel2/catalog/%s" % (cix_filename)
    main(cix_filename, opts.update_perforce)
