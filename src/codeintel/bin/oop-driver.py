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
        if args.log_file in ("stdout", "stderr"):
            stream = getattr(sys, args.log_file)
        else:
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

    try:
        if args.connect:
            if args.connect.startswith("pipe:"):
                pipe_name = args.connect.split(":", 1)[1]
                log.debug("connecting to pipe: %s", pipe_name)
                if sys.platform.startswith("win"):
                    # using Win32 pipes
                    from win32_named_pipe import Win32Pipe
                    fd_out = fd_in = Win32Pipe(name=pipe_name, client=True)
                else:
                    # Open the write end first, so the parent doesn't hang
                    fd_out = open(join(pipe_name, "out"), "wb", 0)
                    fd_in = open(join(pipe_name, "in"), "rb", 0)
                log.debug("opened: %r", fd_in)
            else:
                log.debug("connecting to port: %s", args.connect)
                conn = socket.create_connection(args.connect.rsplit(":", 1))
                fd_in = conn.makefile("r+b", 0)
                fd_out = fd_in
        else:
            # force unbuffered stdout
            fd_in = sys.stdin
            fd_out = os.fdopen(sys.stdout.fileno(), "wb", 0)
    except Exception as ex:
        log.exception("Failed to connect to Komodo: %s", ex)
        raise
    driver = Driver(db_base_dir=args.database_dir,
                    fd_in=fd_in, fd_out=fd_out)
    driver.start()

def set_idle_priority():
    """Attempt to set the process priority to idle"""
    try:
        os.nice(5)
    except AttributeError:
        pass # No os.nice on Windows
    if sys.platform.startswith("win"):
        import ctypes
        from ctypes import wintypes
        SetPriorityClass = ctypes.windll.kernel32.SetPriorityClass
        SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        SetPriorityClass.restype = wintypes.BOOL
        HANDLE_CURRENT_PROCESS = -1
        BELOW_NORMAL_PRIORITY_CLASS = 0x00004000
        SetPriorityClass(HANDLE_CURRENT_PROCESS, BELOW_NORMAL_PRIORITY_CLASS)

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
    elif sys.platform.startswith("linux"):
        import resource
        # Limit the oop process to 2GB of memory.
        #
        # Note that setting to 1GB of memory cause "bk test" failures, showing
        # this error:
        #   Fatal Python error: Couldn't create autoTLSkey mapping
        GB = 1<<30
        resource.setrlimit(resource.RLIMIT_AS, (2 * GB, -1L))
    else:
        # TODO: What to do on the Mac?
        pass


if __name__ == '__main__':
    try:
        main(argv=sys.argv)
    except Exception as ex:
        print(ex)
        if log:
            log.exception(ex)
    finally:
        if log:
            log.debug("Shutting down")
        else:
            print("Shutting down, no log")
