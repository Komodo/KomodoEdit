
from wnd.api.clipformats import *
from ctypes import c_char_p, windll

shell32= windll.shell32

#*************************************************************
# dropped files format  ("FileNameMap")
#*************************************************************

def ValueToHandle(paths):
	hMem= None
	## unicode version ##
	#isunicode= False
	#if isunicode:
	#	paths=  '%s\x00\x00' % '\x00'.join(paths)
	#	n= len(paths)*2
	#else:
	paths=  '%s\x00\x00' % '\x00'.join(paths)
	n= len(paths)
	hMem= kernel32.GlobalAlloc(GMEM_FIXED, n)
	if hMem:
		memmove(hMem, paths, n)
	return hMem
		
def HandleToValue(hMem):
	paths= []
	n= kernel32.GlobalSize(hMem)
	if n:
		p= create_string_buffer(n)
		mem= kernel32.GlobalLock(hMem)
		if mem:	
			memmove(p, mem, n)
			x= 0
			for n, i in enumerate(p):
				if i=='\x00':
					paths.append(p[x:n])
					x= n +1
					try:
						if p[n+1]=='\x00':
							break
					except: 
						paths= []
						break
	kernel32.GlobalUnlock(hMem)
	return paths
   	
			
#*************************************************************
#*************************************************************

class filenamemap(object):
	fmt= FORMATETC()
	fmt.cfFormat = RegisterClipboardFormat("FileNameMap")
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
	
	testformat(filenamemap, ['c:\\p', 'c:\\klmnopwqw','c:\\ssst'])
	
if __name__=='__main__':
	test()
