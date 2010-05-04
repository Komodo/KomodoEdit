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

# Put pywin32 replacement code here that can use pure ctypes,
# no dependencies on wnd or comtypes

from ctypes import *
from ctypes.wintypes import *

# Constants from wnd.wintypes:
LPVOID = c_void_p

# Constants from wnd.api.functions, wnd.wintypes, etc.

FO_DELETE      = 3
FOF_NOCONFIRMATION     =   16  # Don't prompt the user.
FOF_ALLOWUNDO      =        64

# Types needed for move_to_trash
class SHFILEOPSTRUCT(Structure):
    _fields_ = [("hwnd", HWND),
                ("wFunc", UINT),
                ("pFrom", LPCSTR),
                ("pTo", LPCSTR),
                ("fFlags", c_ulong),
                ("fAnyOperationsAborted", BOOL),
                ("hNameMappings", LPVOID),
                ("lpszProgressTitle", LPCSTR)]
        
def move_to_trash(filename):
    # Works only for ascii filenames
    sho=SHFILEOPSTRUCT()
    sho.hwnd = 0
    sho.wFunc = FO_DELETE
    sho.fFlags = FOF_ALLOWUNDO|FOF_NOCONFIRMATION
    sho.pFrom = filename + u"\x00"
    sho.pTo = None
    sho.fAnyOperationsAborted = False
    sho.hNameMappings = None
    sho.lpszProgressTitle = None
    res = windll.shell32.SHFileOperation(byref(sho))
    if res or sho.fAnyOperationsAborted:
        return False
    return True
