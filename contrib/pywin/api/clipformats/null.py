
from wnd.api.clipformats import *

#**************************************************************************
# null format
#
# empty format or used to retrieve data or to setup a custom format
#
# return value of getattr('value') is allways the memory handle
# of the storage medium
#
# fmt is defined at compile time, too, to make the test for 
# IsSameFormat(NULL, other) work.
#************************************************************************
class null(object):
	fmt= FORMATETC()				## makes __eq__ work on the class and on the instance
														## cos the instance may change in format
	fmt.cfFormat = 0
	fmt.dwAspect = DVASPECT_CONTENT
	fmt.lindex =  INDEX_ALL
	fmt.tymed = TYMED_NULL	
	
	def __init__(self, fmt=None, stg=None):
		if fmt:
			self.fmt= fmt
		else:
			self.fmt= FORMATETC()
			self.fmt.cfFormat = 0
			self.fmt.dwAspect = DVASPECT_CONTENT
			self.fmt.lindex =  INDEX_ALL
			self.fmt.tymed = TYMED_NULL
		if stg:
			self.stg= stg
		else:
			self.stg= STGMEDIUM()
			self.stg.tymed = self.fmt.tymed
						
	def _set_value(self, hMem):
		if hMem==None:
			self.stg.hGlobal= 0
		else:	
			if self.stg.hGlobal:
				self.stg.hGlobal= 0
			self.stg.hGlobal = hMem
			
	def _get_value(self):
		if self.stg.hGlobal:
			return self.stg.hGlobal
	
	def Close(self): self.stg.hGlobal= 0
	def __eq__(self, other): return IsSameFormat(self, other) 
	def __repr__(self): return Repr(self)
				
	value= property(_get_value, _set_value)


