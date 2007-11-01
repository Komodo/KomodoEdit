import unittest, gc
from ctypes import *
from ctypes.wintypes import *

################################################################

class PROCESS_MEMORY_COUNTERS(Structure):
    _fields_ = [("cb", DWORD),
                ("PageFaultCount", DWORD),
                ("PeakWorkingSetSize", c_size_t),
                ("WorkingSetSize", c_size_t),
                ("QuotaPeakPagedPoolUsage", c_size_t),
                ("QuotaPagedPoolUsage", c_size_t),
                ("QuotaPeakNonPagedPoolUsage", c_size_t),
                ("QuotaNonPagedPoolUsage", c_size_t),
                ("PagefileUsage", c_size_t),
                ("PeakPagefileUsage", c_size_t)]
    def __init__(self):
        self.cb = sizeof(self)

    def dump(self):
        for n, _ in self._fields_[2:]:
            print n, getattr(self, n)/1e6

windll.psapi.GetProcessMemoryInfo.argtypes = (HANDLE, POINTER(PROCESS_MEMORY_COUNTERS), DWORD)

def wss():
    # Return the working set size (memory used by process)
    pmi = PROCESS_MEMORY_COUNTERS()
    if not windll.psapi.GetProcessMemoryInfo(-1, byref(pmi), sizeof(pmi)):
        raise WinError()
    return pmi.WorkingSetSize

try:
    any
except NameError:
    def any(iterable):
        for element in iterable:
            if element:
                return True
        return False

LOOPS = 10, 1000

def find_memleak(func):
    # call 'func' several times, so that memory consumption
    # stabilizes:
    for j in xrange(LOOPS[0]):
        for k in xrange(LOOPS[1]):
            func()
    gc.collect(); gc.collect(); gc.collect()
##    leaks = [0] * LOOPS[0]
    bytes = wss()
    # call 'func' several times, recording the difference in
    # memory consumption before and after the call.  Repeat this a
    # few times, and return a list containing the memory
    # consumption differences.
    for j in xrange(LOOPS[0]):
        for k in xrange(LOOPS[1]):
            func()
        gc.collect(); gc.collect(); gc.collect()
##        mem = wss()
##        leaks.append(mem - bytes)
##        bytes = mem
##    return leaks
    return [wss() - bytes]

