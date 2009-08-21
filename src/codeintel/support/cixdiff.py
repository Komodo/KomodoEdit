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
# Author: Todd Whiteman
#

"""cixdiff is a simple ciElementTree differing tools to be used with cix files.

Outputs the added or removed element names between the two cix files.
"""

import re
import os.path
import sys
from optparse import OptionParser

from ciElementTree import ElementTree as ET
from ciElementTree import parse

def report_missing(elem, names):
    for name in sorted(names):
        childElem = elem.names[name]
        elem_type = childElem.get("ilk") or childElem.tag
        if elem_type == "variable" and len(childElem):
            elem_type = "namespace"
        print "  missing %-10s %r" % (elem_type, name)

def report_additional(elem, names):
    for name in sorted(names):
        childElem = elem.names[name]
        elem_type = childElem.get("ilk") or childElem.tag
        if elem_type == "variable" and len(childElem):
            elem_type = "namespace"
        path = childElem.get("path")
        if path:
            print "  additional %-10s %-20r %s#%s" % (elem_type, name, path, childElem.get("line", ""))
        else:
            print "  additional %-10s %r" % (elem_type, name)

def report_missing_attributes(elem, names):
    for name in sorted(names):
        print "  missing attr %-10r => %r" % (name, elem.get(name))

def report_additional_attributes(elem, names):
    for name in sorted(names):
        print "  additional attr %-10r => %r" % (name, elem.get(name))

def report_attribute_differences(elem1, elem2, names):
    for name in sorted(names):
        print "  attr %-10s differs, %r != %r" % (name, elem1.get(name), elem2.get(name))

def diffElements(opts, lpath, e1, e2):
    # Ignore elements with these set attributes.
    # Note: this is the elem.attrib["attributes"] field!
    if opts.ignore_with_attributes:
        for attr in opts.ignore_with_attributes:
            e1_attributes = e1.get("attributes")
            e2_attributes = e2.get("attributes")
            if (e1_attributes and attr in e1_attributes.split()) or \
               (e2_attributes and attr in e2_attributes.split()):
                # Not diffing this item
                return

    e1_names = set(e1.names.keys())
    e2_names = set(e2.names.keys())
    names_in_e1_only = e1_names.difference(e2_names)
    names_in_e2_only = e2_names.difference(e1_names)
    names_shared = e1_names.intersection(e2_names)
    attrs_in_e1_only = []
    attrs_in_e2_only = []
    attrs_that_differ = []

    if opts.diff_attributes:
        e1_attrs = set(e1.attrib.keys())
        e2_attrs = set(e2.attrib.keys())
        if opts.ignore_attributes:
            e1_attrs.difference_update(opts.ignore_attributes)
            e2_attrs.difference_update(opts.ignore_attributes)
        attrs_in_e1_only = e1_attrs.difference(e2_attrs)
        attrs_in_e2_only = e2_attrs.difference(e1_attrs)
        for attr in e1_attrs.intersection(e2_attrs):
            if e1.get(attr) != e2.get(attr):
                attrs_that_differ.append(attr)
    if names_in_e1_only or names_in_e2_only or attrs_in_e1_only or \
       attrs_in_e2_only or attrs_that_differ:
        print "%r differs" % (lpath, )
        if names_in_e1_only:
            report_missing(e1, names_in_e1_only)
        if names_in_e2_only:
            report_additional(e2, names_in_e2_only)
        if attrs_in_e1_only:
            report_missing_attributes(e1, attrs_in_e1_only)
        if attrs_in_e2_only:
            report_additional_attributes(e2, attrs_in_e2_only)
        if attrs_that_differ:
            report_attribute_differences(e1, e2, attrs_that_differ)
    if opts.max_depth is not None and len(lpath) < (opts.max_depth - 1):
        for name in names_shared:
            diffElements(opts, lpath + [name], e1.names[name], e2.names[name])

def diffCixFiles(opts, filename1, filename2):
    e1 = parse(filename1).getroot().getchildren()[0]
    e2 = parse(filename2).getroot().getchildren()[0]
    elems1 = []
    elems2 = []
    if opts.lpath:
        for lpath in opts.lpath:
            elem1 = e1
            elem2 = e2
            for name in lpath.split("."):
                try:
                    elem1 = elem1.names[name]
                    elem2 = elem2.names[name]
                except KeyError:
                    print "lpath not found in both cix files: %r" % (lpath, )
                    return
            elems1.append(elem1)
            elems2.append(elem2)
    else:
        elems1 = [e1]
        elems2 = [e2]
    for e1, e2 in zip(elems1, elems2):
        print "Diffing elements: %r, %r" % (e1, e2)
        diffElements(opts, [], e1, e2)

def main(argv=None):
    if argv is None:
        argv = sys.argv
    usage = "usage: %prog [options] arg1 arg2"
    parser = OptionParser(usage=usage)
    parser.add_option("-a", "--diff-attributes", dest="diff_attributes",
                      action="store_true",
                      help="Include the attribute changes of elements.")
    parser.add_option("-d", "--max-depth", dest="max_depth",
                      type="int", help="Maximum recursion depth into the tree")
    #parser.add_option("-i", "--ignore-case", dest="ignore_case",
    #                  action="store_true", help="Case insensitve searching")
    parser.add_option("-l", "--lpath", dest="lpath",
                      action="append",
                      help="Diff from this lpath onwards.")
    parser.add_option("-n", "--ignore-with-attribute", dest="ignore_with_attributes",
                      action="append",
                      help="Ignore element differences that use this attribute.")
    parser.add_option("-x", "--ignore-attribute", dest="ignore_attributes",
                      action="append",
                      help="Ignore these attribute differences.")
    (opts, args) = parser.parse_args()
    if len(args) != 2:
        parser.print_usage()
        return 0
    #print "opts:", opts
    #print "args:", args
    diffCixFiles(opts, *args)
    return 1

if __name__ == "__main__":
    sys.exit(main())
