
from wnd.api.clipformats import *
from ctypes import c_char_p

#*************************************************************
# filename format ("FileName")
#*************************************************************
class filename(object):
	fmt= FORMATETC()
	fmt.cfFormat = RegisterClipboardFormat("FileName")
	fmt.dwAspect = DVASPECT_CONTENT
	fmt.lindex =  INDEX_ALL
	fmt.tymed = TYMED_HGLOBAL
		
	def __init__(self, path=None):
		self.stg= STGMEDIUM()
		self.stg.tymed = self.fmt.tymed
		if path:
			self._set_value(path)
				
	def _set_value(self, path):
		if path==None:
			self.stg.hGlobal= 0
		else:
			if self.stg.hGlobal:
				self.stg.hGlobal= 0
			self.stg.hGlobal = StringToHandle(path)
						
	def _get_value(self):
		if self.stg.hGlobal:
			kernel32.GlobalLock.restype= c_char_p
			value=  kernel32.GlobalLock(self.stg.hGlobal)
			kernel32.GlobalUnlock(self.stg.hGlobal)
			return value
	
	def Close(self): self.stg.hGlobal= 0
	def __eq__(self, other): return IsSameFormat(self, other) 
	def __repr__(self): return Repr(self)
				
	value= property(_get_value, _set_value)

#****************************************************************************
def test():
	
	testformat(filename, 'c:\\klmnopwqw.ddd')
		

if __name__=='__main__':
	test()

