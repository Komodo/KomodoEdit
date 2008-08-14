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
# Contributors:
#   Eric Promislow (EricP@ActiveState.com)

"""
combine-cixes.py -- a utility program that takes a reference
CIX file, and several other modules
"""

import os
from os.path import basename, splitext, isfile, isdir, join
import sys
import getopt
from hashlib import md5
import re
import logging
import glob
import time
import stat

from codeintel2.common import *
from codeintel2.tree import pretty_tree_from_tree

import ciElementTree as ET

from optparse import OptionParser
parser = OptionParser()

usage = "usage: %prog [NAME-RULES...]"
version = "%prog 0.1"
desc = """Blend the XML files into one."""
parser = OptionParser(prog="platinfo", usage=usage,
                                    version=version,
                                    description=desc)

parser.add_option("--orig-file", dest="origfile")
parser.add_option("-q", "--quiet",
                  action="store_false", dest="verbose", default=True,
                  help="don't print status messages to stdout")
(options, args) = parser.parse_args()
if not options.origfile:
    print "Usage: combine_cixes.py --orig-file file file..."
    sys.exit()

origTree = ET.parse(options.origfile)
origTopLevel = origTree.getroot()
origFile = origTopLevel.getchildren()[0]
origBlobStar = origFile.getchildren()[0]
if origBlobStar.get("ilk") != "blob" or origBlobStar.get("name") != "*":
    raise "Unexpected orig tree"

newTrees = [ET.parse(x) for x in args]

# Priority:
# yaml - all
# reflection - buildints
# reflection - binary
# parse - stdlib

# Trees:
# binaries = arg 0
# yaml_builtin = arg 1
# reflection builtin = arg 2
# yaml_stdlib = arg3

bin_tree = newTrees[0].getroot()
yaml_builtin_tree = newTrees[1].getroot()
refl_builtin_tree = newTrees[2].getroot()
yaml_stdlib_tree = newTrees[3].getroot()

reg_ilks = ("class", "namespace")

num_replacements = 0
num_additions = 0
def replace_node(dest_t, src_t, src_node, src_idx):
    global num_replacements, num_additions
    dest_idx = 0
    try:
        for dt in dest_t:
            if dt.tag == "scope" and dt.get("ilk") == src_node.get("ilk") and \
                dt.get("name") == src_node.get("name"):
                dest_t[dest_idx] = src_node
                num_replacements += 1
                return
            dest_idx += 1
        dest_t.append(src_node)
        num_additions += 1
    finally:
        src_t[src_idx] = None

print "Before, orig tree has %d nodes" % len(origBlobStar)
for curr_tree in (yaml_builtin_tree, refl_builtin_tree):
    i = 0
    for t in curr_tree:
        if t and t.get("ilk") in reg_ilks:
            replace_node(origBlobStar, curr_tree, t, i)
        i += 1

print "After doing yaml-nodes, orig tree has %d nodes" % len(origBlobStar)
print "Builtins: %d replacements, %d additions" % (num_replacements, num_additions)

i = 0
for t in bin_tree:
    replace_node(origFile, bin_tree, t, i)
    i += 1
    
print "After doing binary modules, orig tree has %d nodes" % len(origBlobStar)
print "Builtins: %d replacements, %d additions" % (num_replacements, num_additions)

# Finally update the YAML nodes, assuming that if we do a replacement
# we can replace the entire subtree.
i = 0
for t in yaml_stdlib_tree:
    replace_node(origFile, yaml_stdlib_tree, t, i)
    i += 1
  
print "After doing yaml modules, orig tree has %d nodes" % len(origBlobStar)
print "Builtins: %d replacements, %d additions" % (num_replacements, num_additions)
  
newFile = options.origfile + ".new"
fd = open(newFile, "w")
fd.write(ET.tostring(pretty_tree_from_tree(origTopLevel)))
fd.close()
print "Done writing to file %s" % newFile

