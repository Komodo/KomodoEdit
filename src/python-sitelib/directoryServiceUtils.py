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

"""utility functions to make using nsIDirectoryService a little easier.
"""

import os
import sys
from xpcom import components, COMException, _xpcom
import ConfigParser

Cc = components.classes
Ci = components.interfaces

nsIDirectoryServiceContractID = "@mozilla.org/file/directory_service;1";
nsIProperties = Ci.nsIProperties;
directoryService =  Cc[nsIDirectoryServiceContractID].getService(nsIProperties);

def getFiles(key):
    """getFiles
    
    gets a list of nsIFile objects from the directory service.
    """
    enum = directoryService.get(key, Ci.nsISimpleEnumerator);
    files = []
    while enum.hasMoreElements():
        files.append(enum.getNext().QueryInterface(Ci.nsIFile))
    return files

def getFile(key):
    """getFiles
    
    gets a nsIFile object from the directory service.
    """
    return directoryService.get(key, Ci.nsIFile);

_gExtensionDirectoriesCache = None
def getExtensionDirectories():
    """Get extension directories.
    
    @returns A list of full paths to all installed and enabled extension
        directories.
    """
    global _gExtensionDirectoriesCache
    if _gExtensionDirectoriesCache is None:
        dirs = [d.path for d in getFiles("XREExtDL")]
        # Allow a custom directory service to provide additional extension
        # directories using the special "PyxpcomExtDirList" key.
        try:
            dirs += [d.path for d in getFiles("PyxpcomExtDirList")]
        except COMException:
            pass
        if not dirs:
            # Okay, that didn't work; perhaps we're just in early startup.
            # _Hopefully_ this means XREExtDL isn't valid yet; pass an empty
            # list back, but don't update the cache since we might have better
            # luck next time.
            return []
        # Make them unique - ordering does not matter.
        _gExtensionDirectoriesCache = list(set(dirs))
    return _gExtensionDirectoriesCache

_gPylibDirectoriesCache = None
def getPylibDirectories():
    """Get pylib directories.
    
    @returns A list of full paths to all "pylib" directories in all
        installed (and enabled?) extensions.
    """
    global _gPylibDirectoriesCache
    if _gPylibDirectoriesCache is None:
        dirs = set()
        for dir in getExtensionDirectories():
            d = os.path.join(dir, "pylib")
            # Note: pyxpcom will place these pylib paths on the sys.path (when
            #       they exist)
            if d in sys.path:
                dirs.add(d)
            elif os.path.exists(d):
                dirs.add(d)
                # Add to sys.path, saves pyxpcom having to do it later.
                sys.path.append(d)
        _gPylibDirectoriesCache = list(dirs)
    return _gPylibDirectoriesCache

_gExtensionCategoryDirsCache = {}
def getExtensionCategoryDirs(xpcom_category, relpath=None, extension_id=None):
    """Return extension dirpaths, registered via the given xpcom-category.

    Note: It will return paths that have an category entry that matches the
    extension id, e.g.:
        catagory  xpcom_category  myext@ActiveState.com  ignored_field
    will return:
        [ "/path/to/myext@ActiveState.com" ]
    """
    # Check the cache.
    cache_key = (xpcom_category, relpath, extension_id)
    dirs = _gExtensionCategoryDirsCache.get(cache_key)
    if dirs is not None:
        return dirs

    if extension_id:
        extension_id = os.path.normcase(extension_id)

    # Generate the directories.
    extension_dirs = getExtensionDirectories()
    dirs = []
    for entry in _xpcom.GetCategoryEntries(xpcom_category):
        extension_name = os.path.normcase(entry.split(" ")[0])

        # If looking for a specific extension.
        if extension_id and extension_id != extension_name:
            continue

        for ext_dir in extension_dirs:
            if os.path.normcase(os.path.basename(ext_dir)) == extension_name:
                candidate = ext_dir
                if relpath:
                    candidate = os.path.join(ext_dir, relpath)
                    if os.path.exists(candidate):
                        dirs.append(candidate)
                        break
    _gExtensionCategoryDirsCache[cache_key] = dirs
    return dirs

def getExtensionLexerDirs(relpath="lexers"):
    """Return the available (and enabled) extension lexer directories."""
    return getExtensionCategoryDirs("udl-lexers", relpath=relpath)

def getExtensionToolboxDirs(relpath="tools", extension_id=None):
    """Return the available (and enabled) extension tools directories."""
    return getExtensionCategoryDirs("toolbox", relpath=relpath, extension_id=extension_id)
