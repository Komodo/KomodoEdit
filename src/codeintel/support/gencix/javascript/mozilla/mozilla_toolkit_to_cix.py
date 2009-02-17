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

""" Mozilla JavaScript Toolkit to CIX tool.

    Command line tool that parses up Mozilla's own javascript files to
    produce a Mozilla Toolkit CIX file. Works by processing the mozilla
    parsing all the mozilla toolkit JavaScript files to produce
    "mozilla_toolkit.cix".

    Requirements:
      * cElementTree    (http://effbot.org/downloads/#cElementTree)
"""

import os
import sys
import zipfile
from optparse import OptionParser

from codeintel2.manager import Manager
from codeintel2.lang_javascript import JavaScriptCiler
from codeintel2.tree import tree_2_0_from_tree_0_1

from codeintel2.gencix_utils import *

def getMozillaToolkitFilenamesAndContent(toolkit_jar_file):
    files = {}
    zf = zipfile.ZipFile(toolkit_jar_file)
    for zfile in zf.filelist:
        dirpath, filename = os.path.split(zfile.filename)
        if filename.endswith(".js"):
            data = zf.read(zfile.filename)
            files[filename] = data
    return files

def remove_private_elements(tree):
    parent_map = dict((c, p) for p in tree.getiterator() for c in p)
    for node in list(tree.getiterator()):
        attributes = node.get("attributes")
        if attributes and "private" in attributes.split(" "):
            # Remove it
            parentnode = parent_map.get(node)
            if parentnode is not None:
                parentnode.remove(node)

def updateCix(filename, content, updatePerforce=False):
    if updatePerforce:
        print os.popen("p4 edit %s" % (filename)).read()
    file(filename, "w").write(content)
    if updatePerforce:
        diff = os.popen("p4 diff %s" % (filename)).read()
        if len(diff.splitlines()) <= 1 and diff.find("not opened on this client") < 0:
            print "No change, reverting: %s" % os.popen("p4 revert %s" % (filename)).read()

def main(cix_filename, toolkit_jar_file, updatePerforce=False):
    cix_komodo = createCixRoot(name="Mozilla Toolkit", description="Mozilla Toolkit API - version 1.8")
    #cix_yui_file = createCixFile(cix_yui, "yui", lang="JavaScript")
    #cix_yui_module = createCixModule(cix_yui_file, "*", lang="JavaScript")

    print "cix_filename: %r" % (cix_filename, )
    filenames_and_content = getMozillaToolkitFilenamesAndContent(toolkit_jar_file)
    jscile = JavaScriptCiler(Manager(), "Mozilla Toolkit")
    for filename, content in filenames_and_content.items():
        jscile.scan_puretext(content)
    jscile.convertToElementTreeFile(cix_komodo, "JavaScript")

    #mergeElementTreeScopes(cix_yui_module)
    #remove_cix_line_numbers_from_tree(cix_komodo)

    #remove_private_elements(cix_komodo)

    # Write out the tree
    updateCix(cix_filename, get_cix_string(cix_komodo), updatePerforce)

# When run from command line
if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-u", "--update", dest="update_perforce",
                      action="store_true", help="edit perforce cix for this file")
    (opts, args) = parser.parse_args()
    if len(args) != 1:
        print "Usage: python %s path/to/mozilla/toolkit.jar" % (__file__, )
        sys.exit(1)
    toolkit_jar_file = args[0]

    cix_filename = "mozilla_toolkit.cix"
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
    else:
        cix_filename = os.path.abspath(cix_filename)
    main(cix_filename, toolkit_jar_file, opts.update_perforce)
