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

""" YAHOO documentation to Komodo CIX parser.

    Command line tool that parses up Yahoo's own javascript library to
    produce a Komodo CIX file. Works by grabbing a specified copy of yui online
    code and then parsing the JavaScript files to produce "yui.cix".

    Requirements:
      * cElementTree    (http://effbot.org/downloads/#cElementTree)

    Website download from:
      * http://sourceforge.net/projects/yui
"""

import os
import sys
import glob
import urllib
import zipfile
from cStringIO import StringIO
from optparse import OptionParser

from codeintel2.manager import Manager
from codeintel2.lang_javascript import JavaScriptCiler
from codeintel2.tree import tree_2_0_from_tree_0_1

from codeintel2.gencix_utils import *

yui_data = {
    "3.0.0b1": {
        "download_url": "http://yuilibrary.com/downloads/yui3/yui_3.0.0b1.zip",
    },
    "2.8.1": {
        "download_url": "http://yuilibrary.com/downloads/yui2/yui_2.8.1.zip",
    },
    "2.7.0": {
        "download_url": "http://yuilibrary.com/downloads/yui2/yui_2.7.0b.zip",
    },
    "2.5.2": {
        "download_url": "http://superb-west.dl.sourceforge.net/sourceforge/yui/yui_2.5.2.zip",
    },
    "2.5.0": {
        "download_url": "http://superb-west.dl.sourceforge.net/sourceforge/yui/yui_2.5.0.zip",
    },
    "2.4.1": {
        "download_url": "http://superb-west.dl.sourceforge.net/sourceforge/yui/yui_2.4.1.zip",
    },
    "2.3.1": {
        "download_url": "http://superb-west.dl.sourceforge.net/sourceforge/yui/yui_2.3.1.zip",
    },
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

yui_version = "2.8.1"
yui_major_minor_version = yui_version.rsplit(".", 1)[0]
yui_info = yui_data[yui_version]

def getYUIFilesFromWebpage():
    # Gets the zip file from the website and unpacks the necessary contents
    zippath = "yui_%s.zip" % (yui_version, )
    if not os.path.exists(zippath):
        print "Downloading yui version %s" % (yui_version, )
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
        print "Leaving zip file: %s" % (zippath)
        #os.remove(zippath)
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
    cix_yui = createCixRoot(name="YUI-%s" % (yui_major_minor_version, ),
                            description="Yahoo! User Interface Library - v%s" % (yui_version))
    #cix_yui_file = createCixFile(cix_yui, "yui", lang="JavaScript")
    #cix_yui_module = createCixModule(cix_yui_file, "*", lang="JavaScript")

    files = getYUIFilesFromWebpage()
    jscile = JavaScriptCiler(Manager(), "yui")
    for filename, content in files.items():
        if filename in ("utilities.js",
                        "yahoo-dom-event.js",   # v2.2.0
                        "yahoo-event-dom.js",
                        "yuiloader-dom-event.js"):  # v2.7.0
            # This is just a compressed up version of multiple files
            continue
        print "filename: %r" % (filename)
        jscile.path = filename
        jscile.scan_puretext(content, updateAllScopeNames=False)
    print "updating scope names"
    jscile.cile.updateAllScopeNames()
    # Convert the Javascript to CIX, content goes into cix element
    #jscile.toElementTree(cix)
    print "converting to cix"
    jscile.convertToElementTreeFile(cix_yui, "JavaScript")

    #mergeElementTreeScopes(cix_yui_module)

    #remove_cix_line_numbers_from_tree(cix_yui)

    # Write out the tree
    print "writing cix"
    updateCix(cix_filename, get_cix_string(cix_yui), updatePerforce)
    print "done"

# When run from command line
if __name__ == '__main__':
    import logging
    logging.basicConfig()

    parser = OptionParser()
    parser.add_option("-u", "--update", dest="update_perforce",
                      action="store_true", help="edit perforce cix for this file")
    (opts, args) = parser.parse_args()

    cix_filename = "yui_v%s.cix" % (yui_major_minor_version, )
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
