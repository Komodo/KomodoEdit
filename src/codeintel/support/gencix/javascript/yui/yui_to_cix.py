#!/usr/bin/env python
# Copyright (c) 2006 ActiveState Software Inc.
# See LICENSE.txt for license details.
#
# Contributers (aka Blame):
#  - Todd Whiteman
#

""" YAHOO documentation to Komodo CIX parser.

    Command line tool that parses up Yahoo's own javascript library to
    produce a Komodo CIX file. Works by grabbing a specified copy of yui online
    code and then parsing the JavaScript files to produce "yui.cix".

    Requirements:
      * cElementTree    (http://effbot.org/downloads/#cElementTree)

    Website download from:
      * http://sourceforge.net/projects/yui

    Tested with yui versions:
      * Version 2.2.2     (2007-06-11)
      * Version 0.12.0    (2006-11-30)
      * Version 0.11.3    (2006-08-28)
"""

import os
import sys
import glob
import urllib
import zipfile
from cStringIO import StringIO
from optparse import OptionParser

from codeintel2.lang_javascript import JavaScriptCiler
from codeintel2.tree import tree_2_0_from_tree_0_1

from codeintel2.gencix_utils import *

yui_data = {
    "2.2.2": {
        "download_url": "http://superb-west.dl.sourceforge.net/sourceforge/yui/yui_2.2.2.zip",
    },
    "0.12.0": {
        "download_url": "http://superb-west.dl.sourceforge.net/sourceforge/yui/yui_0.12.0.zip",
    },
    "0.11.3": {
        "download_url": "http://superb-west.dl.sourceforge.net/sourceforge/yui/yui_0.11.3.zip",
    },
}

yui_version = "2.2.2"
yui_info = yui_data[yui_version]

def getYUIFilesFromWebpage():
    # Gets the zip file from the website and unpacks the necessary contents
    zippath = "yui.zip"
    if not os.path.exists(zippath):
        urlOpener = urllib.urlopen(yui_info["download_url"])
        f = file(zippath, "wb")
        f.write(urlOpener.read())
        f.close()

    files = {}
    try:
        zf = zipfile.ZipFile(zippath)
        for zfile in zf.filelist:
            dirpath, filename = os.path.split(zfile.filename)
            if dirpath.startswith("yui/build/"):
                name, ext = os.path.splitext(filename)
                #print "name: %r, ext: %r" % (name, ext)
                if ext == ".js" and not name.endswith("-min") and \
                   not name.endswith("-debug"):
                    data = zf.read(zfile.filename)
                    files[filename] = data
    finally:
        #print "Leaving zip file: %s" % (zippath)
        os.remove(zippath)
    return files

def updateCix(filename, content, updatePerforce=False):
    if updatePerforce:
        print os.popen("p4 edit %s" % (filename)).read()
    file(filename, "w").write(content)
    if updatePerforce:
        diff = os.popen("p4 diff %s" % (filename)).read()
        if len(diff.splitlines()) <= 1 and diff.find("not opened on this client") < 0:
            print "No change, reverting: %s" % os.popen("p4 revert %s" % (filename)).read()

def main(cix_filename, updatePerforce=False):
    cix_yui = createCixRoot(name="YUI", description="Yahoo! User Interface Library - v%s" % (yui_version))
    #cix_yui_file = createCixFile(cix_yui, "yui", lang="JavaScript")
    #cix_yui_module = createCixModule(cix_yui_file, "*", lang="JavaScript")

    files = getYUIFilesFromWebpage()
    jscile = JavaScriptCiler("yui", "yui")
    for filename, content in files.items():
        if filename in ("utilities.js",
                        "yahoo-dom-event.js",   # v2.2.0
                        "yahoo-event-dom.js"):  # v2.2.2
            # This is just a compressed up version of multiple files
            continue
        print "filename: %r" % (filename)
        jscile.scan_puretext(content, updateAllScopeNames=False)
    jscile.cile.updateAllScopeNames()
    # Convert the Javascript to CIX, content goes into cix element
    #jscile.toElementTree(cix)
    jscile.convertToElementTreeFile(cix_yui, "JavaScript")

    #mergeElementTreeScopes(cix_yui_module)

    #remove_cix_line_numbers_from_tree(cix_yui)

    # Write out the tree
    updateCix(cix_filename, get_cix_string(cix_yui), updatePerforce)

# When run from command line
if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-u", "--update", dest="update_perforce",
                      action="store_true", help="edit perforce cix for this file")
    (opts, args) = parser.parse_args()

    cix_filename = "yui.cix"
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
