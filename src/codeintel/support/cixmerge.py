#!/usr/bin/env python
# Copyright (c) 2007 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.
#
# Author: Todd Whiteman
#

"""cixmerge is a simple ciElementTree merging tool to be used with cix files.

Can be used to combine elements of one cix tree into another.
"""

import re
import os.path
import sys
from optparse import OptionParser

from codeintel2.tree import pretty_tree_from_tree
from ciElementTree import ElementTree as ET
from ciElementTree import tostring as cixtostring
from ciElementTree import parse

def merge_missing(elem, names, lpath, mergedElem):
    for name in sorted(names):
        childElem = elem.names[name]
        elem_type = childElem.get("ilk") or childElem.tag
        if elem_type == "variable" and len(childElem):
            elem_type = "namespace"
        print "  %-10s %r" % (elem_type, lpath + [name])
        for key, value in childElem.items():
            if len(value) > 60:
                value = value[:60] + "..."
            print "      %-10s: %s" % (key, value)
        answer = raw_input("merge this %r? [Yn]" % (elem_type, ))
        if answer.lower() not in ("n", "no"):
            # Ensure we remove first, otherwise we generate double elements
            elem.remove(childElem)
            mergedElem.append(childElem)

def report_additional(elem, names):
    for name in sorted(names):
        childElem = elem.names[name]
        elem_type = childElem.get("ilk") or childElem.tag
        if elem_type == "variable" and len(childElem):
            elem_type = "namespace"
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
        attrs_in_e1_only = e1_attrs.difference(e2_attrs)
        attrs_in_e2_only = e2_attrs.difference(e1_attrs)
        for attr in e1_attrs.intersection(e2_attrs):
            if e1.get(attr) != e2.get(attr):
                attrs_that_differ.append(attr)
    if names_in_e1_only or names_in_e2_only or attrs_in_e1_only or \
       attrs_in_e2_only or attrs_that_differ:
        if names_in_e1_only:
            answer = raw_input("%r differs, merge? [Yn]" % (lpath, ))
            if answer.lower() not in ("n", "no"):
                merge_missing(e1, names_in_e1_only, lpath, e2)
        #if attrs_in_e1_only:
        #    report_missing_attributes(e1, attrs_in_e1_only)
        #if attrs_in_e2_only:
        #    report_additional_attributes(e2, attrs_in_e2_only)
        #if attrs_that_differ:
        #    report_attribute_differences(e1, e2, attrs_that_differ)
    if opts.max_depth is not None and len(lpath) < (opts.max_depth - 1):
        for name in names_shared:
            diffElements(opts, lpath + [name], e1.names[name], e2.names[name])

def mergeCixFiles(opts, filename1, filename2, outputfilename):
    e1 = parse(filename1).getroot().getchildren()[0]
    mergedcixroot = parse(filename2).getroot()
    e2 = mergedcixroot.getchildren()[0]
    elems1 = []
    elems2 = []
    if opts.lpath:
        for lpath in opts.lpath:
            elem1 = e1
            elem2 = e2
            lpath_split = lpath.split(".")
            for i in range(len(lpath_split)):
                name = lpath_split[i]
                new_elem1 = elem1.names.get(name)
                new_elem2 = elem2.names.get(name)
                if new_elem1 is None and new_elem2 is None:
                    print "lpath not found in either cix file: %r (skipping it)" % (lpath, )
                    break
                elif new_elem2 is None:
                    answer = raw_input("lpath %r only found in first cix file, copy over? [Yn]" % (lpath, ))
                    if answer.lower() not in ("n", "no"):
                        merge_missing(elem1, [name], lpath_split[:i-1], e2)
                    break
                #elif new_elem1 is None:
                #    print "lpath not found in either cix files: %r" % (lpath, )
                #    break
                elem1 = new_elem1
                elem2 = new_elem2
            else:
                elems1.append(elem1)
                elems2.append(elem2)
    else:
        elems1 = [e1]
        elems2 = [e2]
    for e1, e2 in zip(elems1, elems2):
        print "Diffing elements: %r, %r" % (e1, e2)
        diffElements(opts, [], e1, e2)

    pretty_tree_from_tree(mergedcixroot)
    file(outputfilename, "w").write(cixtostring(mergedcixroot))

def main(argv=None):
    if argv is None:
        argv = sys.argv
    usage = "usage: %prog [options] cixfile1 cixfile2 mergedcixfile"
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
    (opts, args) = parser.parse_args()
    if len(args) != 3:
        parser.print_usage()
        return 0
    #print "opts:", opts
    #print "args:", args
    mergeCixFiles(opts, *args)
    return 1

if __name__ == "__main__":
    sys.exit(main())
