# PyXPCOM Hook for the timeline service.
# Installs an xpcom 'tracer', which uses the Moz timeline
# service to record times for components.

import timeline # our timeline utilities
import xpcom.server
from xpcom.server import loader, factory, module
from xpcom.server import DefaultPolicy
from xpcom import _xpcom
import os

# A wrapper around a function - looks like a function,
# but actually profiles the delegate.
class TracerDelegate:
    def __init__(self, ob_name, func):
        self.timer_name = "PyXPCOM: " + ob_name
        self.func = func
    def __call__(self, *args):
        func_repr = self.func.__name__ + repr(args)
        timer_func_name = self.timer_name + "." + func_repr
        timeline.enter(timer_func_name)
        timeline.startTimer(self.timer_name)
        try:
            return self.func(*args)
        finally:
            timeline.stopTimer(self.timer_name)
            timeline.leave(timer_func_name)
            timeline.markTimer(self.timer_name, func_repr)

# A wrapper around each of our XPCOM objects.  All PyXPCOM calls
# in are made on this object, which creates a TracerDelagate around
# every function.  As the function is called, it collects profile info.
class Tracer:
    def __init__(self, ob):
        self.__dict__['_ob'] = ob
    def __repr__(self):
        return "<Tracer around %r>" % (self._ob,)
    def __str__(self):
        return self.__repr__()
    def __getattr__(self, attr):
        ret = getattr(self._ob, attr) # Attribute error just goes up
        # If not collecting, or we have any methods, and ours isn't listed, don't profile.
        if callable(ret):
            ob_name = self._ob.__class__.__module__ + "." + self._ob.__class__.__name__
            ret = TracerDelegate(ob_name, ret)
        return ret
    def __setattr__(self, attr, val):
        return setattr(self._ob, attr, val)

# A ComponentLoader that knows about the timeline
class TimelineComponentLoader(loader.PythonComponentLoader):
    def __init__(self, *args):
        loader.PythonComponentLoader.__init__(self, *args)
        self.moduleFactory = Module
    def _getCOMModuleForLocation(self, componentFile):
        timer_name = "PyXPCOM component import"
        timeline.startTimer(timer_name)
        try:
            return loader.PythonComponentLoader._getCOMModuleForLocation(self, componentFile)
        finally:
            timeline.stopTimer(timer_name)
            timeline.markTimer(timer_name, componentFile.path)
    def getFactory(self, clsid, location, type):
        # wrap to avoid tracer
        ret = loader.PythonComponentLoader.getFactory(self, clsid, location, type)
        return ret

class Factory(factory.Factory):
    def createInstance(self, outer, iid):
        if self.klass is TimelineComponentLoader:
            # short circuit for loader
            ret = factory.Factory.createInstance(self, outer, iid)
            ret = _xpcom.WrapObject(DefaultPolicy(ret, iid), iid, 0)
            timeline.mark("PyXPCOM component loader ready to rock")
            return ret

        klass = self.klass
        this_name = "%s.%s" % (klass.__module__, klass.__name__)
        enter_name = "constructing " + this_name
        timer_name = "PyXPCOM component creation"
        timeline.enter(enter_name)
        timeline.startTimer(timer_name)
        try:
            return factory.Factory.createInstance(self, outer, iid)
        finally:
            timeline.stopTimer(timer_name)
            timeline.leave(enter_name)
            timeline.markTimer(timer_name, this_name)

class Module(module.Module):
    def __init__(self, *args):
        module.Module.__init__(self, *args)
        self.klassFactory = Factory
    def getClassObject(self, compMgr, clsid, iid):
        ret = module.Module.getClassObject(self, compMgr, clsid, iid)
        ret = _xpcom.WrapObject(DefaultPolicy(ret, iid), iid, 0)
        return ret

def NS_GetModule( serviceManager, nsIFile ):
    mod = Module( [TimelineComponentLoader] )
    # wrap it manually to avoid our tracer
    iid = _xpcom.IID_nsIModule
    mod = _xpcom.WrapObject(DefaultPolicy( mod, iid ), iid, 0)
    return mod

def tracer_unwrap(ob):
    return getattr(ob, "_ob", ob)

def _makeTracer(ob):
    # Installed as a global XPCOM function that will be called
    # to wrap each XPCOM object created.
    # In some cases we may be asked to wrap ourself, so handle that.
    if isinstance(ob, Tracer):
        return ob
    return Tracer(ob)

if timeline.getService() is not None:
    if os.environ.has_key("KO_TIMELINE_PYXPCOM"):
        print "PyXPCOM timeline hooks installed"
        if xpcom.server.tracer is not None:
            print "Error: xpcom tracer already installed"
            raise COMException(nsError.NS_ERROR_UNEXPECTED)
        xpcom.server.tracer = _makeTracer
        xpcom.server.tracer_unwrap = tracer_unwrap
        # and patch up the entry point
        xpcom.server.NS_GetModule = NS_GetModule
    else:
        print "PyXPCOM timeline hooks NOT installed (KO_TIMELINE_PYXPCOM not set)"
else:
    # We are only imported when the timeline service is
    # compiled in - but it may not be enabled.
    print "PyXPCOM timeline hooks NOT installed (timeline service currently disabled)"
