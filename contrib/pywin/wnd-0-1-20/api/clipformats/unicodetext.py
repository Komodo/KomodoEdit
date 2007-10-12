
from wnd.api.clipformats import *
from ctypes import c_wchar_p

import locale
LOCALE= locale.getdefaultlocale()[1]

#*************************************************************
# unicode text format (CF_UBICODETEXT)
#*************************************************************
CF_UNICODETEXT     = 13

class unicodetext(object):
	fmt= FORMATETC()
	fmt.cfFormat =  CF_UNICODETEXT
	fmt.dwAspect = DVASPECT_CONTENT
	fmt.lindex =  INDEX_ALL
	fmt.tymed = TYMED_HGLOBAL

	def __init__(self, text=None):
		self.stg= STGMEDIUM()
		self.stg.tymed = self.fmt.tymed
		if text:
			self._set_value(text)
					
	def _set_value(self, text):
		if text==None:
			self.stg.hGlobal= 0
		else:	
			if self.stg.hGlobal:
				self.stg.hGlobal= 0
			self.stg.hGlobal = StringToHandle(text)
					
	def _get_value(self):
		if self.stg.hGlobal:
			kernel32.GlobalLock.restype= c_wchar_p
			value=  kernel32.GlobalLock(self.stg.hGlobal)
			kernel32.GlobalUnlock(self.stg.hGlobal)
			return value

	def Close(self): self.stg.hGlobal= 0
	def __eq__(self, other): return IsSameFormat(self, other) 
	def __repr__(self): return Repr(self)
	
	value= property(_get_value, _set_value)

 
 #****************************************************************************
def test():
	
	testformat(unicodetext, u'aaa\n bbb ccc\n ddd\n')
	

if __name__=='__main__':
	test()

