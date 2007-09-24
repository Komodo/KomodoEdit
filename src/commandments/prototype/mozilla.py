#!python

# equiv to Komodo's mozilla.exe

import os
import sys
import threading
import time
import re
from Tkinter import *  # for fakey komodo.xul
if sys.platform.startswith("win"):
    import wnd.komodo
else:
    import fcntl


#---- globals

def _getKomodoVersion():
    """Return a "MAJOR.MINOR" version string for the currently configured
    Komodo.
    """
    sys.path.insert(0, os.path.join(os.path.dirname(sys.argv[0]), os.pardir,
                                                    os.pardir, os.pardir))
    try:
        import bkconfig
        version = bkconfig.version             # '1.9.0-devel'
        version = re.split('\.|-', version)    # ['1', '9', '0', 'devel']
        version = "%s.%s" % tuple(version[:2]) # '1.9'
    except ImportError:
        # fallback
        version = "2.0"
    del sys.path[0]
    return version

ver = _getKomodoVersion()
if sys.platform.startswith("win"):
    from wnd.api.shell.consts import CLSIDL_APPDATA
    _gStatusLockName = "komodo-%s-status-lock" % ver
    _gStartingEventName = "komodo-%s-starting" % ver
    _gRunningEventName = "komodo-%s-running" % ver
    _gCommandmentsLockName = "komodo-%s-commandments-lock" % ver
    _gCommandmentsEventName = "komodo-%s-new-commandments" % ver
    _gCommandmentsFileName = os.path.join(
        wnd.komodo.get_path_by_shell_clsidl(CLSIDL_APPDATA),
        "ActiveState", "Komodo", ver, "commandments.txt")
else:
    _gRunningLockFileName = os.path.expanduser("~/.komodo/%s/running.lock" % ver)
    _gCommandmentsFileName = os.path.expanduser("~/.komodo/%s/commandments.fifo" % ver)
del ver



#---- support stuff

class KomodoXul(Frame):
    """A little Tk window pretending to be komodo.xul for the sake of the
    prototype.
    """
    def say_hi(self):
        print "hi there, everyone!"
    def createWidgets(self):
        self.QUIT = Button(self)
        self.QUIT["text"] = "QUIT"
        self.QUIT["fg"]   = "red"
        self.QUIT["command"] =  self.quit
        self.QUIT.pack({"side": "left"})
        self.hi_there = Button(self)
        self.hi_there["text"] = "Hello",
        self.hi_there["command"] = self.say_hi
        self.hi_there.pack({"side": "left"})
    def __init__(self, master=None):
        Frame.__init__(self, master)
        self.pack()
        self.createWidgets()


if sys.platform.startswith("win"):
    class CommandmentsReader(threading.Thread):
        """Consume commandments from the commandments.txt file.
        
        The .txt file must by guarded by the appropriate mutex and an
        event is signalled when new commandments are added.
        """
        def __init__(self):
            threading.Thread.__init__(self)
            if os.path.exists(_gCommandmentsFileName):
                os.unlink(_gCommandmentsFileName)

        def run(self):
            lock = wnd.komodo.create_mutex(_gCommandmentsLockName)
            newCommandments = wnd.komodo.create_event(_gCommandmentsEventName)

            while 1:
                # Wait for new commandments.
                rv = wnd.komodo.wait_for_single_object(newCommandments)
                if rv == wnd.komodo.WAIT_OBJECT_0:
                    retval = 1
                else:
                    raise "Error waiting for new commandments: %r" % rv
                # Grab the lock.
                wnd.komodo.wait_for_single_object(lock)
                # Consume the commandments.
                f = open(_gCommandmentsFileName, 'r')
                cmds = []
                for line in f.readlines():
                    if line.endswith('\n'):
                        cmds.append( line[:-1] )
                f.close()
                os.unlink(_gCommandmentsFileName)
                # Reset the "new commandments" event.
                wnd.komodo.reset_event(newCommandments)
                # Release the lock.
                wnd.komodo.release_mutex(lock)
                # Handle the commandments.
                exit = 0
                for cmd in cmds:
                    print "command handler: cmd=%r" % cmd
                    if cmd == "__exit__":
                        exit = 1
                        break
                if exit:
                    break

            wnd.komodo.close_handle(newCommandments)
            wnd.komodo.close_handle(lock)

        def exit(self):
            # Grab the lock.
            lock = wnd.komodo.create_mutex(_gCommandmentsLockName)
            wnd.komodo.wait_for_single_object(lock)
            # Send __exit__ commandment.
            f = open(_gCommandmentsFileName, 'a')
            f.write("__exit__\n")
            f.close()
            # Signal hat there are new commandments.
            newCommandments = wnd.komodo.create_event(_gCommandmentsEventName)
            wnd.komodo.set_event(newCommandments)
            wnd.komodo.close_handle(newCommandments)
            # Release the lock.
            wnd.komodo.release_mutex(lock)
            wnd.komodo.close_handle(lock)

            self.join()

else:
    class CommandmentsReader(threading.Thread):
        def __init__(self):
            threading.Thread.__init__(self)
            if os.path.exists(_gCommandmentsFileName):
                os.unlink(_gCommandmentsFileName)
            os.mkfifo(_gCommandmentsFileName)
            self._pipe = os.open(_gCommandmentsFileName, os.O_RDWR)
    
        def run(self):
            buf = ""
            while 1:
                text = os.read(self._pipe, 4096)
                buf += text
                lines = buf.splitlines(1)
                # parse out commands
                cmds = []
                for line in buf.splitlines(1):
                    if line.endswith('\n'):
                        cmds.append( line[:-1] )
                    else:
                        buf = line
                        break
                else:
                    buf = ""
                # handle each command
                exit = 0
                for cmd in cmds:
                    print "command handler: cmd=%r" % cmd
                    if cmd == "__exit__":
                        exit = 1
                        break
                if exit:
                    break
    
        def exit(self):
            os.write(self._pipe, "__exit__\n")
            self.join()
            os.close(self._pipe)
            os.unlink(_gCommandmentsFileName)


def acquireKomodoStatusLock():
    # No such lock used on Linux.
    lock = None
    if sys.platform.startswith("win"):
        lock = wnd.komodo.create_mutex(_gStatusLockName)
        #XXX Perhaps should have a reasonable timeout?
        wnd.komodo.wait_for_single_object(lock)
    return lock

def releaseKomodoStatusLock(lock):
    # No such lock used on Linux.
    if sys.platform.startswith("win"):
        wnd.komodo.release_mutex(lock)
        wnd.komodo.close_handle(lock)


def setKomodoStatusToRunning():
    handle = None
    if sys.platform.startswith("win"):
        handle = wnd.komodo.create_event(_gRunningEventName)
        wnd.komodo.set_event(handle)
    else:
        handle = open(_gRunningLockFileName, 'w')
        handle.write( str(os.getpid()) )
        handle.flush()
        fcntl.flock(handle, fcntl.LOCK_EX)
    return handle

def cleanupRunningHandle(handle):
    if sys.platform.startswith("win"):
        if handle:
            wnd.komodo.close_handle(handle)
    else:
        fcntl.flock(handle, fcntl.LOCK_UN)
        handle.close()
        os.unlink(_gRunningLockFileName)


#---- mainline

def main(argv):
    #---- startup
    # Take of long time to startup
    for i in range(2):
        print '. (Komodo starting)'
        time.sleep(1)

    # Start commandment handler thread.
    cmdSvc = CommandmentsReader()
    cmdSvc.start()

    # We are now running.
    lock = acquireKomodoStatusLock()
    runningHandle = setKomodoStatusToRunning()
    releaseKomodoStatusLock(lock)

    #--- run komodo.xul
    app = KomodoXul()
    app.mainloop()

    #---- exit
    cmdSvc.exit() # exit command pipe handler
    cleanupRunningHandle(runningHandle)
    print "Komodo exiting"


if __name__ == "__main__":
    sys.exit( main(sys.argv) )
