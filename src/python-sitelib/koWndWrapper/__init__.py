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

# Sub-modules here

# koWndWrapper/__init__.py -
# utility routines that wrap lower-level wnd routines
# around the pythonwin functions

import os, sys, types
import logging
log = logging.getLogger("koWndWrapper")
#log.setLevel(logging.DEBUG)

import ctypes

# Hardwired constants that we'd normally get from wnd, but 
# run into old code that wants to import ctypes.com

CLSIDL_APPDATA = 26

_kernel32 = ctypes.windll.kernel32
_user32 = ctypes.windll.user32

def get_path_by_shell_clsidl(pidl_val):
    from wnd.api.shell.functions import GetPathFromPidl, PidlFree
    from wnd.api.shell.wintypes import PIDL, ITEMIDLIST, shell32
    from ctypes import byref
    pIdl_tmp = PIDL(ITEMIDLIST())
    shell32.SHGetSpecialFolderLocation(0, pidl_val, byref(pIdl_tmp))
    path = GetPathFromPidl(pIdl_tmp)
    PidlFree(pIdl_tmp)
    #log.debug("get_path_by_shell_clsidl(%r) => %r", pidl_val, path)
    return path

def get_unicode_path_by_shell_clsidl(pidl_val):
    path = get_path_by_shell_clsidl(pidl_val)
    # Try to make this a unicode path because SHGetFolderPath does
    # not return unicode strings when there is unicode data in the
    # path.
    try:
        path = unicode(path)
    except UnicodeError:
        pass
    #log.debug("get_unicode_path_by_shell_clsidl(%r) => %r", pidl_val, path)
    return path

# Wrappers around win32api routines

def close_handle(h):
    return _kernel32.CloseHandle(h)

# Wrappers around win32event routines

# Constants

MAXIMUM_WAIT_OBJECTS = 64

def create_event(name, security_attributes=None, manual_reset=1, initial_state=0):
    log.debug("create_event(%r)", name)
    func = (type(name) == types.UnicodeType
            and _kernel32.CreateEventW
            or _kernel32.CreateEventA)
    return func(security_attributes, manual_reset, initial_state, name)

def create_mutex(name, security_attributes=None, owner=0):
    log.debug("create_mutex(%r)", name)
    func = (type(name) == types.UnicodeType
            and _kernel32.CreateMutexW
            or _kernel32.CreateMutexA)
    return func(security_attributes, owner, name)

def reset_event(h):
    return _kernel32.ResetEvent(h)

def release_mutex(lock):
    return _kernel32.ReleaseMutex(lock)

def set_event(h):
    return _kernel32.SetEvent(h)

from wnd.api.process import INFINITE
from wnd.api.process import WAIT_OBJECT_0

def wait_for_single_object(h, timeout=None):
    if timeout is None:
        timeout = INFINITE
    log.debug("wait_for_single_object(%r)", timeout)
    return _kernel32.WaitForSingleObject(h, timeout)

def wait_for_multiple_objects(handle_list, wait_all_flag=0, timeout=None):
    from ctypes.wintypes import HANDLE
    if timeout is None:
        timeout = INFINITE
    log.debug("wait_for_multiple_objects(%r)", timeout)
    # Convert the Python array into a C array
    numHandles = len(handle_list)
    c_handles = (HANDLE * numHandles)()
    for i in range(numHandles):
        c_handles[i] = handle_list[i]
    return _kernel32.WaitForMultipleObjects(numHandles, c_handles,
                                            wait_all_flag, timeout)

# Wrappers around win32gui

def get_active_window():
    return _user32.GetActiveWindow()

def set_foreground_window(h):
    return _user32.SetForegroundWindow(h)

# Wrappers around win32file

# Functions

def CreateFile(fileName, desiredAccess, shareMode, attributes, creationDisposition, flagsAndAttributes, hTemplateFile=None):
    func = (type(fileName) == types.UnicodeType
            and _kernel32.CreateFileW
            or _kernel32.CreateFileA)
    if hTemplateFile is None:
        hTemplateFile = 0
    return func(fileName, desiredAccess, shareMode, attributes, creationDisposition, flagsAndAttributes, hTemplateFile)

def ReadDirectoryChangesW(handle, size, bWatchSubtree, dwNotifyFilter, overlapped, cbOnCompletion):
    pass

