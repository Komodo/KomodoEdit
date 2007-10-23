# Copyright (C) ActiveState Software Inc.

# Define only what we need, taken from the old ctypes.com module

from ctypes.wintypes import DWORD, WORD, BYTE
from ctypes import Structure

class GUID(Structure):
    _fields_ = [("Data1", DWORD),
                ("Data2", WORD),
                ("Data3", WORD),
                ("Data4", BYTE * 8)]

