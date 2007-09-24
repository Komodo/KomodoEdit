# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

"""utility functions to make using nsIDirectoryService a little easier.
"""

from xpcom import components

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

def getComponentsDirectories():
    """getComponentsDirectories
    
    gets a list of file paths for all component directories
    """
    dirs = {}
    dirs[getFile("GreComsD").path]=1
    dirs[getFile("ComsD").path]=1
    for file in getFiles("ComsDL"):
        dirs[file.path]=1
    return dirs.keys()

def getExtensionDirectories():
    """getComponentsDirectories
    
    gets a list of file paths for all installed extensions
    """
    dirs = {}
    for file in getFiles("XREExtDL"):
        dirs[file.path]=1
    return dirs.keys()
