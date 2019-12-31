#!/usr/bin/env python
# Copyright (c) 2005-2008 ActiveState Software Inc.
# License: MIT

"""Cross-platform application utilities. Mainly this includes some
method for determining application-specific dirs.

Utility Functions:
    user_data_dir(...)      path to user-specific app data dir
    site_data_dir(...)      path to all users shared app data dir
    user_cache_dir(...)     path to user-specific app cache dir
"""
from __future__ import print_function
# Dev Notes:
# - MSDN on where to store app data files:
#   http://support.microsoft.com/default.aspx?scid=kb;en-us;310294#XSLTH3194121123120121120120
#
#TODO:
# - Add cross-platform versions of other abstracted dir locations, like
#   a prefs dir, something like bundle/Contents/SharedSupport
#   on OS X, etc.
#       http://developer.apple.com/documentation/MacOSX/Conceptual/BPRuntimeConfig/Concepts/UserPreferences.html
#       http://developer.apple.com/documentation/MacOSX/Conceptual/BPFileSystem/index.html
#       http://msdn.microsoft.com/library/default.asp?url=/library/en-us/shellcc/platform/shell/reference/enums/csidl.asp

__version_info__ = (1, 0, 0)
__version__ = '.'.join(map(str, __version_info__))
__author__ = "Trent Mick"


import sys
import os


class Error(Exception):
    pass



def user_data_dir(appname, owner=None, version=None):
    """Return full path to the user-specific data dir for this application.
    
        "appname" is the name of application.
        "owner" (only required and used on Windows) is the name of the
            owner or distributing body for this application. Typically
            it is the owning company name.
        "version" is an optional version path element to append to the
            path. You might want to use this if you want multiple versions
            of your app to be able to run independently. If used, this
            would typically be "<major>.<minor>".
    
    Typical user data directories are:
        Win XP:     C:\Documents and Settings\USER\Application Data\<owner>\<appname>
        Mac OS X:   ~/Library/Application Support/<appname>
        Unix:       ~/.<lowercased-appname>
    
    For Unix there is no *real* standard here. For example, Firefox uses:
    "~/.mozilla/firefox" which is a "~/.<owner>/<appname>"-type scheme.
    """
    if sys.platform.startswith("win"):
        if owner is None:
            raise Error("must specify 'owner' on Windows")
        path = os.path.join(_get_win_folder("CSIDL_APPDATA"),
                            owner, appname)
    elif sys.platform == 'darwin':
        if os.uname()[-1] == 'i386':
            #XXX Folder.FSFindFolder() fails with error -43 on x86. See 42669.
            basepath = os.path.expanduser('~/Library/Application Support')
        else:
            from Carbon import Folder, Folders
            path = Folder.FSFindFolder(Folders.kUserDomain,
                                       Folders.kApplicationSupportFolderType,
                                       Folders.kDontCreateFolder)
            basepath = path.FSRefMakePath()
        path = os.path.join(basepath, appname)
    else:
        path = os.path.expanduser("~/." + appname.lower())
    if version:
        path = os.path.join(path, version)
    return path


def site_data_dir(appname, owner=None, version=None):
    """Return full path to the user-shared data dir for this application.
    
        "appname" is the name of application.
        "owner" (only required and used on Windows) is the name of the
            owner or distributing body for this application. Typically
            it is the owning company name.
        "version" is an optional version path element to append to the
            path. You might want to use this if you want multiple versions
            of your app to be able to run independently. If used, this
            would typically be "<major>.<minor>".
    
    Typical user data directories are:
        Win XP:     C:\Documents and Settings\All Users\Application Data\<owner>\<appname>
        Mac OS X:   /Library/Application Support/<appname>
        Unix:       /etc/<lowercased-appname>
    """
    if sys.platform.startswith("win"):
        if owner is None:
            raise Error("must specify 'owner' on Windows")
        path = os.path.join(_get_win_folder("CSIDL_COMMON_APPDATA"),
                            owner, appname)
    elif sys.platform == 'darwin':
        if os.uname()[-1] == 'i386':
            #XXX Folder.FSFindFolder() fails with error -43 on x86. See 42669.
            basepath = os.path.expanduser('~/Library/Application Support')
        else:
            from Carbon import Folder, Folders
            path = Folder.FSFindFolder(Folders.kLocalDomain,
                                       Folders.kApplicationSupportFolderType,
                                       Folders.kDontCreateFolder)
            basepath = os.path.join(path.FSRefMakePath(), appname)
        path = os.path.join(basepath, appname)
    else:
        path = "/etc/"+appname.lower()
    if version:
        path = os.path.join(path, version)
    return path


def user_cache_dir(appname, owner=None, version=None):
    """Return full path to the user-specific cache dir for this application.
    
        "appname" is the name of application.
        "owner" (only required and used on Windows) is the name of the
            owner or distributing body for this application. Typically
            it is the owning company name.
        "version" is an optional version path element to append to the
            path. You might want to use this if you want multiple versions
            of your app to be able to run independently. If used, this
            would typically be "<major>.<minor>".
    
    Typical user data directories are:
        Win XP:     C:\Documents and Settings\USER\Local Settings\Application Data\<owner>\<appname>
        Mac OS X:   ~/Library/Caches/<appname>
        Unix:       ~/.<lowercased-appname>/caches

    For Unix there is no *real* standard here. Note that we are returning
    the *same dir as the user_data_dir()* for Unix. Use accordingly.
    """
    if sys.platform.startswith("win"):
        if owner is None:
            raise Error("must specify 'owner' on Windows")
        path = os.path.join(_get_win_folder("CSIDL_LOCAL_APPDATA"),
                            owner, appname)
    elif sys.platform == 'darwin':
        if os.uname()[-1] == 'i386':
            #XXX Folder.FSFindFolder() fails with error -43 on x86. See 42669.
            basepath = os.path.expanduser('~/Library/Caches')
        else:
            from Carbon import Folder, Folders
            path = Folder.FSFindFolder(Folders.kUserDomain,
                                       Folders.kCachedDataFolderType,
                                       Folders.kDontCreateFolder)
            basepath = path.FSRefMakePath()
        path = os.path.join(basepath, appname)
    else:
        path = os.path.expanduser("~/.%s/caches" % appname.lower())
    if version:
        path = os.path.join(path, version)
    return path




#---- internal support stuff

def _get_win_folder_from_registry(csidl_name):
    """This is a fallback technique at best. I'm not sure if using the
    registry for this guarantees us the correct answer for all CSIDL_*
    names.
    """
    import _winreg
    
    shell_folder_name = {
        "CSIDL_APPDATA": "AppData",
        "CSIDL_COMMON_APPDATA": "Common AppData",
        "CSIDL_LOCAL_APPDATA": "Local AppData",
    }[csidl_name]

    key = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
    dir, type = _winreg.QueryValueEx(key, shell_folder_name)

def _get_win_folder_with_ctypes(csidl_name):
    import ctypes

    csidl_const = {
        "CSIDL_APPDATA": 26,
        "CSIDL_COMMON_APPDATA": 35,
        "CSIDL_LOCAL_APPDATA": 28,
    }[csidl_name]
    
    buf = ctypes.create_unicode_buffer(1024)
    ctypes.windll.shell32.SHGetFolderPathW(None, csidl_const, None, 0, buf)
    return buf.value

if sys.platform == "win32":
    try:
        import ctypes
        _get_win_folder = _get_win_folder_with_ctypes
    except ImportError:
        _get_win_folder = _get_win_folder_from_registry



#---- self test code

if __name__ == "__main__":
    print("applib: user data dir:", user_data_dir("Komodo", "ActiveState"))
    print("applib: site data dir:", site_data_dir("Komodo", "ActiveState"))
    print("applib: user cache dir:", user_cache_dir("Komodo", "ActiveState"))

