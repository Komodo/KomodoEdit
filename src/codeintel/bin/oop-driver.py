#!/usr/bin/env python

"""
Experimental out-of-process driver for codeintel2
Reference: http://bugs.activestate.com/show_bug.cgi?id=93455
"""

import argparse
import contextlib
import ctypes
import logging
import os
import os.path
from os.path import abspath, dirname, join
import socket
import sys
import threading

log = None

class DummyStream(object):
    def write(self, message):
        pass
    def flush(self):
        pass

def main(argv=[]):
    global log

    # Don't redirect output
    os.environ["KOMODO_VERBOSE"] = "1"

    parser = argparse.ArgumentParser()
    parser.description = "Komodo out-of-process codeintel driver"
    parser.add_argument("--database-dir", default=os.path.expanduser("~/.codeintel"),
                        help="The base directory for the codeintel database.")
    parser.add_argument("--log-level", action="append", default=[],
                        help="<log name>:<level> Set log level")
    parser.add_argument("--log-file", default=None,
                        help="The name of the file to log to")
    parser.add_argument("--connect", default=None,
                        help="Connect over TCP instead of using stdin/stdout")
    parser.add_argument("--import-path", action="append", default=["", "../lib"],
                        help="Paths to add to the Python import path")
    args = parser.parse_args()

    if args.log_file:
        stream = open(args.log_file, "w", 0)
        logging.basicConfig(stream=stream)
        # XXX marky horrible ugly hack
        sys.stderr = stream
        sys.stdout = stream
    else:
        logging.basicConfig(stream=DummyStream())

    for log_level in args.log_level:
        if ":" in log_level:
            name, level = log_level.rsplit(":", 1)
        else:
            name, level = ["", log_level]
        try:
            level = int(level, 10)
        except ValueError:
            try:
                level = getattr(logging, level)
            except AttributeError:
                pass
        if isinstance(level, int):
            logging.getLogger(name).setLevel(level)

    log = logging.getLogger("codeintel.oop.executable")

    try:
        set_process_limits()
    except:
        log.exception("Failed to set process memory/CPU limits")
    try:
        set_idle_priority()
    except:
        log.exception("Failed to set process CPU priority")

    old_sys_path = set(abspath(join(p)) for p in sys.path)

    for relpath in args.import_path:
        import_path = abspath(join(dirname(__file__), relpath))
        if import_path not in old_sys_path:
            sys.path.append(import_path)

    # importing codeintel imports pyxpcom, which seems to break logging;
    # work around it for now by putting the original handler back
    handler = logging.root.handlers[0]
    from codeintel2.oop import Driver
    logging.root.handlers[0] = handler

    if args.connect:
        log.debug("connecting to: %s", args.connect)
        conn = socket.create_connection(args.connect.rsplit(":", 1))
        fd_in = conn.makefile("r+b", 0)
        fd_out = fd_in
    else:
        # force unbuffered stdout
        fd_in = sys.stdin
        fd_out = os.fdopen(sys.stdout.fileno(), "wb", 0)
    driver = Driver(db_base_dir=args.database_dir,
                    fd_in=fd_in, fd_out=fd_out)
    driver.start()

def set_idle_priority():
    """Attempt to set the process priority to idle"""
    try:
        os.nice(20)
    except AttributeError:
        pass # No os.nice on Windows
    if sys.platform.startswith("linux"):
        import ctypes.util
        import platform
        # Try using a syscall to set io priority...
        __NR_ioprio_set = { # see Linux sources, Documentation/block/ioprio.txt
            "i386": 289,
            "x86_64": 251,
        }.get(platform.machine())
        if __NR_ioprio_set is not None:
            libc = ctypes.cdll.LoadLibrary(ctypes.util.find_library("c"))
            IOPRIO_WHO_PROCESS = 1
            IOPRIO_CLASS_IDLE = 3
            IOPRIO_CLASS_SHIFT = 13
            libc.syscall(__NR_ioprio_set, IOPRIO_WHO_PROCESS, 0,
                         IOPRIO_CLASS_IDLE << IOPRIO_CLASS_SHIFT)
    elif sys.platform.startswith("win"):
        import ctypes
        from ctypes import wintypes
        SetPriorityClass = ctypes.windll.kernel32.SetPriorityClass
        SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        SetPriorityClass.restype = wintypes.BOOL
        HANDLE_CURRENT_PROCESS = -1
        IDLE_PRIORITY_CLASS = 0x00000040
        SetPriorityClass(HANDLE_CURRENT_PROCESS, IDLE_PRIORITY_CLASS)
        # On Vista+, this sets the I/O priority to very low
        PROCESS_MODE_BACKGROUND_BEGIN = 0x00100000
        SetPriorityClass(HANDLE_CURRENT_PROCESS, PROCESS_MODE_BACKGROUND_BEGIN)

def set_process_limits():
    if sys.platform.startswith("win"):
        """Pre-allocate (but don't commit) a 1GB chunk of memory to prevent it
        from actually being used by codeintel; this acts as a limit on the
        amount of memory we can actually use.  It has no effects on performance
        (since we're only eating address space, not RAM/swap) but helps to
        prevent codeintel from blowing up the system.
        """
        from ctypes import wintypes
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        VirtualAlloc = kernel32.VirtualAlloc
        VirtualAlloc.argtypes = [wintypes.LPVOID, wintypes.ULONG, wintypes.DWORD, wintypes.DWORD]
        VirtualAlloc.restype = wintypes.LPVOID
        MEM_RESERVE = 0x00002000
        MEM_TOP_DOWN = 0x00100000
        PAGE_NOACCESS = 0x01
        # we can only eat about 1GB; trying for 2GB causes the allocation to
        # (harmlessly) fail, which doesn't accomplish our goals
        waste = VirtualAlloc(None, 1<<30, MEM_RESERVE|MEM_TOP_DOWN, PAGE_NOACCESS)
        if waste:
            log.debug("Successfullly allocated: %r", waste)
        else:
            log.debug("Failed to reduce address space: %s",
                      ctypes.WinError(ctypes.get_last_error()).strerror)


if __name__ == '__main__':
    main(argv=sys.argv)
