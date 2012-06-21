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

# PyXPCOM Hook for the timeline service.
# Installs an xpcom 'tracer', which uses the Moz timeline
# service to record times for components.

import timeline # our timeline utilities
import xpcom.server
from xpcom.server import loader, factory, module
from xpcom.server import DefaultPolicy
from xpcom import _xpcom
import os

import warnings
warnings.warn("'timeline_hook' module is deprecated and will soon be removed.",
              DeprecationWarning)

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
