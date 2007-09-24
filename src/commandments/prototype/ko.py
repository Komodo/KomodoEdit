#!/usr/bin/env python
#
# Prototype of Komodo startup using Firefox/XRE framework.
#
#TODO:
# - Note this from MSDN docs on CreateMutex:
#
#       If you are using a named mutex to limit your application to a
#       single instance, a malicious user can create this mutex before
#       you do and prevent your application from starting. To prevent
#       this situation, create a randomly named mutex and store the name
#       so that it can only be obtained by an authorized user.
#       Alternatively, you can use a file for this purpose. To limit
#       your application to one instance per user, create a locked file
#       in the user's profile directory.
#
#  Perhaps wantToBeTheMan() should be adjusted appropriately for
#  Windows.
#

import os
import sys
if not sys.platform.startswith("win"):
    import fcntl
import logging
from Tkinter import *
import threading
import time


#---- globals

log = logging.getLogger(str(os.getpid()))
ver = "3.9"
if sys.platform == "win32":
    from wnd.komodo import get_path_by_shell_clsidl
    from wnd.api.shell.consts import CLSIDL_APPDATA
    gMutexName = "komodo-%s-mutex" % ver
    gRunningName = "komodo-%s-running" % ver
    gCommandmentsLockName = "komodo-%s-commandments-lock" % ver
    gCommandmentsEventName = "komodo-%s-new-commandments" % ver
    gCommandmentsFileName = os.path.join(
        get_path_by_shell_clsidl(CLSIDL_APPDATA),
        "ActiveState", "Komodo", ver, "commandments.txt")
else:
    gMutexName = os.path.expanduser("~/.komodo/%s/mutex.lock" % ver)
    gRunningName = os.path.expanduser("~/.komodo/%s/running.lock" % ver)
    gCommandmentsFileName = os.path.expanduser("~/.komodo/%s/commandments.fifo" % ver)
    gFirstCommandmentsFileName = os.path.expanduser("~/.komodo/%s/first-commandments.txt" % ver)


#---- functions

def acquireMutex():
    if sys.platform == "win32":
        mutex = wnd.komodo.create_mutex(gMutexName)
        wnd.komodo.wait_for_single_object(mutex)
    else:
        mutex = os.open(gMutexName, os.O_RDWR | os.O_CREAT)
        fcntl.lockf(handle, fcntl.LOCK_EX) # blocks until free
    return mutex

def releaseMutex(mutex):
    if sys.platform == "win32":
        wnd.komodo.release_mutex(mutex)
        wnd.komodo.close_handle(mutex)
    else:
        fcntl.lockf(mutex, fcntl.LOCK_UN)
 
def releaseTheMan(theMan):
    if sys.platform == "win32":
        wnd.komodo.close_handle(theMan)
    else:
        os.close(theMan)

def wantToBeTheMan():
    """Try to grab an exclusive "running" lock. If successful, we are
    "the man". Returns either None (not the man) or a handle (the man).
    """
    if sys.platform == "win32":
        running = wnd.komodo.create_mutex(gRunningName)
        rv = wnd.komodo.wait_for_single_object(running, 0)
        if rv == wnd.komodo.WAIT_OBJECT_0:
            return running # we *are* the man
        else:
            wnd.komodo.close_handle(running)
            return None # we are *not* the man
    else:
        fd = os.open(gRunningName, os.O_WRONLY|os.O_CREAT)
        try:
            fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError, ex:
            os.close(fd)
            # Darwin:
            #   IOError: [Errno 35] Resource temporarily unavailable
            # Elsewhere:
            #   IOError: [Errno 11] Resource temporarily unavailable
            errorid = (sys.platform == "darwin" and 35 or 11)
            if ex.errno == errorid:
                return None # we are *not* the man
            else:
                raise
        else:
            os.write(fd, str(os.getpid()))
            return fd # we *are* the man

def initCommandments(cmds):
    if sys.platform == "win32":
        if os.path.exists(gCommandmentsFileName):
            os.unlink(gCommandmentsFileName)
        issueCommandments(cmds)
    else:
        if os.path.exists(gCommandmentsFileName):
            os.remove(gCommandmentsFileName) # start fresh
        os.mkfifo(gCommandmentsFileName)
        if cmds:
            if os.path.exists(gFirstCommandmentsFileName):
                os.remove(gFirstCommandmentsFileName) # start fresh
            fout = open(gFirstCommandmentsFileName, 'w')
            for cmd in cmds:
                log.info("issue %r", cmd)
                fout.write(cmd)
            fout.close()
    log.info("commandments initialized")

def issueCommandments(options):
    cmds = ["open\t%s\n" % f for f in options.files]
    if not cmds: return
    if sys.platform == "win32":
        # Grab the lock.
        lock = wnd.komodo.create_mutex(gCommandmentsLockName)
        wnd.komodo.wait_for_single_object(lock)

        # Append the new commandments.
        f = open(gCommandmentsFileName, 'a')
        for cmd in cmds:
            log.info("issue %r", cmd)
            f.write(cmd)
        f.close()
        
        # Signal Komodo that there are new commandments.
        newCommandments = wnd.komodo.create_event(gCommandmentsEventName)
        wnd.komodo.set_event(newCommandments)
        wnd.komodo.close_handle(newCommandments)
        
        # Release the lock.
        wnd.komodo.release_mutex(lock)
        wnd.komodo.close_handle(lock)
    else:
        fd = os.open(gCommandmentsFileName, os.O_WRONLY | os.O_APPEND)
        for cmd in cmds:
            log.info("issue %r", cmd)
            os.write(fd, cmd)
        os.close(fd)


def beTheMan():
    # Take a long time to startup
    log.info("starting xre...")
    time.sleep(1)
    log.info("...done starting xre")

    # Start commandment handler thread.
    cmdSvc = CommandmentsReader()
    cmdSvc.start()

    # Run komodo.xul
    app = KomodoXul()
    app.mainloop()

    cmdSvc.exit() # exit command pipe handler


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

        def run(self):
            lock = wnd.komodo.create_mutex(gCommandmentsLockName)
            existing = os.path.exists(gCommandmentsFileName)
            newCommandments = wnd.komodo.create_event(None, 0, existing,
                                                     gCommandmentsEventName)

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
                f = open(gCommandmentsFileName, 'r')
                cmds = []
                for line in f.readlines():
                    if line[-1] == '\n':
                        line = line[:-1]
                    if line.strip(): # skip empty lines
                        cmds.append(line)
                f.close()
                os.unlink(gCommandmentsFileName)
                # Reset the "new commandments" event.
                wnd.komodo.reset_event(newCommandments)
                # Release the lock.
                wnd.komodo.release_mutex(lock)
                # Handle the commandments.
                exit = 0
                for cmd in cmds:
                    log.info("handle: %r", cmd)
                    if cmd == "__exit__":
                        exit = 1
                        break
                if exit:
                    break

            wnd.komodo.close_handle(newCommandments)
            wnd.komodo.close_handle(lock)

        def exit(self):
            # Grab the lock.
            lock = wnd.komodo.create_mutex(gCommandmentsLockName)
            wnd.komodo.wait_for_single_object(lock)
            # Send __exit__ commandment.
            f = open(gCommandmentsFileName, 'a')
            f.write("__exit__\n")
            f.close()
            # Signal that there are new commandments: to ensure worker
            # thread doesn't wedge.
            newCommandments = wnd.komodo.create_event(gCommandmentsEventName)
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

            self._pipe = os.open(gCommandmentsFileName, os.O_RDWR)
            if os.path.exists(gFirstCommandmentsFileName):
                # Commandments from the invoking process are necessarily
                # passed by a separate mechanism.
                cmds = open(gFirstCommandmentsFileName, 'r').read()
                os.remove(gFirstCommandmentsFileName)
                os.write(self._pipe, cmds)
            log.debug("init command reader (pipe: %r)", self._pipe)
    
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
                    log.info("handle %r", cmd)
                    if cmd == "__exit__":
                        exit = 1
                        break
                if exit:
                    break
    
        def exit(self):
            os.write(self._pipe, "__exit__\n")
            self.join()
            os.close(self._pipe)
            os.unlink(gCommandmentsFileName)


#---- mainline

def main(argv):
    log.info("start")
    # Parse command line arguments.
    # ...for now, no options, just file arguments
    class KoStartOptions: pass
    options = KoStartOptions()
    options.files = argv[1:]

    # Determine who is going to be "the man".
    mutex = acquireMutex()
    try:
        theMan = wantToBeTheMan()
        if theMan is not None:
            log.info("I am the man!")
            # we are the man -> initialize commandments pipe
            initCommandments()
        #XXX If a commandment can block (e.g. for implementing
        #    the Komodo-as-SCC-editor commandment) then issuing them
        #    *has* to be outside the mutex.
        issueCommandments(options)
    finally:
        releaseMutex(mutex)

    if theMan is not None:
        beTheMan() # i.e. startup the XRE and read and run commandments
        releaseTheMan(theMan)
    log.info("exit")


if __name__ == "__main__":
    logging.basicConfig()
    log.setLevel(logging.INFO)
    sys.exit(main(sys.argv))


