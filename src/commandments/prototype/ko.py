#!/usr/bin/env python

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
if sys.platform.startswith("win"):
    import win32pipe
    import win32api
    import win32file
    SW_SHOWDEFAULT = 10 # from win32con
    import win32process
    import win32event
    from win32com.shell import shellcon, shell
else:
    import fcntl
import logging
from Tkinter import *
import threading
import time


#---- globals

log = logging.getLogger(str(os.getpid()))
ver = "3.9"
if sys.platform == "win32":
    gMutexName = "komodo-%s-mutex" % ver
    gRunningName = "komodo-%s-running" % ver
    gCommandmentsLockName = "komodo-%s-commandments-lock" % ver
    gCommandmentsEventName = "komodo-%s-new-commandments" % ver
    gCommandmentsFileName = os.path.join(
        shell.SHGetFolderPath(0, shellcon.CSIDL_APPDATA, 0, 0),
        "ActiveState", "Komodo", ver, "commandments.txt")
else:
    gMutexName = os.path.expanduser("~/.komodo/%s/mutex.lock" % ver)
    gRunningName = os.path.expanduser("~/.komodo/%s/running.lock" % ver)
    gCommandmentsFileName = os.path.expanduser("~/.komodo/%s/commandments.fifo" % ver)
    gFirstCommandmentsFileName = os.path.expanduser("~/.komodo/%s/first-commandments.txt" % ver)


#---- functions

def acquireMutex():
    if sys.platform == "win32":
        mutex = win32event.CreateMutex(None, 0, gMutexName)
        win32event.WaitForSingleObject(mutex, win32event.INFINITE)
    else:
        mutex = os.open(gMutexName, os.O_RDWR | os.O_CREAT)
        fcntl.lockf(handle, fcntl.LOCK_EX) # blocks until free
    return mutex

def releaseMutex(mutex):
    if sys.platform == "win32":
        win32event.ReleaseMutex(mutex)
        win32api.CloseHandle(mutex)
    else:
        fcntl.lockf(mutex, fcntl.LOCK_UN)
 
def releaseTheMan(theMan):
    if sys.platform == "win32":
        win32api.CloseHandle(theMan)
    else:
        os.close(theMan)

def wantToBeTheMan():
    """Try to grab an exclusive "running" lock. If successful, we are
    "the man". Returns either None (not the man) or a handle (the man).
    """
    if sys.platform == "win32":
        running = win32event.CreateMutex(None, 0, gRunningName)
        rv = win32event.WaitForSingleObject(running, 0)
        if rv == win32event.WAIT_OBJECT_0:
            return running # we *are* the man
        else:
            win32api.CloseHandle(running)
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
        lock = win32event.CreateMutex(None, 0, gCommandmentsLockName)
        win32event.WaitForSingleObject(lock, win32event.INFINITE)

        # Append the new commandments.
        f = open(gCommandmentsFileName, 'a')
        for cmd in cmds:
            log.info("issue %r", cmd)
            f.write(cmd)
        f.close()
        
        # Signal Komodo that there are new commandments.
        newCommandments = win32event.CreateEvent(None, 1, 0,
                                                 gCommandmentsEventName)
        win32event.SetEvent(newCommandments)
        win32api.CloseHandle(newCommandments)
        
        # Release the lock.
        win32event.ReleaseMutex(lock)
        win32api.CloseHandle(lock)
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
            lock = win32event.CreateMutex(None, 0, gCommandmentsLockName)
            existing = os.path.exists(gCommandmentsFileName)
            newCommandments = win32event.CreateEvent(None, 0, existing,
                                                     gCommandmentsEventName)

            while 1:
                # Wait for new commandments.
                rv = win32event.WaitForSingleObject(newCommandments,
                                                    win32event.INFINITE)
                if rv == win32event.WAIT_OBJECT_0:
                    retval = 1
                else:
                    raise "Error waiting for new commandments: %r" % rv
                # Grab the lock.
                win32event.WaitForSingleObject(lock, win32event.INFINITE)
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
                win32event.ResetEvent(newCommandments)
                # Release the lock.
                win32event.ReleaseMutex(lock)
                # Handle the commandments.
                exit = 0
                for cmd in cmds:
                    log.info("handle: %r", cmd)
                    if cmd == "__exit__":
                        exit = 1
                        break
                if exit:
                    break

            win32api.CloseHandle(newCommandments)
            win32api.CloseHandle(lock)

        def exit(self):
            # Grab the lock.
            lock = win32event.CreateMutex(None, 0, gCommandmentsLockName)
            win32event.WaitForSingleObject(lock, win32event.INFINITE)
            # Send __exit__ commandment.
            f = open(gCommandmentsFileName, 'a')
            f.write("__exit__\n")
            f.close()
            # Signal that there are new commandments: to ensure worker
            # thread doesn't wedge.
            newCommandments = win32event.CreateEvent(None, 1, 0,
                gCommandmentsEventName)
            win32event.SetEvent(newCommandments)
            win32api.CloseHandle(newCommandments)
            # Release the lock.
            win32event.ReleaseMutex(lock)
            win32api.CloseHandle(lock)

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


