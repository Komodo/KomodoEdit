"""
Some shlwapi.dll path functions
Somewhat faster then os.path

NOT IMPLEMENTED
	
	PathCannonicalize
	PathCompactPathEx
	PathCommonPrefix
	PathFindOnPath
	PathGetCharType
	PathIsContentType
	PathIsFileSpec
	PathIsHTMLFile	## not supported on win9x 
	PathIsPrefix
	PathIsRelative
	PathIsSameRoot
	PathIsSystemFolder
	PathIsUNC
	PathIsUNCServer
	PathIsUNCServerShare
	PathMakePretty
	PathMakeSystemFolder
	PathParseIconLocation
	PathRelativePathTo
	PathRemoveBackslash
	PathRemoveBlanks
	PathSearchAndQualify
	PathSetDlgItemPath
	PathUnmakeSystemFolder
	
	
"""

from ctypes import (windll,
									create_string_buffer,
									string_at)

shlwapi= windll.shlwapi
gdi32= windll.gdi32
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

def AddBackslash(path):
	p= create_string_buffer(path, size=len(path)+1)
	shlwapi.PathAddBackslashA(p)
	return p.value
	
def AddExtension(path, ext):
	p= create_string_buffer(path, size=len(path)+len(ext))
	if not shlwapi.PathAddExtensionA(p, ext):
		raise RuntimeError, "could not add extension"
	return p.value

def Append(path1, path2):
	p= create_string_buffer(path1, size=len(path1)+len(path2)+1)
	if not shlwapi.PathAppendA(p, path2):
		raise RuntimeError, "could not append path"
	
def BuiltRoot(n):
	p= create_string_buffer(4)
	shlwapi.PathBuildRootA(p, n)
	return p.value

def Combine(path1, path2):
	p= create_string_buffer(len(path1)+len(path2)+1)
	if not shlwapi.PathCombineA(p, path1, path2):
		raise RuntimeError, "could not combine path"
	return p.value

def Compact(hDC, hFont, path, cx):
	if hFont:
		hOldFont= gdi32.SelectObject(hDC, hFont)
		if not hOldFont:
			raise RuntimeError, "could not select font"
	p= create_string_buffer(path)
	result= shlwapi.PathCompactPathA(hDC, p, cx)
	if hFont:
		gdi32.SelectObject(hDC, hOldFont)
	return p.value

def Exists(path):
	return bool(shlwapi.PathFileExistsA(path))

def GetExtension(path):
	return string_at(shlwapi.PathFindExtensionA(path))

def GetFileName(path):
	result= string_at(shlwapi.PathFindFileNameA(path))
	if result != path: return result

def Iter(path):
	yield path
	while True:
		path= shlwapi.PathFindNextComponentA(path)
		if not path: break
		path= string_at(path)
		if not path: 
			break
		yield path

def IterReverted(path):
	root= GetRoot(path)
	yield path
	for i in reversed(range(len(path))):
		if path[i] in ('\\/'):
			try:
				if '\\' in path[:i-1]:
					yield path[:i]
				elif '/' in path[:i-1]:
					yield path
				else:
					if root:
						yield root
					else:
						print path[:i]
			except:
				yield path[:i]
				break

def GetArgs(path):
	addr= shlwapi.PathGetArgsA(path)
	if addr: return string_at(addr)

def GetDriveNumber(path):
	result= shlwapi.PathGetDriveNumberA(path)
	if result > -1: return result 

def IsDir(path):
	return bool(shlwapi.PathIsDirectoryA(path))

def IsURL(path):
	return bool(shlwapi.PathIsURLA(path))

def MatchSpec(path, spec):
	return bool(shlwapi.PathMatchSpecA(path, spec))

def QuoteSpaces(path):
	p= create_string_buffer(path, len(path)+2)
	shlwapi.PathQuoteSpacesA(p)
	return p.value
	
def UnquoteSpaces(path):
	p= create_string_buffer(path)
	shlwapi.PathUnquoteSpacesA(p)
	return p.value

def RemoveArgs(path):
	p= create_string_buffer(path)
	shlwapi.PathRemoveArgsA(p)
	return p.value

def RemoveFileSpec(path):
	p= create_string_buffer(path)
	shlwapi.PathRemoveFileSpecA(p)
	return p.value

def RemoveExtension(path):
	p= create_string_buffer(path)
	shlwapi.PathRemoveExtensionA(p)
	return p.value

def ReplaceExtension(path, ext):
	p= create_string_buffer(path, size= len(path)+len(ext)+1)
	if shlwapi.PathRenameExtensionA(path, ext):
		return p.value 

def StripRoot(path):
	addr= shlwapi.PathSkipRootA(path)
	if addr: return string_at(addr)

def StripPath(path):
	addr= shlwapi.PathStripPathA(path)
	if addr: return string_at(addr)

def GetRoot(path):
	p= create_string_buffer(path)
	if shlwapi.PathStripToRootA(p):
		return p.value

def IsRoot(path):
	return  bool(shlwapi.PathIsRootA(path))

#def SetDlgItemPath(hwndParent, hwndControl, path):
#	idControl= user32.GetDlgCtrlID(hwndControl)
#	if not idControl: raise "could not retrieve dlg ID"
#	if not shlwapi.PathSetDlgItemPathA(hwndParent, idControl7, path):
#		raise "could not set path"
	

