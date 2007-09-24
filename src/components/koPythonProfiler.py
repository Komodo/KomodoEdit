# A Python XPCOM component profiler.  Its not perfect, but it can be useful.
#
# The profiler is a service, so you create it like thus:
#
#  profiler = Components.classes["@activestate.com/koPythonProfiler;1"]. \
#           getService(Components.interfaces.koIPythonProfiler);
#
# You then tell it what classes you want to profile.  You can pass contract 
# IDs, class IDs, or just Python class names.
#
# Eg:
#  profiler.addClasses("@activestate.com/stack;1 koPythonDebugProperty koPythonDebugStackFrame");
# or
#  profiler.addAllClasses()
#
# Note that only classes _created_ after the AddClasses call will be profiled.
# Calls to objects created before addClasses wont.
#
# It will then collect stats: you can call profiler.dump() at any time, and 
# profiler.reset() will reset the stats.
#
# That is the good news :)  The bad news is the data seems to be missing 
# chunks.  Im not exactly sure why...


import xpcom.components
from xpcom import nsError, COMException, components

import sys, profile, pstats, os

profiler = None
profiler_stats = None

# A wrapper around a function - looks like a function,
# but actually profiles the delegate.
class TracerDelegate:
    def __init__(self, callme):
        self.callme = callme
    def __call__(self, *args):
        global profiler_stats
        profiler = profile.Profile()
        if profiler_stats is None:
            profiler_stats = pstats.Stats(profiler)
        ps = profiler_stats # thread-etc safe - even if the global goes away under us, this wont!
        ret = profiler.runcall(self.callme, *args)
        if ps is not None:
            ps.add(profiler)
        return ret

# A wrapper around each of our XPCOM objects.  All PyXPCOM calls
# in are made on this object, which creates a TracerDelagate around
# every function.  As the function is called, it collects profile info.
class Tracer:
    def __init__(self, ob, profiler_svc):
        self.__dict__['_ob'] = ob
        self.__dict__['_profiler_service_'] = profiler_svc
        # build the list of methods - if None, we trace on all.
        methods = profiler_svc.methods.get(ob.__class__.__name__)
        self.__dict__['_methods'] = methods
    def __repr__(self):
        return "<Tracer around %r>" % (self._ob,)
    def __str__(self):
        return "<Tracer around %r>" % (self._ob,)
    def __getattr__(self, attr):
        ret = getattr(self._ob, attr) # Attribute error just goes up
        # If not collecting, or we have any methods, and ours isn't listed, don't profile.
        methods = self._methods
        if (not self._profiler_service_.collecting) or (methods is not None and not methods.has_key(attr)):
            return ret
        if callable(ret):
            return TracerDelegate(ret)
        else:
            if not attr.startswith("_com_") and not attr.startswith("_reg_"):
                ps = self._profiler_service_
                ps.getter_accesses[attr] = ps.getter_accesses.setdefault(attr,0) + 1
            return ret
    def __setattr__(self, attr, val):
        if self.__dict__.has_key(attr):
            self.__dict__[attr] = val
            return
        ps = self._profiler_service_
        ps.setter_accesses[attr] = ps.setter_accesses.setdefault(attr,0) + 1
        setattr(self._ob, attr, val)

def tracer_unwrap(ob):
    return getattr(ob, "_ob", ob)

# The XPCOM service.
class koIPythonProfiler:
    _com_interfaces_ = xpcom.components.interfaces.koIPythonProfiler
    _reg_clsid_ = "{8519f7b7-4f2e-4306-b45f-c1a14cfc32df}"
    _reg_contractid_ = "@activestate.com/koPythonProfiler;1"

    def __init__(self):
        self.resetStats()
        self.install()
        self._dumpFilename=None
        
    def install( self ):
        # Result: void - None
        if xpcom.server.tracer is not None:
            raise COMException(nsError.NS_ERROR_UNEXPECTED)
        self.collecting = 1
        self.classes = {}
        self.methods = {}
        self.all_classes = 0
        xpcom.server.tracer = self._makeTracer
        xpcom.server.tracer_unwrap = tracer_unwrap

    def uninstall( self ):
        # Result: void - None
        if xpcom.server.tracer is not self._makeTracer:
            raise COMException(nsError.NS_ERROR_UNEXPECTED)
        self.collecting = 0
        xpcom.server.tracer = xpcom.server.tracer_unwrap = None

    def _makeTracer(self, ob):
        # Installed as a global XPCOM function that if exists, will be called
        # to wrap each XPCOM object created.
        # In some cases we may be asked to wrap ourself, so handle that.
        if isinstance(ob, Tracer):
            return ob
        if self.all_classes or \
           self.classes.get( getattr(ob, "_reg_contractid_", "") ) or \
           self.classes.get( getattr(ob, "_reg_clsid_", "")) or \
           self.classes.get( ob.__class__.__name__ ):
            return Tracer(ob, self)
        # Dont profile this object.
        return ob
    
    def addClasses( self, name ):
        # Result: void - None
        # In: name: string
        for n in name.split():
            try:
                k, method = n.split(".")
            except ValueError:
                k = n
                method = None
            self.classes[k] = 1
            if method is not None:
                self.methods.setdefault(k, {})[method] = 1

    def addAllClasses(self):
        self.all_classes = 1

    def resetStats( self ):
        # Result: void - None
        global profiler_stats
        profiler_stats = None
        self.getter_accesses = {}
        self.setter_accesses = {}

    def dump( self, sortNames ):
        self.dumpSome(sortNames, -1)

    def dumpFile( self, filename ):
        self._dumpFilename = filename

    def dumpToFile(self, filename, sortNames):
        oldfn = self._dumpFilename
        self._dumpFilename = filename
        self.dumpSome(sortNames, -1)
        self._dumpFilename = oldfn

    def _startDump(self):
        koDirs = components.classes["@activestate.com/koDirs;1"]\
                 .getService(components.interfaces.koIDirs)
        logFileName = os.path.join(koDirs.userDataDir, "log", self._dumpFilename)
        file = open(logFileName, 'w')
        if not file:
            print "Error opening ",self._dumpFilename
            return
        self.old_stdout = sys.stdout
        sys.stdout = file
    
    def _finishDump(self):
        sys.stdout = self.old_stdout
        
    def dumpSome( self, sortNames, howMany ):
        # Result: void - None
        if self._dumpFilename: self._startDump();
        try:
            if not sortNames:
                sortNames = "cumulative"
            print "Dumping Python XPCOM profile statistics"
            print "=============================="
            if profiler_stats is None:
                print "No profile call stats collected!"
            else:
                profiler_stats.strip_dirs().sort_stats(sortNames).print_stats(howMany)
            print "%-30s%s" % ("Attribute Gets", "Number")
            print "-" * 36
            for name, num in self.getter_accesses.items():
                print "%-30s%d" % (name, num)
            print "%-30s%s" % ("Attribute Sets", "Number")
            print "-" * 36
            for name, num in self.setter_accesses.items():
                print "%-30s%d" % (name, num)
        finally:
            if self._dumpFilename: self._finishDump();