
from wnd.wintypes import *
from ctypes.com import IUnknown, ole32
from ctypes.com.ole import IAdviseSink
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

DVASPECT_CONTENT    = 1 
DVASPECT_THUMBNAIL  = 2 
DVASPECT_ICON       = 4 
DVASPECT_DOCPRINT   = 8

# medium types
TYMED_HGLOBAL     = 1 
TYMED_FILE        = 2 
TYMED_ISTREAM     = 4 
TYMED_ISTORAGE    = 8 
TYMED_GDI         = 16 
TYMED_MFPICT      = 32 
TYMED_ENHMF       = 64 
TYMED_NULL        = 0 

INDEX_ALL  =  -1





class STGMEDIUM(Structure):
	_fields_ = [("tymed", DWORD),
		("_hGlobal", HANDLE),
		("pUnkForRelease", POINTER(IUnknown))]

	def _get_hGlobal(self):
		return self._hGlobal

	def _set_hGlobal(self, value, release=ole32.ReleaseStgMedium):
		if self._hGlobal:
			release(byref(self))
		self._hGlobal= value
		

	hGlobal= property(_get_hGlobal, _set_hGlobal)

	

class DVTARGETDEVICE(Structure):
    _fields_ = [("tdSize", DWORD),
                ("tdDriverNameOffset", WORD),
                ("tdDeviceNameOffset", WORD),
                ("tdPortNameOffset", WORD),
                ("tdExtDevmodeOffset", WORD),
                ("tdData", BYTE)]
    

class FORMATETC(Structure):
   	_fields_ = [("cfFormat", CLIPFORMAT),
                ("ptd", POINTER(DVTARGETDEVICE)),
                ("dwAspect", DWORD),
                ("lindex", LONG),
                ("tymed", DWORD)]

class STATDATA(Structure):
	_fields_ = [("formatetc", FORMATETC),
					("grfAdvf", DWORD),
					("pAdvSink", POINTER(IAdviseSink)),
					("dwConnection", DWORD)]