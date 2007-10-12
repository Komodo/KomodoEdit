
from wnd.api.clipformats import *
from ctypes import c_ulong

#*************************************************************
# performed drop effect ("Performed DropEffect")
#*************************************************************
class Ddropeffect_performed(object):
	fmt= FORMATETC()
	fmt.cfFormat = RegisterClipboardFormat("Performed DropEffect")
	fmt.dwAspect = DVASPECT_CONTENT
	fmt.lindex =  INDEX_ALL
	fmt.tymed = TYMED_HGLOBAL
		
	def __init__(self, value=None):
		self.stg= STGMEDIUM()
		self.stg.tymed = self.fmt.tymed
		if value:
			self._set_value(value)
				
	def _set_value(self, value):
		if value==None:
			self.stg.hGlobal= 0
		else:	
			if self.stg.hGlobal:
				self.stg.hGlobal= 0
			hMem = kernel32.GlobalAlloc(GMEM_FIXED, sizeof(c_ulong))
			memmove(hMem, buffer(c_ulong(value))[:], sizeof(c_ulong))
			self.stg.hGlobal= hMem
					
				
	def _get_value(self):
		if self.stg.hGlobal:
			kernel32.GlobalLock.restype= POINTER(c_ulong)
			value=  kernel32.GlobalLock(self.stg.hGlobal)
			kernel32.GlobalUnlock(self.stg.hGlobal)
			if value:
				return value[0]
	
	def Close(self): self.stg.hGlobal= 0
	def __eq__(self, other): return IsSameFormat(self, other) 
	def __repr__(self): return Repr(self)
				
	value= property(_get_value, _set_value)

#****************************************************************************
def test():
	
	DROPEFFECT_COPY	 = 1
	testformat(dropeffect_performed, DROPEFFECT_COPY)
		
if __name__=='__main__':
	test()





