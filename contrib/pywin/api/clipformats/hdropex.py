
from wnd.api.clipformats import *
from ctypes import c_char_p, windll

#*************************************************************
# extended dropped files format CF_HDROP
#*************************************************************

class DROPFILES(Structure):
	_fields_ = [("pFiles", DWORD),
					("pt", POINT),
					("fNC", BOOL),
					("fWide", BOOL)]


def ValueToHandle(x, y, fClientarea, isunicode, paths):
	szeof= sizeof(DROPFILES)
	
	df= DROPFILES(szeof, (x, y), fClientarea and [0][0] or 1, isunicode and 1 or 0)
	hMem= None
	if isunicode:
		paths=  '%s\x00\x00' % '\x00'.join(paths)
		n= len(paths)*2
	else:
		paths=  '%s\x00\x00' % '\x00'.join(paths)
		n= len(paths)
	hMem= kernel32.GlobalAlloc(GMEM_FIXED, szeof + n)
	if hMem:
		memmove(hMem, byref(df), szeof)
		memmove(hMem+szeof, paths, n)
	return hMem
		
		
def HandleToValue(hMem):
	n= kernel32.GlobalSize(hMem)
	szeof= sizeof(DROPFILES)
	if n >= szeof:
		pdf= POINTER(DROPFILES).from_address(int(hMem))	## int(hMem) ??
																						## ctypes loves to raise here..
																						## <int expected>
		df= pdf[0]
		paths= []
		if df.pFiles >= szeof:
			if df.fWide:
				p= create_unicode_buffer(n-szeof)
			else:
				p= create_string_buffer(n-szeof)
			memmove(p, addressof(df)+szeof, n-szeof)
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
		return (df.pt.x, df.pt.y, df.fNC, df.fWide, paths)	
		
#*************************************************************
#*************************************************************
CF_HDROP           = 15

class hdropex(object):
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
			self.stg.hGlobal = ValueToHandle(*data)
						
	def _get_value(self):
		if self.stg.hGlobal:
			return HandleToValue(self.stg.hGlobal)
	
	def Close(self): self.stg.hGlobal= 0
	def __eq__(self, other): return IsSameFormat(self, other) 
	def __repr__(self): return Repr(self)
				
	value= property(_get_value, _set_value)


#****************************************************************************
def test():
	testformat(hdropex,
			(12, 44, 1, 0, ['c:\\p', 'c:\\klmnopwqw','c:\\ssst']))
	
	
if __name__=='__main__':
	test()


	


