#!/usr/bin/env python
# Copyright (c) 2005-2006 ActiveState Software Inc.
#
# Contributors:
#   Eric Promislow (EricP@ActiveState.com)

"""
remove-namespace-redundancy.py -- a utility program that takes a reference
CIX file, and several other modules
"""

import os
from os.path import basename, splitext, isfile, isdir, join
import sys
import getopt
import md5
import re
import logging
import glob
import time
import stat

from codeintel2.common import *
from codeintel2.tree import pretty_tree_from_tree
from codeintel2.util import parseDocSummary

import ciElementTree as ET

from optparse import OptionParser
parser = OptionParser()

usage = "usage: %prog file"
version = "%prog 0.1"
desc = """Sometimes yaml includes the namespace in a class or function name.  Remove it."""
parser = OptionParser(prog="platinfo", usage=usage,
                                    version=version,
                                    description=desc)
parser.add_option("-i", "--in-file", dest="infile")
parser.add_option("-o", "--output-file", dest="outfile")
parser.add_option("-q", "--quiet",
                  action="store_false", dest="verbose", default=True,
                  help="don't print status messages to stdout")
(options, args) = parser.parse_args()

def Usage():   
        print "Usage: %s (-i | --in-file f) (-o | --out-file f)" % sys.argv[0]
        print "   or: %s in-file out-file" % sys.argv[0]
        sys.exit()
        
if not options.infile:
    if len(args) == 0:
        Usage()
    else:
        infile = args[0]
        del args[0]
else:
    infile = options.infile

if options.outfile:
    if len(args) > 0:
        Usage()
    else:
        outfile = options.outfile
elif len(args) == 0:
    Usage()
else:
    outfile = args[0]
    
if infile == outfile:
    print "Trying to overwrite file %s" % outfile
    Usage()

origTree = ET.parse(infile)

adjusted_node = 0
def check_redundant_namespace(elem):
    global adjusted_node
    if not elem:
        return
    elif elem.get("ilk") == "namespace":
        top_name = elem.get("name")
        if top_name:
            top_name_double_colon = top_name + "::"
            for child in elem:
                name = child.get("name")
                if name and name.startswith(top_name_double_colon):
                    child.set("name", name[len(top_name_double_colon):])
                    adjusted_node += 1
    for child in elem:
        check_redundant_namespace(child)

lim1 = 250
lim2 = 300
sentence_end = re.compile(r'(.*?[.!?])( +[A-Z][a-z ]?.*)')
# This probably does no work.
def cull_doc(elem):
    global adjusted_node
    doc = elem.get("doc")
    if doc:
        doc_lines = parseDocSummary(doc.split('&#xA;'))
        elem.set("doc", "\n".join(doc_lines))  # ElementTree's been patched.
    for child in elem:
        cull_doc(child)

# Do this one to avoid walking into newly created sub-nodes
def convert_mixinrefs(elem):
    global adjusted_node
    for child in elem:
        convert_mixinrefs(child)
    mixinrefs = elem.get("mixinrefs")
    if mixinrefs and elem.tag == "scope":
        for m in mixinrefs.split(" "):
            if m == "Kernel" and elem.get("classrefs"): continue
            ET.SubElement(elem, 'import', symbol=m)
            adjusted_node += 1
        #XXX Trent - non-deprecated way to delete an attribute?
        del elem.attrib['mixinrefs']
    
origTopLevel = origTree.getroot()
check_redundant_namespace(origTopLevel)
print "check_redundant_namespace: # changes: %d" % (adjusted_node)
adjusted_node = 0
cull_doc(origTopLevel)
print "cull_doc: # changes: %d" % (adjusted_node)

adjusted_node = 0
convert_mixinrefs(origTopLevel)
print "convert_mixinrefs: # changes: %d" % (adjusted_node)

fd = outfile == "-" and sys.stdin or open(outfile, "w")
fd.write(ET.tostring(pretty_tree_from_tree(origTopLevel)))
fd.close()
print "Done writing to file %s" % outfile

