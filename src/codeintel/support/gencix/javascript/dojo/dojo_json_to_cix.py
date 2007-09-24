#!/usr/bin/env python
# Copyright (c) 2006 ActiveState Software Inc.
# See LICENSE.txt for license details.
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
  * 0.3.1           (default)

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

def verifyType(typename):
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
    return t

def parse_functions(dojoblob, cixclass, funcdict):
    for funcname, d in funcdict.items():
        #print "  Function: %s" % (funcname)
        namespace = funcname.split(".")
        cixelement = dojoblob
        for name in namespace[:-1]:
            lastcixelement = cixelement
            cixelement = cixelement.names.get(name)
            if cixelement is None:
                print "Creating variable: %s for namespace: %r, under cix element: %r" % (
                        name, namespace[:-1], lastcixelement.get("name"))
                cixelement = createCixVariable(lastcixelement, name, vartype="Object")
        cixclass = cixelement
        method_name = namespace[-1]
        tmpclass = cixclass.names.get(method_name)
        isCtor = False
        if tmpclass is not None:
            # Must be constructor function for the class then
            cixclass = tmpclass
            isCtor = True
        cixfunction = createCixFunction(cixclass, method_name)
        #print_keys(d)
        underscore = d.get("_", None)
        if not underscore:
            continue
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
        for paramname, paramtype in paramdict.items():
            paramtype = paramtype.get("type", None)
            sigparamname = paramname
            if paramtype:
                isOptional = False
                # Remove optional marker
                if paramtype[-1] == "?":
                    # It's optional
                    paramtype = paramtype.rstrip("?")
                    isOptional = True
                if paramtype.endswith("[]"):
                    # It's an array
                    paramtype = "Array"
                    sigparamname = "%s[]" % sigparamname
                if isOptional:
                    sigparamname = "[%s]" % sigparamname
            sigparams.append(sigparamname)
            addCixArgument(cixfunction, paramname, verifyType(paramtype))
        signature = "%s(%s)" % (method_name, ", ".join(sigparams))
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
                addCixReturns(cixfunction, verifyType(returntype))

        # Class members
        member_variables = meta.get("protovariables", {})
        #print "member_variables: %r" % (member_variables)
        # List of tuples (variable name, variable type)
        for varname, vartype in member_variables.items():
            # These go into the class
            createCixVariable(cixclass, varname, verifyType(vartype))

        # Class variables
        variables = meta.get("variables", {})
        #print "member_variables: %r" % (member_variables)
        # List of tuples (variable name, variable type)
        for varname, vartype in variables.items():
            # These go into the class
            createCixVariable(cixclass, varname, verifyType(vartype))

        # Local function variables
        function_variables = meta.get("this_variables", [])
        if function_variables or isCtor:
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
                           "parameters", "returns", "protovariables",
                           "this_variables", "inherits", "this_inherits",
                           "variables", "object_inherits"):
                print "%s%s: %r" % ("     ", key, val)

        #print_keys_values(meta, depth=3)
        #print_keys_values(meta.get("src", {}), depth=3)

def parse_class(dojoblob, cixclass, meta, namespace):
    # key is the dojo namespace (ex: "dojo.animation.Timer")
    # val is dictionary containing the namespace properties
    for key, val in meta.items():
        if   key == "requires":
            pass
        elif key == "functions":
            parse_functions(dojoblob, cixclass, val)
        else:
            print "  Unhandled key: %s" % (key)

def parse_classes(dojoblob, dojomodule, d):
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
        #print "Key: %s" % (key)
        #print "Namespace: %s" % (namespace)
        #if not key or not namespace or \
        #   (len(namesplit) == 2 and classname[0] in string.uppercase):
        #    # Create this under dojo module
        #    print "Placing component %s (%r) under dojo" % (classname, namesplit)
        #    cixmodule = dojomodule
        #else:
        #    if len(namesplit) == 2:
        #        cixmodule = createOrFindCixModule(dojoblob, key, lang="JavaScript")
        #    else:
        #        cixmodule = createOrFindCixModule(dojoblob, namespace, lang="JavaScript")
        cixelement = dojoblob
        for name in namesplit[:-1]:
            subelem = cixelement.names.get(name)
            if subelem is None:
                print "Creating variable: %s for namespace: %r" % (name, namesplit[:-1])
                subelem = createCixVariable(cixelement, name, vartype="Object")
            cixelement = subelem
        print "Class: %s in module: %s" % (classname, namespace)
        meta = val.get("meta", None)
        # meta contains package info (description, functions, requires, etc...)
        if meta:
            cixclass = cixelement.names.get(classname)
            if cixclass is None:
                cixclass = createCixClass(cixelement, classname)
            parse_class(dojoblob, cixclass, meta, namespace)

def parseJSONFile(dojoblob, dojomodule, filename):
    f = file(filename, "rb")
    d = simplejson.load(f)
    #pprint(d)
    parse_classes(dojoblob, dojomodule, d)

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
    cixroot = createCixRoot(name="Dojo", description="Open Source Javascript web development toolkit")
    cixfile = createCixFile(cixroot, "dojo.js", lang="JavaScript")
    dojoblob = createCixModule(cixfile, "dojo", lang="JavaScript")
    dojomodule = createCixVariable(dojoblob, "dojo", vartype="Object")

    # svn checkout of dojo trunk
    co_dir = os.path.abspath("dojo_svn")
    remove_directory(co_dir)
    p = os.popen("svn co http://svn.dojotoolkit.org/dojo/tags/release-0.4.0/docscripts/local_json dojo_svn")
    # Read, to ensure we don't get a broken pipe before everything is done
    svn_output = p.read()

    try:
        #for filename in [directory]:
        for filename in glob.glob(os.path.join(co_dir, "dojo*")):
            parseJSONFile(dojoblob, dojomodule, filename)
    finally:
        # Finally, remove the temporary svn directory
        remove_directory(co_dir)

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
