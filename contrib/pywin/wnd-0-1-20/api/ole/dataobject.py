
"""IDataObject and PyDataObject
Note: 
don't forgett to call OleInitialize before use. ;)
(I bet nobody's gonna read this.......)
"""

from ctypes.com import (ole32,
											GUID, 
											IUnknown,
											STDMETHOD, 
											HRESULT,
											COMObject,
											REFIID)

from wnd.api.ole.wintypes import *
from wnd.api.ole.enumformatetc import (SHCreateStdEnumFmtEtc,
																						IEnumFORMATETC,
																						FORMATETC)
from ctypes.com.ole import IAdviseSink
from wnd.api.ole.enumstatdata import IEnumSTATDATA
from wnd.api.clipformats import cf


TYMED_HGLOBAL     = 1 
DATADIR_GET = 1
DATADIR_SET = 2

# error codes
S_OK = 0
S_FALSE = 1
DV_E_FORMATETC = -2147221404
STG_E_MEDIUMFULL = 2147680368   
E_NOTIMPL    = -2147467263
OLE_E_ADVISENOTSUPPORTED = -2147221501    
DATA_E_FORMATETC   =     0x80040064L
DV_E_TYMED         =          0x80040069L

E_OUTOFMEMORY      =             0x8007000L
E_INVALIDARG         =            0x80070057L

E_UNEXPECTED                 =              0x8000FFFFL

GMEM_FIXED  =  0
#***************************************************
class IDataObject(IUnknown):
    _iid_ = GUID("{0000010E-0000-0000-C000-000000000046}")

IDataObject._methods_ = IUnknown._methods_ + [
    STDMETHOD(HRESULT, "GetData", POINTER(FORMATETC), POINTER(STGMEDIUM)),
    STDMETHOD(HRESULT, "GetDataHere", POINTER(FORMATETC), POINTER(STGMEDIUM)),
    STDMETHOD(HRESULT, "QueryGetData", POINTER(FORMATETC)),
    STDMETHOD(HRESULT, "GetCanonicalFormatEtc", POINTER(FORMATETC), POINTER(FORMATETC)),
    STDMETHOD(HRESULT, "SetData", POINTER(FORMATETC), POINTER(STGMEDIUM), BOOL),
    STDMETHOD(HRESULT, "EnumFormatEtc", DWORD, POINTER(POINTER(IEnumFORMATETC))),
    STDMETHOD(HRESULT, "DAdvise", POINTER(FORMATETC), DWORD, POINTER(IAdviseSink), POINTER(DWORD)),
    STDMETHOD(HRESULT, "DUnadvise", DWORD),
    STDMETHOD(HRESULT, "EnumDAdvise", POINTER(POINTER(IEnumSTATDATA)))]


class IDataAdviseHolder(IUnknown):
    _iid_ = GUID("{00000110-0000-0000-C000-000000000046}")

IDataAdviseHolder._methods_ = IUnknown._methods_ + [
	 STDMETHOD(HRESULT, "Advise", POINTER(IDataObject), POINTER(FORMATETC), DWORD, POINTER(IAdviseSink), POINTER(DWORD)),

	STDMETHOD(HRESULT, "Unadvise", DWORD),
	STDMETHOD(HRESULT, "EnumAdvise", POINTER(IEnumSTATDATA)),
	STDMETHOD(HRESULT, "SendOnDataChange", POINTER(IDataObject), DWORD, DWORD),
	 ]
       


class IDataObject2(IUnknown):
    _iid_ = GUID("{0000010E-0000-0000-C000-000000000046}")

IDataObject2._methods_ = IUnknown._methods_ + [
    STDMETHOD(HRESULT, "GetData", POINTER(FORMATETC), POINTER(STGMEDIUM)),
    STDMETHOD(HRESULT, "GetDataHere", POINTER(FORMATETC), POINTER(STGMEDIUM)),
    STDMETHOD(HRESULT, "QueryGetData", POINTER(FORMATETC)),
    STDMETHOD(HRESULT, "GetCanonicalFormatEtc", POINTER(FORMATETC), POINTER(FORMATETC)),
    STDMETHOD(HRESULT, "SetData", POINTER(FORMATETC), POINTER(STGMEDIUM), BOOL),
    STDMETHOD(HRESULT, "EnumFormatEtc", DWORD, POINTER(POINTER(IEnumFORMATETC))),
    STDMETHOD(HRESULT, "DAdvise", POINTER(FORMATETC), DWORD, POINTER(IAdviseSink), POINTER(DWORD)),
    STDMETHOD(HRESULT, "DUnadvise", DWORD),
    STDMETHOD(HRESULT, "EnumDAdvise", POINTER(POINTER(IEnumSTATDATA)))]


#**************************************************

class DataObjectFactory(object):
    def LockServer(self, arg, arg2):
		pass

#**************************************************
#**************************************************

class DataObjectImpl(COMObject):
	_com_interfaces_ = [IDataObject]
	_factory = DataObjectFactory()
	
	
	def __init__(self, *formats, **kwargs):
		COMObject.__init__(self)
		self.IDataObject = self._com_pointers_[0][1]
				
		self.formats= list(formats)		## list of cf.FORMATS
		self.allowset= list(kwargs.get('allowset', []))
		
		
	def _lookup_formatetc_set(self, pFormatetc):
		"""Helper method. 
		Returns the index of the requested FORMATEC type
		or -1 if none of our FORMATEC types matches the given
		FORMATEC."""
		if pFormatetc:
			for n, i in enumerate(self.allowset):
				if i.fmt.tymed & pFormatetc[0].tymed						 \
				and i.fmt.cfFormat == pFormatetc[0].cfFormat     \
				and i.fmt.dwAspect == pFormatetc[0].dwAspect:
					return n
		return -1		# error format not found
	
		
	def _lookup_formatetc(self, pFormatetc):
		"""Helper method. 
		Returns the index of the requested FORMATEC type
		or -1 if none of our FORMATEC types matches the given
		FORMATEC."""
		if pFormatetc:
			for n, i in enumerate(self.formats):
				if i.fmt.tymed & pFormatetc[0].tymed						 \
				and i.fmt.cfFormat == pFormatetc[0].cfFormat     \
				and i.fmt.dwAspect == pFormatetc[0].dwAspect:
					return n
		return -1		# error format not found
	
	#--------------------------------------------------------------------------
	# default DataObject methods

	def QueryGetData(self, this, pFormatetc):
		if pFormatetc:
			if self._lookup_formatetc(pFormatetc) != -1:
				return S_OK
		return DV_E_FORMATETC
			
				
	def GetData(self, this, pFormatetc, pStgmedium):
		# get the corrosponding format from our list
		# stuff the data into the supplied STGMEDIUM
		# pUnkForRelease dhould be NULL here, so the caller 
		# is responsible for freeing the memory handle
		if pFormatetc and pStgmedium:
		
		
			n = self._lookup_formatetc(pFormatetc)
			if n == -1:
				return DV_E_FORMATETC	# sorry format not supported
			
			format= self.formats[n]
			pStgmedium[0].tymed =format.stg.tymed
			pStgmedium[0].pUnkForRelease = format.stg.pUnkForRelease
			if format.fmt.tymed == TYMED_HGLOBAL:
				hMem= ole32.OleDuplicateData(format.stg.hGlobal, format.fmt.cfFormat, None)
				if hMem:
					pStgmedium[0].hGlobal = hMem
					return S_OK
				else:
					return STG_E_MEDIUMFULL
			else:
				## other then hGlobal (...)
				pass
		return DV_E_FORMATETC
		
	
	def EnumFormatEtc(self, this, direction, ppEnumFormatetc):
			## create a FORMATETC array on the fly from available formats 
			arr= None
			if direction == DATADIR_GET:
				if self.formats:
					arr= (FORMATETC*len(self.formats))()
					for n, i in enumerate(self.formats):
						arr[n]= i.fmt
			elif direction==DATADIR_SET:
				if self.allowset:
					arr= (FORMATETC*len(self.allowset))()
					for n, i in enumerate(self.allowset):
						arr[n]= i.fmt
			if arr:
				if not SHCreateStdEnumFmtEtc(len(arr), addressof(arr[0]), ppEnumFormatetc):
					return S_OK
			return E_NOTIMPL	
			
				
	## not tested
	def SetData(self, this, pFormatetc, pStgmedium, release):
		if self.allowset== None:	return E_NOTIMPL
		if not pFormatetc or not pStgmedium: return E_INVALIDARG
		if self._lookup_formatetc_set(pFormatetc) == -1: return DV_E_FORMATETC 

		n = self._lookup_formatetc(pFormatetc)
		if n == -1:
			## add format
			format= cf.null()
			memmove(byref(format.fmt), pFormatetc, sizeof(FORMATETC))
			format.stg.tymed= format.fmt.tymed
			self.formats.append(format)
		else:
			## replace format
			format= self.formats[n]
	
		if release:		## we own the medium
			format.stg.hGlobal= pStgmedium[0].hGlobal
			return S_OK
		else:				## copy the medium
			if pFormatetc[0].tymed == TYMED_HGLOBAL:
				if pStgmedium[0].hGlobal:
					format.stg.hGlobal= ole32.OleDuplicateData(pStgmedium[0].hGlobal, format.fmt.cfFormat, None)
					if not format.stg.hGlobal:
						## something went wrong
						return STG_E_MEDIUMFULL
				return S_OK
			else:
				## other then hGlobal (...)
				return DV_E_TYMED
				
		return E_UNEXPECTED
			
	
	# not tested implemented currently
	def GetDataHere(self, this, pFormatetc, pStgmedium):
		return DATA_E_FORMATETC
	def GetCanonicalFormatEtc(self, this, pFormatetc, pFormatetcout):
		pFormatetcout[0].ptd = 0 # Tutorial says we have to NULL it
		return E_NOTIMPL
	
	def DAdvise(self, this, pFormatetc, advf, pAdvisesink, connection):
		return OLE_E_ADVISENOTSUPPORTED
	def DUnAdvise(self, this, connection):
		return OLE_E_ADVISENOTSUPPORTED
	def EnumDAdvise(self, this, ppEnumadvise):
		return OLE_E_ADVISENOTSUPPORTED
	
	
	##
	def GetComPointer(self):
		return byref(self._com_pointers_[0][1])
	
	def Close(self):
		for i in self.formats: i.value= None
		for i in self.allowset: i.value= None
		self.formats= []
		self.allowset= []


	def GetComPointer(self):
		return byref(self._com_pointers_[0][1])

	

#************************************************************
#************************************************************


class DataObjectFromPointer(object):
	def __init__(self, pDataObject):
		self._DataObject= pDataObject

	def GetComPointer(self):
		return self._DataObject
		
	def __nonzero__(self):
		return bool(self._DataObject)
	
	def ListFormats(self, get=True):
		enum = POINTER(IEnumFORMATETC)()
		result= self._DataObject.EnumFormatEtc(get and DATADIR_GET or DATADIR_SET, byref(enum))
		if result:
			raise WinError(result)
			
		n = pointer(ULONG())
		enum.Reset()
		out= []
		while 1:
			fmtNull= cf.null()
			result = enum.Next(1, byref(fmtNull.fmt), n)
			if result: break
			out.append(fmtNull) 
		
		del enum
		return out
			
	def GetData(self, format):
		try:
			self._DataObject.GetData(byref(format.fmt), byref(format.stg))
			return True
		except: return False
				
	def HasFormat(self, format):
		try:
			self._DataObject.QueryGetData(byref(format.fmt))
			return True
		except: return False

	def CanSet(self, format):
		try:
			if formst in ListFormats(self, get=False):
				return True
		except: pass
		return False
	
	def SetData(self, format, release=True):
		try:
			self._DataObject.SetData(byref(format.fmt), byref(format.stg), release and 1 or 0)
			return True
		except: return False

#************************************************************
#************************************************************

class DataObjectPointer(DataObjectFromPointer):
	def __init__(self):
		self._DataObject= POINTER(IDataObject)()
		self.refiid= REFIID(IDataObject._iid_)
		self.ptr= byref(self._DataObject)
				
	
#************************************************************
#************************************************************

class DataObject(object):
	
	def __init__(self, *formats, **kwargs):
		self._DataObject= DataObjectImpl(*formats, **kwargs)
		
	def GetComPointer(self):
		return byref(self._DataObject._com_pointers_[0][1])

	def ListFormats(self, get=True):
		enum = POINTER(IEnumFORMATETC)()
		if  self._DataObject.EnumFormatEtc(0, get and DATADIR_GET or DATADIR_SET, byref(enum)):
			raise WinError(result)
		enum.AddRef()
		
		n = pointer(ULONG())
		enum.Reset()
		out= []
		while 1:
			fmtNull= cf.null()
			result = enum.Next(1, byref(fmtNull.fmt), n)
			if result: break
			out.append(fmtNull) 
		enum.Release()	
		return out
			
	def GetData(self, format):
		try:
			self._DataObject.GetData(0, pointer(format.fmt), pointer(format.stg))
			return True
		except: return False
				
	def HasFormat(self, format):
		try:
			self._DataObject.QueryGetData(0, pointer(format.fmt))
			return True
		except: return False

	def CanSet(self, format):
		return format in self.ListFormats(get=False)
	
	def SetData(self, format, release=True):
		try:
			self._DataObject.SetData(0, pointer(format.fmt), pointer(format.stg), release and 1 or 0)
			return True
		except: return False

	def Close(self):
		return self._DataObject.Close()






