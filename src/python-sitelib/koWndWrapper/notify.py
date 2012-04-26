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

# koWndWrapper.notify module

from ctypes import *
from ctypes.wintypes import *
import logging
log = logging.getLogger("koWndWrapper.notify")
#log.setLevel(logging.DEBUG)

class OVERLAPPED(Structure):
    _fields_ = [("Internal", POINTER(ULONG)),
                ("InternalHigh", POINTER(ULONG)),
                ("Offset", DWORD),
                ("OffsetHigh", DWORD),
                ("hEvent", HANDLE)]

class FILE_NOTIFY_INFORMATION(Structure):
    _fields_ = [("NextEntryOffset", DWORD),
                ("Action", DWORD),
                ("FileNameLength", DWORD),
                ("FileName", (WCHAR * 1))]

LPFNI = POINTER(FILE_NOTIFY_INFORMATION)

def ReadDirectoryChangesW(hDirectory, # handle to directory
                          lpBuffer,   # read results buffer
                          nBufferLength,  # length of buffer
                          bWatchSubtree,  # true: watch subdirs
                          dwNotifyFilter, # filter conditions
                          lpOverlapped,    # pointer to overlapped buffer
                          lpCompletionRoutine # completion routine
                          ):
    bytesReturned = DWORD(0) # Not used
    res = windll.kernel32.ReadDirectoryChangesW(hDirectory,
               pointer(lpBuffer),
               nBufferLength, bWatchSubtree,
               dwNotifyFilter, pointer(bytesReturned),
               pointer(lpOverlapped),
               lpCompletionRoutine)
    if not res:
        code = GetLastError()
        raise WindowsError("%d: %r" % (code, FormatError(code)))
    return bytesReturned

def GetOverlappedResult(hFile, overlappedObj, waitFlag):
    nbytes = DWORD(0)
    res = windll.kernel32.GetOverlappedResult(hFile, pointer(overlappedObj),
                                              pointer(nbytes), waitFlag)
    if res == 0:
        code = GetLastError()
        raise WindowsError("%d: %r" % (code, FormatError(code)))
    #print "Got %r bytes" % (nbytes,)
    return nbytes.value

# In the win32api FILE_NOTIFY_INFORMATION is a type, but in
# python's win32file module it's a method

def getFILE_NOTIFY_INFORMATION(readBuffer, nbytes):
    results = []
    #print "getFILE_NOTIFY_INFORMATION - process %d bytes" % (nbytes, )
    if nbytes < sizeof(FILE_NOTIFY_INFORMATION):
        log.error("getFILE_NOTIFY_INFORMATION: Expecting nbytes = at least %d bytes, got %d",
                  sizeof(FILE_NOTIFY_INFORMATION), nbytes)
        return results
    while nbytes > 0:
        fni = cast(readBuffer, LPFNI).contents
        if not fni:
            log.error("getFILE_NOTIFY_INFORMATION: fni is null")
            return results
        fnameLocn = addressof(fni) + FILE_NOTIFY_INFORMATION.FileName.offset
        actualFileName = wstring_at(fnameLocn, fni.FileNameLength / 2)
        #print "FNI Size = ", fni.NextEntryOffset
        #print "FNI Action = ", fni.Action
        #print "FNI FileNameLen = ", fni.FileNameLength
        #print "FNI FileName = %r" % (actualFileName, )
        results.append((fni.Action, actualFileName))
        numToSkip = fni.NextEntryOffset
        if numToSkip <= 0:
            break
        readBuffer = readBuffer[numToSkip / 2:]
        nbytes -= numToSkip
    return results
        
