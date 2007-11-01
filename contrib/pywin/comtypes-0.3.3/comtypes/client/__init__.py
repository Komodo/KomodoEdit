'''High level client level COM support module.
'''

################################################################
#
# TODO: 
#
# - rename wrap
#
# - beautify the code generator output (import statements at the top)
#
# - add a GetTypelibWrapper(obj) function?
#
# - refactor this code into several modules now that this is a package
#
################################################################

# comtypes.client

import sys, os, new
import ctypes

import comtypes
from comtypes.hresult import *
import comtypes.automation
import comtypes.typeinfo
import comtypes.client.dynamic

from comtypes.client._events import GetEvents, ShowEvents
from comtypes.client._generate import GetModule

import logging
logger = logging.getLogger(__name__)

__all__ = ["CreateObject", "GetActiveObject", "CoGetObject",
           "GetEvents", "ShowEvents", "GetModule"]

################################################################
# Determine the directory where generated modules live.
# Creates the directory if it doesn't exist - if possible.
def _find_gen_dir():
    if not os.path.isfile(comtypes.__file__):
        try:
            from comtypes import gen
        except ImportError:
            module = sys.modules["comtypes.gen"] = new.module("comtypes.gen")
            comtypes.gen = module
        return None
    # determine the place where generated modules live
    comtypes_path = os.path.join(comtypes.__path__[0], "gen")
    if not os.path.exists(comtypes_path):
        os.mkdir(comtypes_path)
    comtypes_init = os.path.join(comtypes_path, "__init__.py")
    if not os.path.exists(comtypes_init):
        ofi = open(comtypes_init, "w")
        ofi.write("# comtypes.gen package, directory for generated files.\n")
        ofi.close()
    from comtypes import gen
    return gen.__path__[0]

gen_dir = _find_gen_dir()
import comtypes.gen

### for testing
##gen_dir = None
    
################################################################

def wrap_outparam(punk):
    logger.info("wrap_outparam(%s)", punk)
    if not punk:
        return None
    if punk.__com_interface__ == comtypes.automation.IDispatch:
        return wrap(punk)
    return punk

# XXX rename this!
def wrap(punk):
    """Try to QueryInterface a COM pointer to the 'most useful'
    interface.
    
    Get type information for the provided object, either via
    IDispatch.GetTypeInfo(), or via IProvideClassInfo.GetClassInfo().
    Generate a wrapper module for the typelib, and QI for the
    interface found.
    """
    if not punk: # NULL COM pointer
        return punk # or should we return None?
    # find the typelib and the interface name
    logger.info("wrap(%s)", punk)
    try:
        pci = punk.QueryInterface(comtypes.typeinfo.IProvideClassInfo)
        logger.info("Does implement IProvideClassInfo")
        tinfo = pci.GetClassInfo() # TypeInfo for the CoClass
        # find the interface marked as default
        ta = tinfo.GetTypeAttr()
        for index in range(ta.cImplTypes):
            if tinfo.GetImplTypeFlags(index) == 1:
                break
        else:
            if ta.cImplTypes != 1:
                # Hm, should we use dynamic now?
                raise TypeError, "No default interface found"
            # Only one interface implemented, use that (even if
            # not marked as default).
            index = 0
        href = tinfo.GetRefTypeOfImplType(index)
        tinfo = tinfo.GetRefTypeInfo(href)
    except comtypes.COMError:
        logger.info("Does NOT implement IProvideClassInfo")
        try:
            pdisp = punk.QueryInterface(comtypes.automation.IDispatch)
        except comtypes.COMError:
            logger.info("No Dispatch interface: %s", punk)
            return punk
        try:
            tinfo = pdisp.GetTypeInfo(0)
        except comtypes.COMError:
            pdisp = comtypes.client.dynamic.Dispatch(pdisp)
            logger.info("IDispatch.GetTypeInfo(0) failed: %s" % pdisp)
            return pdisp
    typeattr = tinfo.GetTypeAttr()
    logger.info("Default interface is %s", typeattr.guid)
    try:
        punk.QueryInterface(comtypes.IUnknown, typeattr.guid)
    except comtypes.COMError, details:
        logger.info("Does not implement default interface, returning dynamic object")
        return comtypes.client.dynamic.Dispatch(punk)

    itf_name = tinfo.GetDocumentation(-1)[0] # interface name
    tlib = tinfo.GetContainingTypeLib()[0] # typelib

    # import the wrapper, generating it on demand
    mod = GetModule(tlib)
    # Python interface class
    interface = getattr(mod, itf_name)
    logger.info("Implements default interface from typeinfo %s", interface)
    # QI for this interface
    # XXX
    # What to do if this fails?
    # In the following example the engine.Eval() call returns
    # such an object.
    #
    # engine = CreateObject("MsScriptControl.ScriptControl")
    # engine.Language = "JScript"
    # engine.Eval("[1, 2, 3]")
    #
    # Could the above code, as an optimization, check that QI works,
    # *before* generating the wrapper module?
    result = punk.QueryInterface(interface)
    logger.info("Final result is %s", result)
    return result

# Should we do this for POINTER(IUnknown) also?
ctypes.POINTER(comtypes.automation.IDispatch).__ctypes_from_outparam__ = wrap_outparam

################################################################
#
# Object creation
#
def GetActiveObject(progid, interface=None):
    clsid = comtypes.GUID.from_progid(progid)
    if interface is None:
        interface = getattr(progid, "_com_interfaces_", [None])[0]
    obj = comtypes.GetActiveObject(clsid, interface=interface)
    return _manage(obj, clsid, interface=interface)
                    
def _manage(obj, clsid, interface):
    obj.__dict__['__clsid'] = str(clsid)
    if interface is None:
        obj = wrap(obj)
    return obj


def CreateObject(progid,                  # which object to create
                 clsctx=None,             # how to create the object
                 machine=None,            # where to create the object
                 interface=None):         # the interface we want
    """Create a COM object from 'progid', and try to QueryInterface()
    it to the most useful interface, generating typelib support on
    demand.  A pointer to this interface is returned.

    'progid' may be a string like "InternetExplorer.Application",
       a string specifying a clsid, a GUID instance, or an object with
       a _clsid_ attribute which should be any of the above.
    'clsctx' specifies how to create the object, use the CLSCTX_... constants.
    'machine' allows to specify a remote machine to create the object on.

    You can also later request to receive events with GetEvents().
    """
    clsid = comtypes.GUID.from_progid(progid)
    logger.debug("%s -> %s", progid, clsid)
    if interface is None:
        interface = getattr(progid, "_com_interfaces_", [None])[0]
    if machine is None:
        logger.debug("CoCreateInstance(%s, clsctx=%s, interface=%s)",
                     clsid, clsctx, interface)
        obj = comtypes.CoCreateInstance(clsid, clsctx=clsctx, interface=interface)
    else:
        logger.debug("CoCreateInstanceEx(%s, clsctx=%s, interface=%s, machine=%s)",
                     clsid, clsctx, interface, machine)
        obj = comtypes.CoCreateInstanceEx(clsid, clsctx=clsctx, interface=interface, machine=machine)
    return _manage(obj, clsid, interface=interface)

def CoGetObject(displayname, interface=None):
    """Create an object by calling CoGetObject(displayname).

    Additional parameters have the same meaning as in CreateObject().
    """
    punk = comtypes.CoGetObject(displayname, interface)
    return _manage(punk,
                   clsid=None,
                   interface=interface)


################################################################
# Helper function: in single threaded appartments, a message loop must
# be running to dispatch COM events.

def PumpWaitingMessages():
    """Single threaded COM apartments need to run a messageloop to
    dispatch events correctly.  This function should be called
    periodically if no other message loop is running (in a console
    application, for example).
    """
    user32 = ctypes.windll.user32
    from ctypes.wintypes import MSG
    msg = MSG()
    PM_REMOVE = 0x0001
    while user32.PeekMessageA(ctypes.byref(msg), None, 0, 0, PM_REMOVE):
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageA(ctypes.byref(msg))


