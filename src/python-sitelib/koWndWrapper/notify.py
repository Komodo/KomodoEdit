# koWndWrapper.notify module

from ctypes import *
from ctypes.wintypes import *

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
    while nbytes > 0:
        fni = cast(readBuffer, LPFNI).contents
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
        
