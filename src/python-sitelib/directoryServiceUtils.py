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
from xpcom import components, COMException
import ConfigParser

nsIDirectoryServiceContractID = "@mozilla.org/file/directory_service;1";
nsIProperties = components.interfaces.nsIProperties;
directoryService =  components.classes[nsIDirectoryServiceContractID].getService(nsIProperties);

def getFiles(key):
    """getFiles
    
    gets a list of nsIFile objects from the directory service.
    """
    enum = directoryService.get(key, components.interfaces.nsISimpleEnumerator);
    files = []
    while enum.hasMoreElements():
        files.append(enum.getNext().QueryInterface(components.interfaces.nsIFile))
    return files

def getFile(key):
    """getFiles
    
    gets a nsIFile object from the directory service.
    """
    return directoryService.get(key, components.interfaces.nsIFile);

_gExtensionDirectoriesCache = None
def getExtensionDirectories():
    """Get extension directories.
    
    @returns A list of full paths to all installed and enabled extension
        directories.
    """
    global _gExtensionDirectoriesCache
    if _gExtensionDirectoriesCache is None:
        dirs = set()
        try:
            iniFile = getFile("ProfD")
            iniFile.append("extensions.ini")
            config = ConfigParser.RawConfigParser()
            config.read(iniFile.path)
            if config.has_section("ExtensionDirs"):
                for name, dir in config.items("ExtensionDirs"):
                    if os.path.exists(dir):
                        dirs.add(dir)
        except COMException:
            # Hopefully this means we're in a unit test and not a real app,
            # so ask the test service for it.
            try:
                for d in getFiles("koTestExtDirL"):
                    dirs.add(d.path)
            except COMException as e:
                # Okay, that didn't work either; perhaps we're just in early
                # startup. _Hopefully_ this means ProfD isn't valid yet; pass
                # an empty list back, but don't update the cache since we might
                # have better luck next time.
                return []
        _gExtensionDirectoriesCache = list(dirs)
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
            if os.path.exists(d):
                dirs.add(d)
        _gPylibDirectoriesCache = list(dirs)
    return _gPylibDirectoriesCache
