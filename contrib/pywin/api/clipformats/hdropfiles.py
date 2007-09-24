
from wnd.api.clipformats import *
from ctypes import c_char_p, windll

shell32= windll.shell32

#*************************************************************
# dropped files format  CF_HDROP
#*************************************************************

class DROPFILES(Structure):
	_fields_ = [("pFiles", DWORD),
					("pt", POINT),
					("fNC", BOOL),
					("fWide", BOOL)]


def ValueToHandle(paths):
	szeof= sizeof(DROPFILES)
	
	df= DROPFILES(szeof)
	hMem= None
		
	## unicode version ##
	#isunicode= False
	#if isunicode:
	#	paths=  '%s\x00\x00' % '\x00'.join(paths)
	#	n= len(paths)*2
	#else:
	paths=  '%s\x00\x00' % '\x00'.join(paths)
	n= len(paths)
	hMem= kernel32.GlobalAlloc(GMEM_FIXED, szeof + n)
	if hMem:
		memmove(hMem, byref(df), szeof)
		memmove(hMem+szeof, paths, n)
	return hMem
		
def HandleToValue(hMem):
	out= []
	result= shell32.DragQueryFileA(hMem, 0xFFFFFFFF,  None, 0)
	p= create_string_buffer(260)
	for i in range(result):
		shell32.DragQueryFile(hMem, i,  p, 260)
		out.append(p.value)
	return out
	## seems to be quite some discussion about wether if zo pull in DropFinish 
	## for closing the mem handle or not. Noone knows and so do I.
   	
			
#*************************************************************
#*************************************************************
CF_HDROP           = 15

class hdropfiles(object):
	fmt= FORMATETC()
	fmt.cfFormat = CF_HDROP 
	fmt.dwAspect = DVASPECT_CONTENT
	fmt.lindex =  INDEX_ALL
	fmt.tymed = TYMED_HGLOBAL
		
	def __init__(self, data=None):
		self.stg= STGMEDIUM()
		self.stg.tymed = self.fmt.tymed
		if data:
			self._set_value(data)
				
	def _set_value(self, data):
		if data==None:
			self.stg.hGlobal= 0
		else:	
			if self.stg.hGlobal:
				self.stg.hGlobal= 0
			self.stg.hGlobal = ValueToHandle(data)
						
	def _get_value(self):
		if self.stg.hGlobal:
			return HandleToValue(self.stg.hGlobal)
	
	def Close(self): self.stg.hGlobal= 0
	def __eq__(self, other): return IsSameFormat(self, other) 
	def __repr__(self): return Repr(self)
				
	value= property(_get_value, _set_value)


#****************************************************************************
def test():
	
	testformat(hdropfiles, ['c:\\p', 'c:\\klmnopwqw','c:\\ssst'])
	
if __name__=='__main__':
	test()
