#!/usr/bin/env python
# Copyright (c) 2011 ActiveState Software Inc.
# See LICENSE.txt for license details.

"""
Generates the CIX file for the global objects in a Node.JS environment

This is expected to be run manually, and generates node.js.cix
"""

from ciElementTree import parse
import os, subprocess, sys, time
from os.path import abspath, dirname, join

# make sure python can find ../ecmaToCodeintel.py
scriptdir = dirname(abspath(__file__))
sys.path.append(dirname(scriptdir))

# parse the pre-written Node.js cix
tree = parse(join(scriptdir, "node_globals.cix"))
tree.find("/file").set("mtime", str(int(time.time())))

# generate ../javascript.cix
import ecmaToCodeintel
ecmaToCodeintel.performXSLTransform()
ecmaToCodeintel.fixTags()

# parse ../javascript.cix
jstree = parse(join(dirname(scriptdir), "javascript.cix"))

# copy all elements over
scope = tree.find("/file/scope")
for elem in jstree.find("/file/scope"):
    scope.append(elem)

# Write out the joined
filename = os.sep.join(scriptdir.split(os.sep)[:-4] +
                       ["lib", "codeintel2", "stdlibs", "node.js.cix"])
tree.write(filename, encoding="utf-8")

# Try to clean the file up if possible
subprocess.call(["xmllint", "--nonet", "--format", "-o", filename, filename])
