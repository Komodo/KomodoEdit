#!/usr/bin/env python
import sys
if sys.platform.startswith("win"):
    def namer():
        import ctypes
        import threading
        import time
        from ctypes import wintypes

        class THREADNAME_INFO(ctypes.Structure):
            _pack_ = 8
            _fields_ = [
                ("dwType", wintypes.DWORD),
                ("szName", wintypes.LPCSTR),
                ("dwThreadID", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD),
            ]
            def __init__(self):
                self.dwType = 0x1000
                self.dwFlags = 0


        def debugChecker():
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            RaiseException = kernel32.RaiseException
            RaiseException.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
                                       ctypes.c_void_p]
            RaiseException.restype = None

            IsDebuggerPresent = kernel32.IsDebuggerPresent
            IsDebuggerPresent.argtypes = []
            IsDebuggerPresent.restype = wintypes.BOOL
            MS_VC_EXCEPTION = 0x406D1388
            info = THREADNAME_INFO()
            while True:
                time.sleep(1)
                if IsDebuggerPresent():
                    for thread in threading.enumerate():
                        if thread.ident is None:
                            continue # not started
                        if hasattr(threading, "_MainThread"):
                            if isinstance(thread, threading._MainThread):
                                continue # don't name the main thread
                        info.szName = "%s (Python)" % (thread.name,)
                        info.dwThreadID = thread.ident
                        try:
                            RaiseException(MS_VC_EXCEPTION, 0,
                                           ctypes.sizeof(info) / ctypes.sizeof(ctypes.c_void_p),
                                           ctypes.addressof(info))
                        except:
                            pass

        dt = threading.Thread(target=debugChecker,
                              name="MSVC debugging support thread")
        dt.daemon = True
        dt.start()
    namer()
    del namer
elif sys.platform.startswith("linux"):
    def namer():
        import ctypes, ctypes.util, threading
        libpthread_path = ctypes.util.find_library("pthread")
        if not libpthread_path:
            return
        libpthread = ctypes.CDLL(libpthread_path)
        if not hasattr(libpthread, "pthread_setname_np"):
            return
        pthread_setname_np = libpthread.pthread_setname_np
        pthread_setname_np.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        pthread_setname_np.restype = ctypes.c_int

        orig_setter = threading.Thread.__setattr__
        def attr_setter(self, name, value):
            orig_setter(self, name, value)
            if name == "name":
                ident = getattr(self, "ident", None)
                if ident:
                    try:
                        pthread_setname_np(ident, str(value))
                    except:
                        pass # Don't care about failure to set name
        threading.Thread.__setattr__ = attr_setter

        #set the thread name to itself to trigger the new logic
        for thread in threading.enumerate():
            if thread.name:
                if hasattr(threading, "_MainThread"):
                    if isinstance(thread, threading._MainThread):
                        continue # don't name the main thread
                thread.name = thread.name

    namer()
    del namer
