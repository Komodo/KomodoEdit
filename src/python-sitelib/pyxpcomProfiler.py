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

import xpcom, xpcom.server
#import hotshot
import cProfile as profile
import time
import threading

class koProfile:
    def __init__(self):
        #self.prof = hotshot.Profile("kogrind.prof", lineevents=1)
        self.prof = profile.Profile()
        self.lock = threading.Lock()

    def __del__(self):
        self.prof.close()

    def acquire(self):
        return self.lock.acquire(0)

    def release(self):
        self.lock.release()

    def print_stats(self, sort=-1, limit=None):
        import pstats
        stats = pstats.Stats(self.prof)
        #stats.strip_dirs()
        stats.sort_stats(sort)
        stats.print_stats(limit)

    def save_stats(self, filename):
        self.prof.dump_stats(filename)

# store in xpcom module
xpcom._koprofiler = koProfile()

xpcom_recordings = {}

class XPCOMRecorder:
    """Object to record pyxpcom usage"""
    def __init__(self, name):
        self.name = name
        self.calls = {}
        self.getters = {}
        self.setters = {}

    def recordCall(self, attr):
        # [timespent, numcalls]
        value = self.calls.get(attr)
        if value is None:
            value = [0, 1]
            self.calls[attr] = value
        else:
            value[1] += 1
        return value

    def recordGetter(self, attr):
        self.getters[attr] = self.getters.get(attr, 0) + 1

    def recordSetter(self, attr):
        self.setters[attr] = self.setters.get(attr, 0) + 1

    def totalcalltime(self):
        return sum([x[0] for x in self.calls.values()])

    def totalcallcount(self):
        return sum([x[1] for x in self.calls.values()])

    def __len__(self):
        return self.totalcallcount() + sum(self.getters.values()) + sum(self.setters.values())

    def print_stats(self):
        print "%s" % (self.name)
        if self.calls:
            print "  Calls: %d, Time: %f" % (self.totalcallcount(), self.totalcalltime())
            for name, recorder in sorted(self.calls.items(), key=lambda (k,v): (v,k), reverse=True):
                print "      %-30s%5d %f" % (name, recorder[1], recorder[0])
        if self.getters:
            print "  Getters: %d" % (sum(self.getters.values()))
            for name, num in sorted(self.getters.items(), key=lambda (k,v): (v,k), reverse=True):
                print "      %-30s%d" % (name, num)
        if self.setters:
            print "  Setters: %d" % (sum(self.setters.values()))
            for name, num in sorted(self.setters.items(), key=lambda (k,v): (v,k), reverse=True):
                print "      %-30s%d" % (name, num)
        #print

def getXPCOMRecorder(xpcomObject):
    """Return the base xpcom recorder object for this python xpcom object.

    Tries to record all the same xpcom instances for one interface in the same
    recorder object.
    """
    names = None
    if hasattr(xpcomObject, "_interface_names_"):
        names = [x.name for x in xpcomObject._interface_names_]
    if not names:
        com_interfaces = getattr(xpcomObject, "_com_interfaces_", None)
        if com_interfaces:
            if not isinstance(com_interfaces, (tuple, list)):
                names = [com_interfaces.name]
            else:
                names = [x.name for x in com_interfaces]
    if names is not None:
        name = "_".join(names)
    else:
        name = repr(xpcomObject)
    recorder = xpcom_recordings.get(name)
    if recorder is None:
        recorder = XPCOMRecorder(name)
        xpcom_recordings[name] = recorder
    return recorder

# A wrapper around a function - looks like a function,
# but actually profiles the delegate.
class TracerDelegate:
    def __init__(self, callme, callstats=None):
        self.callme = callme
        self.callstats = callstats
    def __call__(self, *args):
        if not xpcom._koprofiler.acquire():
            return apply(self.callme, args)
        try:
            if self.callstats:
                t1 = time.time()
            return xpcom._koprofiler.prof.runcall(self.callme, *args)
        finally:
            if self.callstats:
                self.callstats[0] += time.time() - t1
            xpcom._koprofiler.release()

# A wrapper around each of our XPCOM objects.  All PyXPCOM calls
# in are made on this object, which creates a TracerDelagate around
# every function.  As the function is called, it collects profile info.
class Tracer:
    def __init__(self, ob):
        self.__dict__['_ob'] = ob
        self.__dict__['_recorder'] = getXPCOMRecorder(ob)
    def __repr__(self):
        return "<Tracer around %r>" % (self._ob,)
    def __str__(self):
        return "<Tracer around %r>" % (self._ob,)
    def __getattr__(self, attr):
        ret = getattr(self._ob, attr) # Attribute error just goes up
        if callable(ret):
            callstats = None
            if not attr.startswith("_com_") and not attr.startswith("_reg_"):
                callstats = self.__dict__['_recorder'].recordCall(attr)
            return TracerDelegate(ret, callstats)
        else:
            if not attr.startswith("_com_") and not attr.startswith("_reg_"):
                self.__dict__['_recorder'].recordGetter(attr)
            return ret
    def __setattr__(self, attr, val):
        if self.__dict__.has_key(attr):
            self.__dict__[attr] = val
            return
        if not attr.startswith("_com_") and not attr.startswith("_reg_"):
                self.__dict__['_recorder'].recordSetter(attr)
        setattr(self._ob, attr, val)

def print_stats():
    """Print out the pyXPCOM stats and the python main thread profiler stats"""
    def recorder_cmp(a, b):
        return cmp(a[0].totalcalltime(), b[0].totalcalltime())
    for name, recorder in sorted(xpcom_recordings.items(),
                                 cmp=recorder_cmp,
                                 key=lambda (k,v): (v,k), reverse=True):
        if len(recorder) > 0:
            recorder.print_stats()
    print
    print "*" * 60
    print
    xpcom._koprofiler.print_stats(sort='time', limit=100)
    print "*" * 60
    print "Stats finished\n"


# Installed as a global XPCOM function that if exists, will be called
# to wrap each XPCOM object created.
def MakeTracer(ob):
    # In some cases we may be asked to wrap ourself, so handle that.
    if isinstance(ob, Tracer):
        return ob
    return Tracer(ob)

def UnwrapTracer(ob):
    if isinstance(ob, Tracer):
        return ob._ob
    return ob

xpcom.server.tracer = MakeTracer
xpcom.server.tracer_unwrap = UnwrapTracer

class xpcomShutdownObserver(object):
    _com_interfaces_ = [xpcom.components.interfaces.nsIObserver]
    def observe(self, subject, topic, data):
        if topic == "xpcom-shutdown":
            print_stats()
            xpcom._koprofiler.save_stats("koprofile.data")

xpcomObs = xpcomShutdownObserver()
obsSvc = xpcom.components.classes["@mozilla.org/observer-service;1"].\
               getService(xpcom.components.interfaces.nsIObserverService)
obsSvc.addObserver(xpcomObs, 'xpcom-shutdown', False)
