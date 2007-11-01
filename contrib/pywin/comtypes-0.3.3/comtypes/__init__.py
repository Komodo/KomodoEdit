import new, types, sys, os

__version__ = "0.3.3"

from ctypes import *
from _ctypes import COMError

import logging
logger = logging.getLogger(__name__)

##class IDLWarning(UserWarning):
##    "Warn about questionable type information"

from comtypes.GUID import GUID
_GUID = GUID
IID = GUID
DWORD = c_ulong

wireHWND = c_ulong

################################################################
# About COM apartments:
# http://blogs.msdn.com/larryosterman/archive/2004/04/28/122240.aspx
################################################################

################################################################
# Where should the __ctypes_from_param__ story go?
# And what would be the 'correct' name for that method?
################################################################
# constants for object creation
CLSCTX_INPROC_SERVER = 1
CLSCTX_INPROC_HANDLER = 2
CLSCTX_LOCAL_SERVER = 4

CLSCTX_INPROC = 3
CLSCTX_SERVER = 5
CLSCTX_ALL = 7

CLSCTX_INPROC_SERVER16 = 8
CLSCTX_REMOTE_SERVER = 16
CLSCTX_INPROC_HANDLER16 = 32
CLSCTX_RESERVED1 = 64
CLSCTX_RESERVED2 = 128
CLSCTX_RESERVED3 = 256
CLSCTX_RESERVED4 = 512
CLSCTX_NO_CODE_DOWNLOAD = 1024
CLSCTX_RESERVED5 = 2048
CLSCTX_NO_CUSTOM_MARSHAL = 4096
CLSCTX_ENABLE_CODE_DOWNLOAD = 8192
CLSCTX_NO_FAILURE_LOG = 16384
CLSCTX_DISABLE_AAA = 32768
CLSCTX_ENABLE_AAA = 65536
CLSCTX_FROM_DEFAULT_CONTEXT = 131072

tagCLSCTX = c_int # enum
CLSCTX = tagCLSCTX

################################################################
# Initialization and shutdown
_ole32 = oledll.ole32

COINIT_MULTITHREADED     = 0x0
COINIT_APARTMENTTHREADED = 0x2
COINIT_DISABLE_OLE1DDE   = 0x4
COINIT_SPEED_OVER_MEMORY = 0x8

def CoInitialize():
    return CoInitializeEx(COINIT_APARTMENTTHREADED)

def CoInitializeEx(flags=None):
    if flags is None:
        if os.name == "ce":
            flags = getattr(sys, "coinit_flags", COINIT_MULTITHREADED)
        else:
            flags = getattr(sys, "coinit_flags", COINIT_APARTMENTTHREADED)
    logger.debug("CoInitializeEx(None, %s)", flags)
    _ole32.CoInitializeEx(None, flags)

# COM is initialized automatically for the thread that imports this module
# for the first time.  sys.coinit_flags is passed as parameter to CoInitializeEx,
# if defined, otherwise COINIT_APARTMENTTHREADED is used.
# A shutdown function is registered with atexit, so that CoUninitialize is
# called when Python is shut down.
CoInitializeEx()

# We need to have CoUninitialize for multithreaded model where we have
# to initialize and uninitialize COM for every new thread (except main)
# in which we are using COM
def CoUninitialize():
    logger.debug("CoUninitialize()")
    _ole32.CoUninitialize()

def shutdown(func=_ole32.CoUninitialize,
             _debug=logger.debug):
    # Make sure no COM pointers stay in exception frames.
    sys.exc_clear()
    # Sometimes, CoUnititialize, running at Python shutdown,
    # raises an exception.  We suppress this when __debug__ is
    # False.
    _debug("Calling CoUnititialize()")
    if __debug__:
        func()
    else:
        try: func()
        except WindowsError: pass
    # Set the flag which means that calling obj.Release() is no longer
    # needed.
    _cominterface_meta._com_shutting_down = True
    _debug("CoUnititialize() done.")

import atexit
atexit.register(shutdown)
del shutdown

################################################################
# global registries.

# allows to find interface classes by guid strings (iid)
com_interface_registry = {}

# allows to find coclasses by guid strings (clsid)
com_coclass_registry = {}

################################################################
# The metaclasses...

class _cominterface_meta(type):
    """Metaclass for COM interfaces.  Automatically creates high level
    methods from COMMETHOD lists.
    """

    # This flag is set to True by the atexit handler which calls
    # CoUnititialize.
    _com_shutting_down = False

    # Creates also a POINTER type for the newly created class.
    def __new__(self, name, bases, namespace):
        methods = namespace.pop("_methods_", None)
        dispmethods = namespace.pop("_disp_methods_", None)
        cls = type.__new__(self, name, bases, namespace)

        if methods is not None:
            cls._methods_ = methods
        if dispmethods is not None:
            cls._disp_methods_ = dispmethods

        # If we sublass a COM interface, for example:
        #
        # class IDispatch(IUnknown):
        #     ....
        #
        # then we need to make sure that POINTER(IDispatch) is a
        # subclass of POINTER(IUnknown) because of the way ctypes
        # typechecks work.
        if bases == (object,):
            _ptr_bases = (cls, _compointer_base)
        else:
            _ptr_bases = (cls, POINTER(bases[0]))

        # The following function will be used as POINTER(<cominterface>).from_param.
        #
        # It fixes the problem when there are multiple python interface types
        # wrapping the same COM interface.  This could happen because some interfaces
        # are contained in multiple typelibs.
        #
        # It also allows to pass a CoClass instance to an api
        # expecting a COM interface.
        def from_param(klass, value):
            """Convert 'value' into a COM pointer to the interface.

            This method accepts a COM pointer, or a CoClass instance
            which is QueryInterface()d."""
            if value is None:
                return None
            if isinstance(value, klass):
                return value
            # multiple python interface types for the same COM interface.
            # Do we need more checks here?
            if klass._iid_ == getattr(value, "_iid_", None):
                return value
            # Accept an CoClass instance which exposes the interface required.
            try:
                table = value._com_pointers_
            except AttributeError:
                pass
            else:
                try:
                    # a kind of QueryInterface
                    return table[klass._iid_]
                except KeyError:
                    raise TypeError("Interface %s not supported" % klass._iid_)
            return value.QueryInterface(cls)

        # case insensitive attributes for COM methods and properties
        def __getattr__(self, name):
            """Implement case insensitive access to methods and properties"""
            try:
                name = self.__map_case__[name.lower()]
            except KeyError:
                raise AttributeError(name)
            else:
                return getattr(self, name)

        # __setattr__ is pretty heavy-weight, because it is called for
        # EVERY attribute assignment.  Settings a non-com attribute
        # through this function takes 8.6 usec, while without this
        # function it takes 0.7 sec - 12 times slower.
        #
        # How much faster would this be if implemented in C?
        def __setattr__(self, name, value):
            """Implement case insensitive access to methods and properties"""
            object.__setattr__(self,
                               self.__map_case__.get(name.lower(), name),
                               value)
            
        namespace = {"from_param": classmethod(from_param),
                     "__com_interface__": cls,
                     "_needs_com_addref_": None}

        if cls._case_insensitive_:
            namespace["__setattr__"] = __setattr__
            namespace["__getattr__"] = __getattr__

        # The interface 'cls' is used as a mixin.
        p = type(_compointer_base)("POINTER(%s)" % cls.__name__,
                                   _ptr_bases,
                                   namespace)
        from ctypes import _pointer_type_cache
        _pointer_type_cache[cls] = p

        def comptr_setitem(self, index, value):
            # We override the __setitem__ method of the
            # POINTER(POINTER(interface)) type, so that the COM
            # reference count is managed correctly.
            #
            # This is so that we can implement COM methods that have to
            # return COM pointers more easily and consistent.  Instead of
            # using CopyComPointer in the method implementation, we can
            # simply do:
            #
            # def GetTypeInfo(self, this, ..., pptinfo):
            #     if not pptinfo: return E_POINTER
            #     pptinfo[0] = a_com_interface_pointer
            #     return S_OK
            if index != 0:
                raise IndexError("Invalid index %s, must be 0" % index)
            from _ctypes import CopyComPointer
            CopyComPointer(value, self)
        POINTER(p).__setitem__ = comptr_setitem

        return cls

    def __setattr__(self, name, value):
        if name == "_methods_":
            self._make_methods(value)
        elif name == "_disp_methods_":
            self._make_dispmethods(value)
        type.__setattr__(self, name, value)

    def _make_case_insensitive(self):
        # The __map_case__ dictionary maps lower case names to the
        # names in the original spelling to enable case insensitive
        # method and attribute access.
        try:
            self.__dict__["__map_case__"]
        except KeyError:
            d = {}
            d.update(getattr(self, "__map_case__", {}))
            self.__map_case__ = d

    def _make_dispmethods(self, methods):
        if self._case_insensitive_:
            self._make_case_insensitive()

        # create dispinterface methods and properties on the interface 'self'
        properties = {}
        for m in methods:
            what, name, idlflags, restype, argspec = m

            # argspec is a sequence of tuples, each tuple is:
            # ([paramflags], type, name)
            try:
                memid = [x for x in idlflags if isinstance(x, int)][0]
            except IndexError:
                raise TypeError, "no dispid found in idlflags"
            if what == "DISPPROPERTY": # DISPPROPERTY
                assert not argspec # XXX does not yet work for properties with parameters
                accessor = self._disp_property(memid, idlflags)
                setattr(self, name, accessor)
            elif what == "DISPMETHOD": # DISPMETHOD
                # argspec is a tuple of (idlflags, type, name[,
                # defval]) items.
                method = self._disp_method(memid, name, idlflags, restype, argspec)
## not in 2.3                method.__name__ = name
                if 'propget' in idlflags:
                    nargs = len(argspec)
                    properties.setdefault((name, nargs), [None, None])[0] = method
                elif 'propput' in idlflags:
                    nargs = len(argspec)-1
                    properties.setdefault((name, nargs), [None, None])[1] = method
                else:
                    setattr(self, name, method)
        for (name, nargs), methods in properties.items():
            if nargs:
                setattr(self, name, named_property(*methods))
            else:
                assert len(methods) <= 2
                setattr(self, name, property(*methods))

    # Some ideas, (not only) related to disp_methods:
    #
    # Should the functions/methods we create have restype and/or
    # argtypes attributes?

    def _disp_method(self, memid, name, idlflags, restype, argspec):
        if 'propget' in idlflags:
            def getfunc(obj, *args, **kw):
                return self.Invoke(obj, memid, _invkind=2, *args, **kw) # DISPATCH_PROPERTYGET
            return getfunc
        elif 'propput' in idlflags:
            def putfunc(obj, *args, **kw):
                return self.Invoke(obj, memid, _invkind=4, *args, **kw) # DISPATCH_PROPERTYPUT
            return putfunc
        # a first attempt to make use of the restype.  Still, support
        # for named arguments and default argument values should be
        # added.
        if hasattr(restype, "__com_interface__"):
            interface = restype.__com_interface__
            def func(s, *args, **kw):
                result = self.Invoke(s, memid, _invkind=1, *args, **kw)
                return result.QueryInterface(interface)
        else:
            def func(obj, *args, **kw):
                return self.Invoke(obj, memid, _invkind=1, *args, **kw) # DISPATCH_METHOD
        return func

    def _disp_property(self, memid, idlflags):
        # XXX doc string missing in property
        def _get(obj):
            return obj.Invoke(memid, _invkind=2) # DISPATCH_PROPERTYGET
        if "readonly" in idlflags:
            return property(_get)
        def _set(obj, value):
            return obj.Invoke(memid, value, _invkind=4) # DISPATCH_PROPERTYPUT
        return property(_get, _set)

    def __get_baseinterface_methodcount(self):
        "Return the number of com methods in the base interfaces"
        try:
            return sum([len(itf.__dict__["_methods_"])
                        for itf in self.mro()[1:-1]])
        except KeyError, (name,):
            if name == "_methods_":
                raise TypeError, "baseinterface '%s' has no _methods_" % itf.__name__
            raise

    def _make_methods(self, methods):
        if self._case_insensitive_:
            self._make_case_insensitive()

        # we insist on an _iid_ in THIS class!
        try:
            iid = self.__dict__["_iid_"]
        except KeyError:
            raise AttributeError, "this class must define an _iid_"
        else:
            iid = str(iid)
##            if iid in com_interface_registry:
##                # Warn when multiple interfaces are defined with identical iids.
##                # This would also trigger if we reload() a module that contains
##                # interface types, so suppress the warning in this case.
##                other = com_interface_registry[iid]
##                if self.__name__ != other.__name__ or self.__module__ != other.__module__:
##                    text = "Multiple interface defn: %s, %s" % \
##                           (self, other)
##                    warnings.warn(text, UserWarning)
            com_interface_registry[iid] = self
            del iid
        vtbl_offset = self.__get_baseinterface_methodcount()

        properties = {}

        # create private low level, and public high level methods
        for i, item in enumerate(methods):
            restype, name, argtypes, paramflags, idlflags, doc = item
            # the function prototype
            prototype = WINFUNCTYPE(restype, *argtypes)

            # a low level unbound method calling the com method.
            # attach it with a private name (__com_AddRef, for example),
            # so that custom method implementations can call it.

            # If the method returns a HRESULT, we pass the interface iid,
            # so that we can request error info for the interface.
            if restype == HRESULT:
##                print "%s.%s" % (self.__name__, name)
                raw_func = prototype(i + vtbl_offset, name, None, self._iid_)
                func = prototype(i + vtbl_offset, name, paramflags, self._iid_)
            else:
                raw_func = prototype(i + vtbl_offset, name, None, None)
                func = prototype(i + vtbl_offset, name, paramflags, None)
            setattr(self,
                    "_%s__com_%s" % (self.__name__, name),
                    new.instancemethod(raw_func, None, self))
            # 'func' is a high level function calling the COM method
            func.__doc__ = doc
            func.__name__ = name # for pyhelp
            # make it an unbound method.  Remember, 'self' is a type here.
            mth = new.instancemethod(func, None, self)

            # is it a property set or property get?
            is_prop = False

            # XXX Hm.  What, when paramflags is None?
            # Or does have '0' values?
            # Seems we loose then, at least for properties...

            # The following code assumes that the docstrings for
            # propget and propput are identical.
            if "propget" in idlflags:
                assert name.startswith("_get_")
                nargs = len([flags for flags in paramflags
                             if flags[0] & 7 in (0, 1)])
                # XXX or should we do this?
                # nargs = len([flags for flags in paramflags
                #             if (flags[0] & 1) or (flags[0] == 0)])
                propname = name[len("_get_"):]
                properties.setdefault((propname, doc, nargs), [None, None])[0] = func
                is_prop = True
            elif "propput" in idlflags:
                assert name.startswith("_set_")
                nargs = len([flags for flags in paramflags
                              if flags[0] & 7 in (0, 1)]) - 1
                propname = name[len("_set_"):]
                properties.setdefault((propname, doc, nargs), [None, None])[1] = func
                is_prop = True

            # We install the method in the class, except when it's a
            # property accessor.  And we make sure we don't overwrite
            # a property that's already present in the class.
            if not is_prop:
                if hasattr(self, name):
                    setattr(self, "_" + name, mth)
                else:
                    setattr(self, name, mth)

            # COM is case insensitive.
            #
            # For a method, this is the real name.  For a property,
            # this is the name WITHOUT the _set_ or _get_ prefix.
            if self._case_insensitive_:
                self.__map_case__[name.lower()] = name

        # create public properties / attribute accessors
        for (name, doc, nargs), methods in properties.items():
            if nargs == 0:
                prop = property(*methods + [None, doc])
            else:
                # Hm, must be a descriptor where the __get__ method
                # returns a bound object having __getitem__ and
                # __setitem__ methods.
                prop = named_property(*methods + [doc])
            # Again, we should not overwrite class attributes that are
            # already present.
            if hasattr(self, name):
                setattr(self, "_" + name, prop)
            else:
                setattr(self, name, prop)

            # COM is case insensitive
            if self._case_insensitive_:
                self.__map_case__[name.lower()] = name


################################################################
# helper classes for COM propget / propput
# Should they be implemented in C for speed?

class bound_named_property(object):
    def __init__(self, getter, setter, im_inst):
        self.im_inst = im_inst
        self.getter = getter
        self.setter = setter

    def __getitem__(self, index):
        if self.getter is None:
            raise TypeError("unsubscriptable object")
        return self.getter(self.im_inst, index)

    def __call__(self, *args):
        if self.getter is None:
            raise TypeError("object is nor callable")
        return self.getter(self.im_inst, *args)

    def __setitem__(self, index, value):
        if self.setter is None:
            raise TypeError("object does not support item assignment")
        self.setter(self.im_inst, index, value)

class named_property(object):
    def __init__(self, getter, setter, doc=None):
        self.getter = getter
        self.setter = setter
        self.doc = doc

    def __get__(self, im_inst, im_class=None):
        if im_inst is None:
            return self
        return bound_named_property(self.getter, self.setter, im_inst)

################################################################

class _compointer_meta(type(c_void_p), _cominterface_meta):
    "metaclass for COM interface pointer classes"
    # no functionality, but needed to avoid a metaclass conflict

class _compointer_base(c_void_p):
    "base class for COM interface pointer classes"
    __metaclass__ = _compointer_meta
    def __del__(self, _debug=logger.debug):
        "Release the COM refcount we own."
        if self:
            # comtypes calls CoUnititialize() when the atexit handlers
            # runs.  CoUninitialize() cleans up the COM objects that
            # are still alive. Python COM pointers may still be
            # present but we can no longer call Release() on them -
            # this may give a protection fault.  So we need the
            # _com_shutting_down flag.
            if not self.__metaclass__._com_shutting_down:
                _debug("Release %s", self)
                self.Release()

    def __cmp__(self, other):
        """Compare pointers to COM interfaces."""
        # COM identity rule
        #
        # XXX To compare COM interface pointers, should we
        # automatically QueryInterface for IUnknown on both items, and
        # compare the pointer values?
        if not isinstance(other, _compointer_base):
            return 1

        # get the value property of the c_void_p baseclass, this is the pointer value
        return cmp(super(_compointer_base, self).value, super(_compointer_base, other).value)

    def __hash__(self):
        """Return the hash value of the pointer."""
        # hash the pointer values
        return hash(super(_compointer_base, self).value)

    # override the .value property of c_void_p
    #
    # for symmetry with other ctypes types
    # XXX explain
    # XXX check if really needed
    def __get_value(self):
        return self
    value = property(__get_value, doc="""Return self.""")

    def __repr__(self):
        return "<%s object %x>" % (self.__class__.__name__, id(self))

################################################################

from ctypes import _SimpleCData

class BSTR(_SimpleCData):
    "The windows BSTR data type"
    _type_ = "X"
    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.value)

    def __ctypes_from_outparam__(self, _free=windll.oleaut32.SysFreeString):
        result = self.value
        _free(self)
        return result

    def __del__(self, _free=windll.oleaut32.SysFreeString):
        """If we own the memory, call SysFreeString to free it."""
        if not self._b_base_:
            _free(self)

    def from_param(cls, value):
        """Convert into a foreign function call parameter."""
        if isinstance(value, cls):
            return value
        # Although the builtin SimpleCData.from_param call does the
        # right thing, it doesn't ensure that SysFreeString is called
        # on destruction.
        return cls(value)
    from_param = classmethod(from_param)

################################################################
# IDL stuff

class helpstring(unicode):
    "Specifies the helpstring for a COM method or property."

class defaultvalue(object):
    "Specifies the default value for parameters marked optional."
    def __init__(self, value):
        self.value = value

class dispid(int):
    "Specifies the DISPID of a method or property."

# XXX STDMETHOD, COMMETHOD, DISPMETHOD, and DISPPROPERTY should return
# instances with methods, or at least accessors instead of tuple.

def STDMETHOD(restype, name, argtypes=()):
    "Specifies a COM method slot without idlflags"
    # restype, name, argtypes, paramflags, idlflags, docstring
    return restype, name, argtypes, None, (), None

def DISPMETHOD(idlflags, restype, name, *argspec):
    "Specifies a method of a dispinterface"
    return "DISPMETHOD", name, idlflags, restype, argspec

def DISPPROPERTY(idlflags, proptype, name):
    "Specifies a property of a dispinterface"
    return "DISPPROPERTY", name, idlflags, proptype, ()#, argspec

# COMMETHOD returns:
# restype, methodname, tuple(argtypes), tuple(paramflags), tuple(idlflags), helptext
#
# paramflags is a sequence of (flags (integer), paramname (string)
# tuple(idlflags) is for the method itself: (dispid, 'readonly')
#
# Example: (HRESULT, 'Width', (c_long,), (2, 'rhs'), (4, 'readonly'), None)

## sample generated code:
##    DISPPROPERTY([5, 'readonly'], OLE_YSIZE_HIMETRIC, 'Height'),
##    DISPMETHOD([6], None, 'Render',
##               ( [], c_int, 'hdc' ),
##               ( [], c_int, 'x' ),
##               ( [], c_int, 'y' ))

################################################################

_PARAMFLAGS = {
    "in": 1,
    "out": 2,
    "lcid": 4,
    "retval": 8,
    "optional": 16,
    }

def _encode_idl(names):
    # sum up all values found in _PARAMFLAGS, ignoring all others.
    return sum([_PARAMFLAGS.get(n, 0) for n in names])

_NOTHING = object()
def _unpack_argspec(idl, typ, name=None, defval=_NOTHING):
    return idl, typ, name, defval

# will be overwritten with the real VARIANT type when
# comtypes.automation is imported.

# XXX We don't want to make this module import
# comtypes.automation but we need VARIANT.  So
# comtypes.automation sets it from the outside into
# this module, when it is imported. Hack, hack.
_VARIANT_type_hack = None

def COMMETHOD(idlflags, restype, methodname, *argspec):
    """Specifies a COM method slot with idlflags.

    XXX should explain the sematics of the arguments.
    """
    paramflags = []
    argtypes = []

    # collect all helpstring instances
    # We should suppress docstrings when Python is started with -OO
    helptext = [t for t in idlflags if isinstance(t, helpstring)]
    # join them together(does this make sense?) and replace by None if empty.
    helptext = "".join(helptext) or None

    VARIANT = _VARIANT_type_hack # more pretty local name for our hack

    for item in argspec:
        idl, typ, argname, defval = _unpack_argspec(*item)
        pflags = _encode_idl(idl)
        if "optional" in idl:
            if defval is _NOTHING:
                if VARIANT and typ is VARIANT:
                    defval = VARIANT.missing
                elif VARIANT and typ is POINTER(VARIANT):
                    defval = pointer(VARIANT.missing)
                else:
##                    msg = "'optional' only allowed for VARIANT and VARIANT*, not for %s" \
##                                  % typ.__name__
##                    warnings.warn(msg, IDLWarning, stacklevel=2)
                    defval = typ()
        if defval is _NOTHING:
            paramflags.append((pflags, argname))
        else:
            paramflags.append((pflags, argname, defval))
        argtypes.append(typ)
    if "propget" in idlflags:
        methodname = "_get_%s" % methodname
    elif "propput" in idlflags:
        methodname = "_set_%s" % methodname
    return restype, methodname, tuple(argtypes), tuple(paramflags), tuple(idlflags), helptext

################################################################
# IUnknown, the root of all evil...

class IUnknown(object):
    """The most basic COM interface.

    Each subclasses of IUnknown must define these class attributes:

    _iid_ - a GUID instance defining the identifier of this interface

    _methods_ - a list of methods for this interface.

    The _methods_ list must in VTable order.  Methods are specified
    with STDMETHOD or COMMETHOD calls.
    """
    _case_insensitive_ = False
    __metaclass__ = _cominterface_meta
    _iid_ = GUID("{00000000-0000-0000-C000-000000000046}")

    _methods_ = [
        STDMETHOD(HRESULT, "QueryInterface",
                  [POINTER(GUID), POINTER(c_void_p)]),
        STDMETHOD(c_ulong, "AddRef"),
        STDMETHOD(c_ulong, "Release")
    ]

    def QueryInterface(self, interface, iid=None):
        "QueryInterface(interface) -> instance"
        p = POINTER(interface)()
        if iid is None:
            iid = interface._iid_
        self.__com_QueryInterface(byref(iid), byref(p))
        clsid = self.__dict__.get('__clsid')
        if clsid is not None:
            p.__dict__['__clsid'] = clsid
        return p

    # these are only so that they get a docstring.
    # XXX There should be other ways to install a docstring.
    def AddRef(self):
        "Increase the internal refcount by one and return it."
        return self.__com_AddRef()

    def Release(self):
        "Decrease the internal refcount by one and return it."
        return self.__com_Release()

    # should these methods be in a mixin class, which the metaclass
    # adds when it detects the Count, Item, and _NewEnum methods?
    def __len__(self):
        """Return the value of 'self.Count', or raise TypeError if no such property."""
        try:
            return self.Count
        except AttributeError:
            raise TypeError, "len() of unsized object"

    # calling a COM pointer calls its .Item property, if that is present.
    def __call__(self, *args, **kw):
        """Return the value of 'self.Item(*args, **kw)', or raise TypeError if no such method."""
        try:
            mth = self.Item
        except AttributeError:
            raise TypeError, "object is not callable"
        return mth(*args, **kw)

    # does this make sense? It seems that all standard typelibs I've
    # seen so far that support .Item also support ._NewEnum
    def __getitem__(self, index):
        """Return the result of 'self.Item(index)', or raise TypeError if no such method."""
        # Should we insist that the Item method has a dispid of DISPID_VALUE ( 0 )?
        try:
            mth = self.Item
        except AttributeError:
            raise TypeError, "unsubscriptable object"
        try:
            result = mth(index)
        except COMError, details:
            if details.hresult == -2147352565: # DISP_E_BADINDEX
                raise IndexError, "invalid index"
            else:
                raise
        # Hm, this doesn't look correct...
        if not result: # we got a NULL com pointer
            raise IndexError, "invalid index"
        # Hm, should we call __ctypes_from_outparam__ on the result?
        return result

    # Some magic to implement an __iter__ method.  Raises
    # AttributeError if no _NewEnum attribute is found in the class.
    # If _NewEnum is present, returns a callable that will return a
    # python iterator when called.  Thanks to Bengt Richter for the
    # idea.
    def __iter__(self):
        """Return self._NewEnum, or raise AttributeError if no such property."""
        try:
            enum = self._NewEnum
        except AttributeError:
            raise AttributeError("__iter__")
        if isinstance(enum, types.MethodType):
            # _NewEnum should be a propget property, with dispid -4.  See:
            # http://msdn.microsoft.com/library/en-us/automat/htm/chap2_2ws9.asp
            # http://msdn.microsoft.com/library/en-us/automat/htm/chap4_64j7.asp
            #
            # Sometimes, however, it is a method.
            enum = enum()
        if hasattr(enum, "Next"):
            enum.__parent = self
            return lambda: enum
        # _NewEnum returns an IUnknown pointer, QueryInterface() it to
        # IEnumVARIANT
        from comtypes.automation import IEnumVARIANT
        result = enum.QueryInterface(IEnumVARIANT)
        # Hm, is there a comtypes problem? Or are we using com incorrectly?
        result.__parent = self
        return lambda: result
    __iter__ = property(__iter__)

################################################################
def CoGetObject(displayname, interface):
    """Convert a displayname to a moniker, then bind and return the object
    identified by the moniker."""
    if interface is None:
        interface = IUnknown
    punk = POINTER(interface)()
    # Do we need a way to specify the BIND_OPTS parameter?
    _ole32.CoGetObject(unicode(displayname),
                       None,
                       byref(interface._iid_),
                       byref(punk))
    return punk

def CoCreateInstance(clsid, interface=None, clsctx=None, punkouter=None):
    """The basic windows api to create a COM class object and return a
    pointer to an interface.
    """
    if clsctx is None:
        clsctx = CLSCTX_SERVER
    if interface is None:
        interface = IUnknown
    p = POINTER(interface)()
    iid = interface._iid_
    _ole32.CoCreateInstance(byref(clsid), punkouter, clsctx, byref(iid), byref(p))
    return p

def GetActiveObject(clsid, interface=None):
    """Retrieves a pointer to a running object"""
    p = POINTER(IUnknown)()
    oledll.oleaut32.GetActiveObject(byref(clsid), None, byref(p))
    if interface is not None:
        p = p.QueryInterface(interface)
    return p

class MULTI_QI(Structure):
    _fields_ = [("pIID", POINTER(GUID)),
                ("pItf", POINTER(c_void_p)),
                ("hr", HRESULT)]

class _COAUTHIDENTITY(Structure):
    _fields_ = [
        ('User', POINTER(c_ushort)),
        ('UserLength', c_ulong),
        ('Domain', POINTER(c_ushort)),
        ('DomainLength', c_ulong),
        ('Password', POINTER(c_ushort)),
        ('PasswordLength', c_ulong),
        ('Flags', c_ulong),
    ]
COAUTHIDENTITY = _COAUTHIDENTITY

class _COAUTHINFO(Structure):
    _fields_ = [
        ('dwAuthnSvc', c_ulong),
        ('dwAuthzSvc', c_ulong),
        ('pwszServerPrincName', c_wchar_p),
        ('dwAuthnLevel', c_ulong),
        ('dwImpersonationLevel', c_ulong),
        ('pAuthIdentityData', POINTER(_COAUTHIDENTITY)),
        ('dwCapabilities', c_ulong),
    ]
COAUTHINFO = _COAUTHINFO

class _COSERVERINFO(Structure):
    _fields_ = [
        ('dwReserved1', c_ulong),
        ('pwszName', c_wchar_p),
        ('pAuthInfo', POINTER(_COAUTHINFO)),
        ('dwReserved2', c_ulong),
    ]
COSERVERINFO = _COSERVERINFO

class tagBIND_OPTS(Structure):
    _fields_ = [
        ('cbStruct', c_ulong),
        ('grfFlags', c_ulong),
        ('grfMode', c_ulong),
        ('dwTickCountDeadline', c_ulong)
    ]
# XXX Add __init__ which sets cbStruct?
BIND_OPTS = tagBIND_OPTS

class tagBIND_OPTS2(Structure):
    _fields_ = [
        ('cbStruct', c_ulong),
        ('grfFlags', c_ulong),
        ('grfMode', c_ulong),
        ('dwTickCountDeadline', c_ulong),
        ('dwTrackFlags', c_ulong),
        ('dwClassContext', c_ulong),
        ('locale', c_ulong),
        ('pServerInfo', POINTER(_COSERVERINFO)),
    ]
# XXX Add __init__ which sets cbStruct?
BINDOPTS2 = tagBIND_OPTS2

def CoCreateInstanceEx(clsid, interface=None,
                       clsctx=None,
                       machine=None):
    """The basic windows api to create a COM class object and return a
    pointer to an interface, possibly on another machine.
    """
    if clsctx is None:
        clsctx=CLSCTX_LOCAL_SERVER|CLSCTX_REMOTE_SERVER
    if machine:
        serverinfo = COSERVERINFO()
        serverinfo.pwszName = machine
        psi = byref(serverinfo)
    else:
        psi = None
    if interface is None:
        interface = IUnknown
    multiqi = MULTI_QI()
    multiqi.pIID = pointer(interface._iid_)
    _ole32.CoCreateInstanceEx(byref(clsid),
                             None,
                             clsctx,
                             psi,
                             1,
                             byref(multiqi))
    return cast(multiqi.pItf, POINTER(interface))

################################################################
from comtypes._comobject import COMObject

# What's a coclass?
# a POINTER to a coclass is allowed as parameter in a function declaration:
# http://msdn.microsoft.com/library/en-us/midl/midl/oleautomation.asp
class CoClass(COMObject):
    from comtypes._meta import _coclass_meta as __metaclass__

################################################################
