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
# Portions created by ActiveState Software Inc are Copyright (C) 2000-2008
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

"""Generate Ext JavaScript library CIX for use in Komodo.

    Command line tool that parses up Ext's own javascript library to
    produce a Komodo CIX file. Works by grabbing a specified copy of ext online
    code and then parsing the JavaScript files to produce "ext.cix".

    Requirements:
      * cElementTree    (http://effbot.org/downloads/#cElementTree)

    Website download from:
      * http://extjs.com/download

    Tested with ext versions:
      * Version 1.1.0     (2007-09-05)
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

ext_data = {
    "2.0.2": {
        "download_url": "http://extjs.com/deploy/ext-2.0.2.zip",
        "zip_file_prefix": { "source": "ext-2.0/source",
                             "all": "ext-2.0" },
    },
    "1.1.1": {
        "download_url": "http://extjs.com/deploy/ext-1.1.1.zip",
        "zip_file_prefix": { "source": "ext-1.1.1/source",
                             "all": "ext-1.1.1" },
    },
    "1.1.0": {
        "download_url": "http://extjs.com/deploy/ext-1.1.zip",
        "zip_file_prefix": { "source": "ext-1.1-beta1/source",
                             "all": "ext-1.1-beta1" },
    },
    "1.0.1": {
        "download_url": "http://extjs.com/deploy/ext-1.0.1a.zip",
        "zip_file_prefix": { "source": "ext-1.0.1/source" }
    },
}

library_name = "Ext"
#library_version = "1.1.1"
library_version = "2.0.2"
library_version_major_minor = library_version.rsplit(".", 1)[0]
library_info = ext_data[library_version]

def getFilesFromWebpage():
    # Gets the zip file from the website and unpacks the necessary contents
    zippath = "tmp_js.zip"
    if not os.path.exists(zippath):
        urlOpener = urllib.urlopen(library_info["download_url"])
        f = file(zippath, "wb")
        f.write(urlOpener.read())
        f.close()

    files = {}
    for build_type in library_info["zip_file_prefix"]:
        files[build_type] = {}
    try:
        zf = zipfile.ZipFile(zippath)
        for zfile in zf.filelist:
            dirpath, filename = os.path.split(zfile.filename)
            #print "dirpath: %r" % (dirpath, )
            for build_type, prefix in library_info["zip_file_prefix"].items():
                if dirpath.startswith(prefix) >= 0:
                    name, ext = os.path.splitext(filename)
                    #print "name: %r, ext: %r" % (name, ext)
                    if ext == ".js":
                        data = zf.read(zfile.filename)
                        files[build_type][zfile.filename] = (dirpath, filename, data)
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
    cix = createCixRoot(name="%s_%s" % (library_name,
                                        library_version.replace(".", "")),
                        description="%s JavaScript framework - version %s" % (
                                         library_name, library_version))
    files = getFilesFromWebpage()
    jscile = JavaScriptCiler(Manager(), "extjs")
    for path, (dirname, filename, content) in files["source"].items():
        if "source" in dirname.split("/") and not filename.startswith("ext-lang-"):
            print "filename: %r" % (filename)
            jscile.scan_puretext(content, updateAllScopeNames=False)

    jscile.cile.updateAllScopeNames()
    jscile.cile.name = "%s_%s" % (library_name.lower(),
                                  library_version.replace(".", ""))
    # Convert the Javascript to CIX, content goes into cix element
    jscile.convertToElementTreeFile(cix, "JavaScript")
    # Write out the tree
    updateCix(cix_filename, get_cix_string(cix), updatePerforce)

# When run from command line
if __name__ == '__main__':
    import logging
    logging.basicConfig()

    parser = OptionParser()
    parser.add_option("-u", "--update", dest="update_perforce",
                      action="store_true", help="edit perforce cix for this file")
    (opts, args) = parser.parse_args()

    cix_filename = "%s_%s.cix" % (library_name.lower(), library_version_major_minor)
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
