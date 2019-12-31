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

"""
    measure_typing_speed.py -- attempt to measure possible linting leaks in Komodo
    
    %(PROGRAM)s [options] <file to use for key data>

    Options:
        -h, --help                      print this help
        --komodo=<path-to-komodo-exe>   specify komodo executable to drive
        -o                              dump output to stdout [default]
"""
from __future__ import print_function

import os, sys, time, random, getopt
if sys.platform.startswith("win"):
    import win32api
    import win32com.client
    import win32pdh, win32pdhutil

import which



#---- support routines

def usage(code, msg=''):
    print(__doc__ % globals(), file=sys.stderr)
    if msg:
        print(msg, file=sys.stderr)
    sys.exit(code)


def _SameFile(fname1, fname2):
    return ( os.path.normpath(os.path.normcase(fname1)) ==\
        os.path.normpath(os.path.normcase(fname2)) )


def _GetRegisteredExecutable(exe):
    if sys.platform.startswith('win'):
        # If on Windows, look up the Path in the "App Paths" registry
        import _winreg
        try:
            #XXX might have to be smart enough to handle HKCU too
            return _winreg.QueryValue(_winreg.HKEY_LOCAL_MACHINE,
                "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths"\
                "\\" + exe + ".exe")
        except _winreg.error:
            pass
    return None


def _GetMozillaPIDs(exename):
    if sys.platform.startswith("win"):
        win32pdh.EnumObjects(None, None, 0, 1)  # refresh internal cache
        pids = win32pdhutil.FindPerformanceAttributesByName(exename,
                                                            "Process",
                                                            "ID Process")
        return pids
    else:
        raise "Don't know how to list the mozilla PIDs yet on this OS."


class Win32PDHCounter:
    """Interface to Win32 PDH API for the given process prefix."""
    def __init__(self, pid):
        self.my_process_prefix = self.getProcessPrefix(pid)
        self.counters = {}
        self.query = win32pdh.OpenQuery()

    def __del__(self):
        win32pdh.CloseQuery(self.query)
    
    def getProcessPrefix(self, pid):
        object = "Process"
        items, instances = win32pdh.EnumObjectItems(None,None,object, win32pdh.PERF_DETAIL_WIZARD)
        # Need to track multiple instances of the same name.
        instance_dict = {}
        for instance in instances:
            try:
                instance_dict[instance] = instance_dict[instance] + 1
            except KeyError:
                instance_dict[instance] = 0
            
        # Bit of a hack to get useful info.
        item = "ID Process"
        for instance, max_instances in instance_dict.items():
            for inum in xrange(max_instances+1):
                hq = win32pdh.OpenQuery()
                try:
                    hcs = []
                    path = win32pdh.MakeCounterPath( (None,object,instance, None, inum, item) )
                    hc = win32pdh.AddCounter(hq, path)
                    try:
                        win32pdh.CollectQueryData(hq)
                        type, val = win32pdh.GetFormattedCounterValue(hc, win32pdh.PDH_FMT_LONG)
                        if val == pid:
                            return "\\".join(path.split("\\")[:-1]) + "\\"
                    finally:
                        win32pdh.RemoveCounter(hc)
                finally:
                    win32pdh.CloseQuery(hq)

    def addCounter(self, counter):
        counter_use = counter
        if counter.find("\\")==-1:
            counter_use = self.my_process_prefix + counter
        hc = win32pdh.AddCounter(self.query, counter_use)
        self.counters[counter] = hc

    def getCounterValue(self, counter):
        hc = self.counters[counter]
        return win32pdh.GetFormattedCounterValue(hc, win32pdh.PDH_FMT_DOUBLE)[1]

    def collect(self):
        win32pdh.CollectQueryData(self.query)

class Stopwatch:
    def __init__(self):
        self._timers = {}

    def resetTimerFor(self, id):
        self._timers[id] = (0, 0)

    def startTimerFor(self, id):
        if id not in self._timers:
            self.resetTimerFor(id)
        elapsed, then = self._timers[id]
        assert then == 0
        now = time.clock()
        self._timers[id] = (elapsed, now)

    def stopTimerFor(self, id):
        elapsed, then = self._timers[id]
        assert then != 0
        now = time.clock()
        self._timers[id] = (elapsed + (now - then), 0)

    def readTimerFor(self, id):
        elapsed, then = self._timers[id]
        if then:
            now = time.clock()
            return elapsed + (now - then)
        else:
            return elapsed

#---- public interface

def measure_typing_speed(testFile, blankFile, komodoExe, out, verbose):
    if not os.path.isfile(testFile):
        out.write("ERROR: '%s' does not exist" % testFile)
        return
    
    # start up Komodo with the testFile
    # - spawn komodo and wait to startup
    exename = os.path.basename(komodoExe)
    procname = exename.split(".")[0]
    argv = [exename, blankFile]
    sleeptime = 2
    if procname == "komodo":
        procname = "mozilla"
        sleeptime=20
    print("using procname",procname)
    
    pidsBefore = _GetMozillaPIDs(procname)
    print("pidsBefore:",repr(pidsBefore))
    argv = [exename, blankFile]
    
    os.spawnv(os.P_NOWAIT, komodoExe, argv)
    if verbose:
        out.write("Wait for '%s %s' to start up.\n" % (komodoExe,
                                                       ' '.join(argv[1:])))
    time.sleep(sleeptime)

    # - determine process PID and prefix for Win32 PDH logging
    pidsAfter = _GetMozillaPIDs(procname)
    newPids = [pid for pid in pidsAfter if pid not in pidsBefore]
    print("newPids:",repr(newPids))
    if len(newPids) == 0:
        raise "No new Mozilla PIDs were found. The same Komodo was probably already running."
    elif len(newPids) > 1:
        raise "More that one Mozilla process was started by spawning Komodo!"
    else:
        pid = newPids[0]

    # - get a WScript handle on it, for SendKeys playing
    komodo = win32com.client.Dispatch("WScript.Shell")
    komodo.AppActivate("[%s" % testFile) # find the Komodo window
    win32api.Sleep(100) # wait 0.1 secs for it to "wake up"
    
    f = open(testFile)
    keys = f.read()
    f.close()
    
    # Randomly edit the file (to muck with linting), measuring the
    # memory.
    try:
        timer = Stopwatch()
        timer.startTimerFor("typing")
        # - get a PDH counter to measure the memory working set
        #pdhCounter = Win32PDHCounter(pid)
        #pdhCounter.addCounter("Working Set")
        data = []
        err = 0
        for ch in keys:
            # As long as the number of loops in even the file will end off the
            # same as when it started. This is important because there is no way
            # to end Komodo 1.1 from the keyboard without saving the changed
            # file.
            try:
                if ch == '\r':
                    continue
                if ch == '\n':
                    komodo.SendKeys("{ENTER}")
                    # defeat komodo's autoindent
                    komodo.SendKeys("{HOME}")
                    komodo.SendKeys("{HOME}")
                elif ch == '\t':
                    komodo.SendKeys("{TAB}")
                elif ch in ["(",")","{","}","[","]","+","^","%","~"]:
                    ch = "{%s}"%(ch)
                    komodo.SendKeys(ch)
                else:
                    komodo.SendKeys(ch)
            except:
                print("unable to send ",repr(ch))
                win32api.Sleep(1)
            
            # emulate some kind of delay in typing
            win32api.Sleep(1)
            
            #pdhCounter.collect()
            #mem = pdhCounter.getCounterValue("Working Set")
            #data.append(mem)
            
            #try:
            #    log = "[%4d] write %-7s - pause %4dms - memory is %8.0f bytes (%+9.0f)\n"\
            #          % (i, repr(ch), pause, mem, mem-data[0])
            #    out.write(log)
            #except IOError: # catch this exception that seems to happen rarely
            #    import traceback
            #    traceback.print_exception(*sys.exc_info())
            #    print "XXX i=%s (%s), ch=%s (%s), pause=%s (%s), mem=%s (%s)"\
            #          % (i, type(i), ch, type(ch), pause, type(pause), mem, type(mem))
            #    print "XXX log='%s' (%s)" % (log, type(log))
    
    finally:
        # close Komodo
        timer.stopTimerFor("typing")
        duration = timer.readTimerFor("typing")
        print("typing took ",duration)
        print("each char took ",(duration/len(keys)))
        #komodo.SendKeys("%(f)x")    # Alt-fx
        # big delay to see if komodo will finish eating the key buffer
        win32api.Sleep(5000)        # wait for "Save Changes" dialog to come up
        #komodo.SendKeys("n")        # select: "No"
        #try:
        #    komodo.SendKeys("{ENTER}")  # select default ("n" doesn't work in Komodo 1.1)
        #except:
        #    pass


#---- mainline

def main(argv):
    if not sys.platform.startswith("win"):
        usage(1, "This script currently only works on Windows.")

    # defaults
    verbose = 1
    komodoExe = which.which("komodo")
    out = sys.stdout

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'ho',
                                   ['help', 'komodo='])
    except getopt.error as msg:
        usage(1, msg)

    for opt, optarg  in opts:
        if opt in ('-h', '--help'):
            usage(0)
        elif opt == '-o':
            out = sys.stdout 
        elif opt == '--komodo':
            komodoExe = optarg
            if not os.path.isfile(optarg):
                usage(1, "Given komodo executable does not exist: '%s'"\
                         % komodoExe)
    testFile = args[0]
    blankFile = args[1]
    if not testFile or not blankFile:
        usage(1, "You must specify some files to work on.")

    #for testFile in testFiles:
    measure_typing_speed(testFile, blankFile, komodoExe, out, verbose)
    


if __name__ == "__main__":
    main(sys.argv)

