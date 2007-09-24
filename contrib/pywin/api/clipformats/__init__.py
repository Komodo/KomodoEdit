
"""helpers and data for clipboard and clipformats"""

import imp, os
from ctypes import windll
from wnd.api.ole.wintypes import *

kernel32= windll.kernel32
user32= windll.user32
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

_PATH= os.path.split(__file__)[0]

#**************************************************************************
#**************************************************************************

CF_ASPECT = {
DVASPECT_CONTENT:'content',      
DVASPECT_THUMBNAIL:'thumbnail',
DVASPECT_ICON:'icon',
DVASPECT_DOCPRINT:'docprint'    
}

CF_TYMED = {
TYMED_NULL:'null',
TYMED_HGLOBAL:'hglobal',
TYMED_FILE:'file',
TYMED_ISTREAM:'stream',
TYMED_ISTORAGE:'storage',
TYMED_GDI:'gdi',         
TYMED_MFPICT:'mfpict',
TYMED_ENHMF:'enhmf'   
}

CF_INDEX=  {
INDEX_ALL:'all',
}

RegisterClipboardFormat= user32.RegisterClipboardFormatA

CF_NAMES= ['null', 'text', 'bitmap', 'metafilepict', 'sylk', 'dif', 'tiff', 
						'oemtext', 'dib', 'palette', 'pendata', 'riff', 'wave', 
						'unicodetext', 'enhmetafile', 'hdrop', 'locale', 
						'dibv5',] 
FW_NAMES= {
						"html format": 'html',
						"shell idlist array": 'idlarray',
						"shell object offsets": 'objoffset',
						"net resource": 'netres',
						"filegroupdescriptor": 'filegroup',
						"filecontents": 'filecotents',
						"filename": 'filename',
						"printerfriendlyname": 'printername',
						"filenamemap": 'filenamemap',
						"uniformresourcelocator": 'url',
						"preferred dropeffect": 'dropeffect_prefered',
						"performed dropeffect": 'dropeffect_performed',
						"paste succeeded": 'pastesuceeded',
						"inshelldragloop": 'dragloop',
						}


def GetFormatName(format, nBuffer=56):
	if  format.fmt.cfFormat < 18: return CF_NAMES[format.fmt.cfFormat]
	p= create_string_buffer(nBuffer)
	user32.GetClipboardFormatNameA(format.fmt.cfFormat, p, nBuffer) 
	if p.value: return p.value

def GetFrameworkName(format):
	if  format.fmt.cfFormat < 18: return CF_NAMES[format.fmt.cfFormat]
	try:
		return FW_NAMES[GetFormatName(format).lower()]
	except: pass

def GetFormatNameN(nFormat, nBuffer=56):
	if  nFormat < 18: return CF_NAMES[nFormat]
	p= create_string_buffer(nBuffer)
	user32.GetClipboardFormatNameA(nFormat) 
	if p.value: return p.value

def GetFrameworkNameN(nFormat):
	if  nFormat < 18: return CF_NAMES[nFormat]
	try:
		return FW_NAMES[GetFormatNameN(nFormat).lower()]
	except: pass



## import format wrappers dynamically
class _cf(object):
	def __getattribute__(self, name):
		try:
			mod= globals()[name]
			return getattr(mod, name)
		except:
			try:
				mod= imp.load_source(name, os.path.join(_PATH, '%s.py' % name))
				globals()[name]= mod
				return getattr(mod, name)
			except IOError:
				raise ValueError, "no matching clipformat found: %s" % name
			except Exception, d:
				raise d
cf= _cf()



#*******************************************************************
# helper methods for clipformat wrapper classes
#*******************************************************************

def IsSameFormat(fmt1, fmt2):
	if fmt1.fmt.cfFormat== fmt2.fmt.cfFormat:
		if fmt1.fmt.dwAspect==fmt2.fmt.dwAspect:
			if (fmt1.fmt.tymed == fmt2.fmt.tymed == 0) or	\
				(fmt1.fmt.tymed & fmt2.fmt.tymed):
				return True
	return False


def Repr(format):
	name= GetFormatName(format)
	if name==None:
		name= 'unknown'
	
	if format.fmt.tymed== 0:
		tymed= CF_TYMED[0]
	else:
		out= []
		for value, medname in CF_TYMED.items():
			if format.fmt.tymed & value:
				out.append(medname)
		tymed= '/'.join(out)
	return "<wnd.cf.%s at %x {format=%s} {aspect=%s} {tymed=%s} {index=%s}>" % \
						(format.__class__.__name__,
						id(format),
						name,
						CF_ASPECT[format.fmt.dwAspect],
						tymed,
						format.fmt.lindex
						)


GMEM_FIXED = 0
## returns a chunk of global memory containing the passed string
## use GlobaFree to free it
def StringToHandle(text):
	if isinstance(text, str):
		n= len(text) +1
	elif isinstance(text, unicode):
		n= (len(text)*2) +2
	else:
		raise ValueError, "string or unicode expected found: %s" % type(text) 
	# no GlobalLock/unlock needed for GMEM_FIXED
	hMem = kernel32.GlobalAlloc(GMEM_FIXED, n)
	if hMem:
		if not memmove(hMem, text, n):
			raise MemoryError, "could not memmove text"
	else:
		raise MemoryError, "could alloc memory"
	return hMem


## test helper
def testformat(FMT, data):
	from wnd.api import clipboard
	from wnd.api.ole import dataobject
		
	print '** test clipformat %s*************************************' % FMT.__name__
	print 'set clipboard=%s' % repr(data)
	fmt= FMT(data)
	try:
		do= dataobject.DataObject(fmt)
		clipboard.SetDataObject(do)
		clipboard.Flush()
		fmt.value= None
		do2= clipboard.GetDataObject()
		if do2.HasFormat(fmt):
			print fmt.value
			do2.GetData(fmt)
		print 'get clipboard=%s' % repr(fmt.value)
		if fmt.value==data:
			print '<success>'
		else:
			print '<error>' 
	finally:
		fmt.Close()
	print

