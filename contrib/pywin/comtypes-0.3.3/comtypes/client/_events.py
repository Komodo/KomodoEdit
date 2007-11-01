import ctypes
import comtypes
from comtypes.hresult import *
import comtypes.automation
import comtypes.typeinfo
import comtypes.connectionpoints
import logging
logger = logging.getLogger(__name__)


# XXX move into comtypes
def _getmemid(idlflags):
    # get the dispid from the idlflags sequence
    return [memid for memid in idlflags if isinstance(memid, int)][0]

# XXX move into comtypes?
def _get_dispmap(interface):
    # return a dictionary mapping dispid numbers to method names
    assert issubclass(interface, comtypes.automation.IDispatch)

    dispmap = {}
    if "dual" in interface._idlflags_:
        # It would be nice if that would work:
##        for info in interface._methods_:
##            mth = getattr(interface, info.name)
##            memid = mth.im_func.memid
    
        # See also MSDN docs for the 'defaultvtable' idl flag, or
        # IMPLTYPEFLAG_DEFAULTVTABLE.  This is not a flag of the
        # interface, but of the coclass!
        #
        # Use the _methods_ list
        assert not hasattr(interface, "_disp_methods_")
        for restype, name, argtypes, paramflags, idlflags, helpstring in interface._methods_:
            memid = _getmemid(idlflags)
            dispmap[memid] = name
    else:
        # Use _disp_methods_
        # tag, name, idlflags, restype(?), argtypes(?)
        for tag, name, idlflags, restype, argtypes in interface._disp_methods_:
            memid = _getmemid(idlflags)
            dispmap[memid] = name
    return dispmap

class _AdviseConnection(object):
    def __init__(self, source, interface, receiver):
        cpc = source.QueryInterface(comtypes.connectionpoints.IConnectionPointContainer)
        self.cp = cpc.FindConnectionPoint(ctypes.byref(interface._iid_))
        logger.debug("Start advise %s", interface)
        self.cookie = self.cp.Advise(receiver)
        self.receiver = receiver

    def __del__(self):
        try:
            self.cp.Unadvise(self.cookie)
        except (comtypes.COMError, WindowsError):
            # Are we sure we want to ignore errors here?
            pass

def FindOutgoingInterface(source):
    """XXX Describe the strategy that is used..."""
    # QI for IConnectionPointContainer and then
    # EnumConnectionPoints would also work, but doesn't make
    # sense.  The connection interfaces are enumerated in
    # arbitrary order, so we cannot decide on out own which one to
    # use.
    #
    # Hm, if IConnectionPointContainer::EnumConnectionPoints only has
    # one connectionpoint, we could use that one.
    try:
        pci = source.QueryInterface(comtypes.typeinfo.IProvideClassInfo2)
        guid = pci.GetGUID(1)
    except comtypes.COMError:
        pass
    else:
        # another try: block needed?
        try:
            interface = comtypes.com_interface_registry[str(guid)]
        except KeyError:
            tinfo = pci.GetClassInfo()
            tlib, index = tinfo.GetContainingTypeLib()
            from comtypes.client import GetModule
            GetModule(tlib)
            interface = comtypes.com_interface_registry[str(guid)]
        logger.debug("%s using sinkinterface %s", source, interface)
        return interface

    clsid = source.__dict__.get('__clsid')
    try:
        interface = comtypes.com_coclass_registry[clsid]._outgoing_interfaces_[0]
    except KeyError:
        pass
    else:
        logger.debug("%s using sinkinterface from clsid %s", source, interface)
        return interface

    raise TypeError("cannot determine source interface")

class _DispEventReceiver(comtypes.COMObject):
    _com_interfaces_ = [comtypes.automation.IDispatch]
    # Hrm.  If the receiving interface is implemented as a dual interface,
    # the methods implementations expect 'out, retval' parameters in their
    # argument list.
    #
    # What would happen if we call ITypeInfo::Invoke() ?
    # If we call the methods directly, shouldn't we pass pVarResult
    # as last parameter?
    def IDispatch_Invoke(self, this, memid, riid, lcid, wFlags, pDispParams,
                         pVarResult, pExcepInfo, puArgErr):
        mth = self.dispmap.get(memid, None)
        if mth is None:
            return S_OK
        dp = pDispParams[0]
        # DISPPARAMS contains the arguments in reverse order
        args = [dp.rgvarg[i].value for i in range(dp.cArgs)]
        ##print "Event", self, memid, mth, args
        result = self.dispmap[memid](None, *args[::-1])
        if pVarResult:
            pVarResult[0].value = result
        return S_OK

    def GetTypeInfoCount(self, this, presult):
        if not presult:
            return E_POINTER
        presult[0] = 0
        return S_OK

    def GetTypeInfo(self, this, itinfo, lcid, pptinfo):
        return E_NOTIMPL

    def GetIDsOfNames(self, this, riid, rgszNames, cNames, lcid, rgDispId):
        return E_NOTIMPL


def GetDispEventReceiver(interface, sink):
    methods = {} # maps memid to function
    interfaces = interface.mro()[:-3] # skip IDispatch, IUnknown, object
    interface_names = [itf.__name__ for itf in interfaces]
    for itf in interfaces:
        for memid, name in _get_dispmap(itf).iteritems():
            # find methods to call, if not found ignore event
            for itf_name in interface_names:
                mth = getattr(sink, "%s_%s" % (itf_name, name), None)
                if mth is not None:
                    break
            else:
                mth = getattr(sink, name, lambda *args: 0)
            methods[memid] = mth

    # XX Move this stuff into _DispEventReceiver.__init__() ?
    rcv = _DispEventReceiver()
    rcv.dispmap = methods
    rcv._com_pointers_[interface._iid_] = rcv._com_pointers_[comtypes.automation.IDispatch._iid_]
    return rcv

def GetCustomEventReceiver(interface, sink):
    class EventReceiver(comtypes.COMObject):
        _com_interfaces_ = [interface]

    for itf in interface.mro()[:-2]: # skip object and IUnknown
        for info in itf._methods_:
            restype, name, argtypes, paramflags, idlflags, docstring = info

            mth = getattr(sink, name, lambda self, this, *args: 0)
            setattr(EventReceiver, name, mth)
    rcv = EventReceiver()
    return rcv


def GetEvents(source, sink, interface=None):
    """Receive COM events from 'source'.  Events will call methods on
    the 'sink' object.  'interface' is the source interface to use.
    """
    # When called from CreateObject, the sourceinterface has already
    # been determined by the coclass.  Otherwise, the only thing that
    # makes sense is to use IProvideClassInfo2 to get the default
    # source interface.

    if interface is None:
        interface = FindOutgoingInterface(source)

    if issubclass(interface, comtypes.automation.IDispatch):
        rcv = GetDispEventReceiver(interface, sink)
    else:
        rcv = GetCustomEventReceiver(interface, sink)
    return _AdviseConnection(source, interface, rcv)

class EventDumper(object):
    """Universal sink for COM events."""

    def __getattr__(self, name):
        "Create event handler methods on demand"
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        print "# event found:", name
        def handler(*args, **kw):
            print "Event %s(%s)" % (name, ", ".join([repr(a) for a in args]))
            return 0
        return handler

def ShowEvents(source, interface=None):
    """Receive COM events from 'source'.  A special event sink will be
    used that first prints the names of events that are found in the
    outgoing interface, and will also print out the events when they
    are fired.
    """
    return comtypes.client.GetEvents(source, sink=EventDumper(), interface=interface)
