import logging

from ctypes import *
from comtypes.hresult import *

from comtypes import COMObject, IUnknown
from comtypes.typeinfo import LoadRegTypeLib, IProvideClassInfo, IProvideClassInfo2
from comtypes.automation import IEnumVARIANT

logger = logging.getLogger(__name__)

_oleaut32 = windll.oleaut32

__all__ = ["DualDispImplMixin", "VARIANTEnumerator"]

class DualDispImplMixin(object):
    # a mixin class to implement a dual dispatch interface.
    # Needs a _reg_typelib_ attribute in the subclass.
    #
    # Also implements IProvideClassInfo2.  XXX Where should this
    # really go?  And: XXX Can we load the typelib in the CoClass
    # baseclass?
    def __init__(self):
        super(DualDispImplMixin, self).__init__()
        tlib = LoadRegTypeLib(*self._reg_typelib_)

        # XXX This works only if the default dispatch interface is
        # also the default interface.  We should either search for the
        # first dispatch interface, or raise an error if the first is
        # no default disp interface.
        self.__dispatch_iid = self._com_interfaces_[0]._iid_
        self.__tinfo = tlib.GetTypeInfoOfGuid(self.__dispatch_iid)
        if hasattr(self, "_reg_clsid_"):
            self.__coclass_tinfo = tlib.GetTypeInfoOfGuid(self._reg_clsid_)

    def IDispatch_GetTypeInfoCount(self, this, pctinfo):
        if not pctinfo:
            return E_POINTER
        pctinfo[0] = 1
        return S_OK

    def IDispatch_GetTypeInfo(self, this, itinfo, lcid, pptinfo):
        if not pptinfo:
            return E_POINTER
        if itinfo != 0:
            return DISP_E_BADINDEX
        pptinfo[0] = self.__tinfo
        return S_OK

    def IDispatch_GetIDsOfNames(self, this, riid, rgszNames, cNames, lcid, rgDispId):
        return _oleaut32.DispGetIDsOfNames(self.__tinfo, rgszNames, cNames, rgDispId)

    def IDispatch_Invoke(self, this, dispIdMember, riid, lcid, wFlags,
                         pDispParams, pVarResult, pExcepInfo, puArgErr):
        impl = self._com_pointers_[self.__dispatch_iid]
        return _oleaut32.DispInvoke(impl, self.__tinfo,
                                    dispIdMember, wFlags, pDispParams,
                                    pVarResult, pExcepInfo, puArgErr)

    def IProvideClassInfo_GetClassInfo(self, this, ppTI):
        if not ppTI:
            return E_POINTER
        logger.debug("GetClassInfo called for %s", self._reg_clsid_)
        ppTI[0] = self.__coclass_tinfo
        return S_OK

    def IProvideClassInfo2_GetGUID(self, this, dwGuidKind, pGUID):
        if not pGUID:
            return E_POINTER
        GUIDKIND_DEFAULT_SOURCE_DISP_IID = 1
        if dwGuidKind != GUIDKIND_DEFAULT_SOURCE_DISP_IID:
            return E_INVALIDARG
        # XXX MSDN: The outgoing interface in question must be derived from IDispatch. 
        iid = self._outgoing_interfaces_[0]._iid_
        memmove(pGUID, byref(iid), sizeof(iid))
        logger.debug("IProvideClassInfo2::GetGUID -> %s", iid)
        return S_OK

################################################################

class VARIANTEnumerator(COMObject):
    _com_interfaces_ = [IEnumVARIANT]

    def __init__(self, itemtype, jobs):
        self.jobs = jobs # keep, so that we can restore our iterator (in Reset, and Clone).
        self.itemtype = itemtype
        self.item_interface = itemtype._com_interfaces_[0]
        self.seq = iter(self.jobs)
        super(VARIANTEnumerator, self).__init__()

    def Next(self, this, celt, rgVar, pCeltFetched):
        if not rgVar: return E_POINTER
        if not pCeltFetched: pCeltFetched = [None]
        pCeltFetched[0] = 0
        try:
            for index in range(celt):
                job = self.itemtype(self.seq.next())
                p = POINTER(self.item_interface)()
                job.IUnknown_QueryInterface(None,
                                            pointer(p._iid_),
                                            byref(p))
                rgVar[index].value = p
                pCeltFetched[0] += 1
        except StopIteration:
            pass
        if pCeltFetched[0] == celt:
            return S_OK
        return S_FALSE

    def Skip(self, this, celt):
        # skip some elements.
        try:
            for _ in range(celt):
                self.seq.next()
        except StopIteration:
            return S_FALSE
        return S_OK

    def Reset(self, this):
        self.seq = iter(self.jobs)
        return S_OK

    # Clone

################################################################

class COMCollection(COMObject):
    """Abstract base class which implements Count, Item, and _NewEnum."""
    def __init__(self, itemtype, collection):
        self.collection = collection
        self.itemtype = itemtype
        super(COMCollection, self).__init__()

    def _get_Item(self, this, pathname, pitem):
        if not pitem:
            return E_POINTER
        item = self.itemtype(pathname)
        return item.IUnknown_QueryInterface(None,
                                            pointer(pitem[0]._iid_),
                                            pitem)

    def _get_Count(self, this, pcount):
        if not pcount:
            return E_POINTER
        pcount[0] = len(self.collection)
        return S_OK

    def _get__NewEnum(self, this, penum):
        if not penum:
            return E_POINTER
        enum = VARIANTEnumerator(self.itemtype, self.collection)
        return enum.IUnknown_QueryInterface(None,
                                            pointer(IUnknown._iid_),
                                            penum)

