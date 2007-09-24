
from wnd.api.clipformats import *
from wnd.api.shell import Malloc, PidlGetSize, PIDL, ITEMIDLIST 

#*************************************************************
# idlist array "Shell IDList Array"
#*************************************************************
class CIDA(Structure):
	_fields_ = [("cidl", UINT),				# n-offsets in offset array
					("aoffset", UINT*1)]			# var length offset array
# the structure is followed by an array of IDLISTs, 1st the absolute of the folder, 
# then the relative of the items. aoffset is the offset of the next item from the
# beginning of the structure. 


def HandleToValue(hMem):
		
	if hMem:
		n= kernel32.GlobalSize(hMem)
		if n >= sizeof(CIDA):
			kernel32.GlobalLock.restype= POINTER(CIDA)
			pCida= kernel32.GlobalLock(hMem)
			if pCida:
				## get the offset array
				## cidl seems to be +1 -- aoffset[1], is not counted
				addr= addressof(pCida[0])
				offs= (UINT*(pCida[0].cidl+1)).from_address(addr +	\
																							sizeof(UINT))
				# copy ITEMIDLISTs from global mem to shell allocated mem
				out= []
				for i in offs:
					error= True
					if addr +i <= addr + n:
						il= ITEMIDLIST.from_address(int(addr +i))
						size= PidlGetSize(byref(il))
						pMem= Malloc.Alloc(size)
						if pMem:
							if memmove(pMem, byref(il), size):
								out.append(PIDL(ITEMIDLIST.from_address(pMem)))
								error= False
					if error:
						for i in out:
							shell.PidlFree(i)
							return None
									
				return out
					

def ValueToHandle(data):
	if data:
		## prep the CIDA struct and fill in the offset members
		## have to work with two arrays here
		cida= CIDA(len(data)-1)
		arrOffs= (UINT*(len(data)-1))()
		offs= sizeof(cida) + sizeof(arrOffs)
		for n, i in enumerate(data):
			if n==0:
				cida.aoffset[0]= offs
			else:
				arrOffs[n-1]= offs	# append later
			offs += PidlGetSize(i)
		
		hMem= kernel32.GlobalAlloc(GMEM_FIXED, offs)
		if hMem:
			## move the CIDA structure + array to global mem
			p= hMem
			memmove(hMem, byref(cida), sizeof(cida))
			p += sizeof(cida)
			memmove(p, byref(arrOffs), sizeof(arrOffs))
			p += sizeof(arrOffs)
						
			## move the pIdls to global mem
			n= PidlGetSize(data[0])
			memmove(p, data[0], n)
			p += n
			for n, i in enumerate(data[1:]):
				n= PidlGetSize(i)
				memmove(p, i, n)
				p += n
			return hMem
		return 0

#*************************************************************
#*************************************************************
class idlistarray(object):
	fmt= FORMATETC()
	fmt.cfFormat = RegisterClipboardFormat("Shell IDList Array")
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
	from wnd.api import shell
	from wnd.api import clipboard
	from wnd.api.ole import dataobject
		
	print '** test clipformatIDLISTARRAY*************************************' 
	
	## get some friendly pIdls
	## pass them to our format and set it to clipboard
	pIdls, paths= [], []
	sh= shell.ShellNamespace()
	sh.OpenSpecialFolder(shell.CLSIDL_DRIVES)
	pIdls.append(sh.GetCwd())
	paths.append(sh.GetParseName())
	for i in sh:
		pIdls.append(i)
		paths.append(sh.GetParseName(i))
	il=idlistarray(pIdls)
	for i in pIdls:
		shell.PidlFree(i)
	pIdls= []

	print 'set clipboard=%s' % paths[0]
	for i in paths[1:]:
		print '                         %s' % i
	
	do= dataobject.DataObject(il)
	clipboard.SetDataObject(do)
	clipboard.Flush()
	il.value= None

	## retrive the format from clipboard
	do2= clipboard.GetDataObject()
	if do2.HasFormat(il):
		do2.GetData(il)

		pIdls= il.value
		il.value= None
		paths2= []
		if pIdls:
			sh.SetCwd(pIdls[0])
			paths2.append(sh.GetParseName())
			for i in pIdls[1:]:
				paths2.append(sh.GetParseName(i))

			for i in pIdls:
				shell.PidlFree(i)
		
		print 'get clipboard=%s' % paths2[0]
		for i in paths2[1:]:
			print '                         %s' % i
	else:
		print 'get clipboard='
		
	if paths==paths2:
		print '<success>'
	else:
		print '<error>'
	print

	
if __name__=='__main__':
	test()
