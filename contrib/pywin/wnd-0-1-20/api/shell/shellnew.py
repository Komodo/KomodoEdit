"""
TODO
	- Not tested and not optimised
	- documentation




"""
import os, wnd
from wnd import gdi
from wnd.api import shell
from wnd.res.icons import icons1
from wnd.controls import imagelist
from wnd.api import process
from wnd.wintypes import (MEASUREITEMSTRUCT, 
												DRAWITEMSTRUCT,
												user32,
												WNDPROC,
												shell32,
												windll, 
												DWORD, 
												create_string_buffer,
												byref,
												sizeof,
												c_ubyte,
												LOWORD,
												HIWORD,
												MAKELONG)
advapi= windll.advapi32
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

HKEY_CLASSES_ROOT        = 2147483648
REG_SZ             =        1
REG_BINARY       = 3 



def EnumKey(hKey):
	cchName= DWORD()
	p= create_string_buffer(260)
	i= 0
	while True:
		cchName.value= 260
		if advapi.RegEnumKeyExA(hKey, i, p, byref(cchName), None, None, None, None):
			break
		i += 1
		yield p.value


def OpenKey(hParent, key):
	hKey= DWORD()
	if not advapi.RegOpenKeyA(hParent, key, byref(hKey)):
		return hKey.value


def CloseKey(hKey):
	advapi.RegCloseKey(hKey)


def GetDefaultValue(hKey):
	cchValue= DWORD()
	if not advapi.RegQueryValueA(hKey, None, None, byref(cchValue)):
		p= create_string_buffer(cchValue.value)
		if not advapi.RegQueryValueA(hKey, None, p, byref(cchValue)):
			return p.value


def GetShellNewValue(hKey):
	nValues= DWORD()
	maxValueName= DWORD()
	pChars= DWORD()
	pType= DWORD()
	cchData= DWORD()
	
	if not advapi.RegQueryInfoKeyA(hKey, None, None, None, None, None, None,
	byref(nValues), byref(maxValueName), None, None, None):
		if nValues.value:
			p= create_string_buffer(maxValueName.value +1)
			for i in range(nValues.value):
				pChars.value= sizeof(p)
				advapi.RegEnumValueA(hKey, i, p, byref(pChars), None, byref(pType), None, None)
				name= p.value.lower()
				
				if name in ('data', 'nullfile', 'command', 'filename'):
										
					if not advapi.RegQueryValueExA(hKey, p.value, None, None, None, byref(cchData)):
						
						if name=='data':
							if pType.value==REG_BINARY:
								p2= (c_ubyte*cchData.value)()
								if not advapi.RegQueryValueExA(hKey, p.value, None, None, byref(p2), byref(cchData)):
									return [name, p2]

						elif name=='nullfile':
							if pType.value==REG_SZ:
								return [name, '']
						
						elif name=='filename':
							if pType.value==REG_SZ:
								p2= create_string_buffer(cchData.value)
								if not advapi.RegQueryValueExA(hKey, p.value, None, None, p2, byref(cchData)):
									if p2.value:
										return [name, p2.value.lower()]
						
						else: 
							if pType.value==REG_SZ:
								p2= create_string_buffer(cchData.value)
								if not advapi.RegQueryValueExA(hKey, p.value, None, None, p2, byref(cchData)):
									if p2.value:
										return [name, p2.value]





def GetShellNew():
	"""could not find any documentation on the 'shell new' menu
	this function will enumerate all available asociations for this menu
	
"""
	
	## get available templates for errorcheck
	sh= shell.ShellNamespace()
	tpl= []
	sh.OpenSpecialFolder(shell.CLSIDL_TEMPLATES)
	path_tpl= sh.GetParseName() 
	for i in sh:
		tpl.append(sh.GetName(i).lower())	
		shell.PidlFree(i)
	sh.Close()
		
	## enum all available file asociations
	lnk= None		## '.lnk' to avoid sorting keep it extra
	out= []
	for i in EnumKey(HKEY_CLASSES_ROOT):
		if i[0]=='.':
			i= i.lower()
			

			hKey= OpenKey(HKEY_CLASSES_ROOT, i)
			asoc= GetDefaultValue(hKey)
						
			if asoc:
				## get suggested filename
				hKey2= OpenKey(HKEY_CLASSES_ROOT, asoc)
				if hKey2:
					filename= GetDefaultValue(hKey2)
					CloseKey(hKey2)
				else:
					filename= None
						
				if filename:
					## check if key has subkey 'ShellNew'
					hKey2= OpenKey(hKey, 'shellnew')
					if not hKey2:
						## check if key has subkey 'asoc'
						hKey_tmp= OpenKey(hKey, asoc)
						if hKey_tmp:
							hKey2= OpenKey(hKey_tmp, 'shellnew')
							CloseKey(hKey_tmp)
					
					if hKey2:
						result= GetShellNewValue(hKey2)
						
						if result:
							if result[0]=='filename':
								if result[1] in tpl:
									result[1] = '%s\\%s' % (path_tpl, result[1])
									out.append([filename, i] + result)
							else:
								if i=='.lnk':
									lnk= [filename, i] + result
								else:
									out.append([filename, i] + result)
						CloseKey(hKey2)
				
			CloseKey(hKey)
	
	out.sort()
	if lnk: out.insert(0, lnk)
	
	## get folder asoc
	hKey= OpenKey(HKEY_CLASSES_ROOT, 'folder')
	if hKey:
		name= GetDefaultValue(hKey)
		if name:
			out.insert(0, [name, 'folder', 'folder', ''])
		CloseKey(hKey)
	
	return out



#******************************************************************************
#******************************************************************************

class ShellNewMenu(object):
	def __init__(self, idMin, idMax):
		self.idMin= idMin
		self.idMax= idMax
		self.idMaxUsed= idMin
		self.items= None
		self._pOldWndProc= 0
		self.hMenu= None
		self.charcodes= {}		## for WM_MENUCHAR ord(mnemonic) --> itempos

		self.textExtend= (0, 0)
		self._pWndproc= WNDPROC(self.HandleMessage)

		self.Imagelist= imagelist.SystemImagelist('small')
		
		
	def QueryShellNewMenu(self, Popup):
		
		dc= gdi.ClientDC(hwnd=0)
		font= dc.GetFont()
		self.textExtend= (0, 0)
		self.hMenu= Popup.handle
		self.charcodes= {}

		
		sepID= None
		#try:
		self.items= GetShellNew()
		if self.items:
		
			for n, i in enumerate(self.items):
				if self.idMin + n <= self.idMax:
					Popup.Item('', self.idMin + n, 'ownerdraw')
					if i[1]=='folder' or i[1]=='.lnk':
						if len(self.items) > n:
							sepID= self.idMin + n
							if i[0]:
								self.charcodes[ord(i[0][0].lower())]= n
					self.textExtend= max(self.textExtend, font.GetTextExtend(dc, i[0]))
			
			if sepID != None:
				Popup.InsertSeparator(sepID +1, 0)
			#except Exception, d:
			#	raise d
			#	return False
			
			self.textExtend= max(self.textExtend, (self.Imagelist.GetIconSize()[0], self.textExtend[1]))
			
			self.idMaxUsed= self.idMin + n
			dc.Close()
			font.Close()
			return True
	
	
	
	def IsMenuID(self, ID):
		if isinstance(ID, (int, long)):
			if ID >= self.idMin and ID <= self.idMaxUsed:
				return True
		return False
	
	
	def HandleMessage(self, hwnd, msg, wp, lp):
		## returns nonzero if the message was handled, zero otherwise
		
		if msg==43:		# WM_DRAWITEM
			if self.items:
				if wp==0:
					di= DRAWITEMSTRUCT.from_address(lp)
					if self.IsMenuID(di.itemID):
						dc= gdi.DCFromHandle(di.hDC)

						nItem= di.itemID- self.idMin
						text= self.items[nItem][0]
						fType= self.items[nItem][1]
						icoW, icoH= self.Imagelist.GetIconSize()
						
						## draw background
						dc.SetBkMode('transparent')
						if di.itemState & di.SELECTED:
							br= gdi.SysColorBrush('highlight')
							dc.SetTextColor(gdi.GetSysColor('highlighttext'))
						else:
							br= gdi.SysColorBrush('menu')
							dc.SetTextColor(gdi.GetSysColor('menutext'))
						br.FillRect(dc, di.rcItem)
						br.Close()
						
						
						## draw icons
						if fType=='folder':
							nIco= self.Imagelist.GetIconIndex('directory', 'smallicon')
							self.Imagelist.Draw(dc, nIco, di.rcItem.left, di.rcItem.top, 'transparent')
						elif fType=='.lnk':
							ico= gdi.IconFromFile('%s\\icons\\lnk.ico' % wnd.WND_RESPATH)
							ico.DrawEx(dc, di.rcItem.left, di.rcItem.top, icoW, icoH, 'normal')
							ico.Close()
						else:
							nIco= self.Imagelist.GetIconIndex('*%s' % fType, 'smallicon')
							self.Imagelist.Draw(dc, nIco, di.rcItem.left, di.rcItem.top, 'transparent')
						di.rcItem.left += icoW + (icoW/2)
						
						## draw text
						font= dc.GetFont()
						if fType=='folder' or fType=='.lnk':
							font.DrawText(dc, di.rcItem, '&%s' % text, 'singleline')
						else:
							font.DrawText(dc, di.rcItem, text, 'singleline')
						
						dc.Close()
						font.Close()
						
			return 1
		

		elif msg==44:	# WM_MEASUREITEN
			if self.items:
				if wp==0:
					mi= MEASUREITEMSTRUCT.from_address(lp)
					if self.IsMenuID(mi.itemID):
						mi.itemWidth, mi.itemHeight= self.textExtend
			return  1
									
		
		elif msg==288:	# WM_MENUCHAR
			
			if lp==self.hMenu:
				if LOWORD(wp) in self.charcodes:
					## executes the item (by position)
					return MAKELONG(self.charcodes[LOWORD(wp)], 2)	## MNC_EXECUTE = 2
			return 0	
				
		else:
			if self._pOldWndProc:
				return user32.CallWindowProcA(self._pOldWndProc, hwnd, msg, wp, lp)
			return 0
			
	
	
	def MakeUniqueFilename(self, path, name, ext='', isdir=False):
		if isdir:
			for i in xrange(99999):
				if i==0:
					newName= '%s\\%s' % (path, name)
				else:
					newName= '%s\\%s (%s)' % (path, name, i)
				if not os.path.isdir(newName):
					return  os.path.normpath(newName)
		else:
			for i in xrange(99999):
				if i==0:
					newName= '%s\\%s%s' % (path, name, ext)
				else:
					newName= '%s\\%s (%s)%s' % (path, name, i, ext)
				if not os.path.isfile(newName):
					return os.path.normpath(newName)
	
	
	
	def InvokeCommand(self, ID, path):
		if isinstance(ID, (int, long)):
			if ID >= self.idMin or ID <= self.idMaxUsed:
				data= self.items[ID- self.idMin]
				if data[2]=='folder':
					name= self.MakeUniqueFilename(path, 'New Folder', isdir=True)
					if name:
						try: os.mkdir(name)
						except: pass
				
				elif data[2]=='command':
					cmd= data[3]
					if '%2' in cmd:
						name= self.MakeUniqueFilename(path, data[0], ext=data[1], isdir=False)
						if name:
							cmd= cmd.replace('%2', name)
							cmd= cmd.replace('%1', path)
							
							tmp_cmd= cmd.lower()
							if 'newlinkhere' in tmp_cmd:
								open(name, 'w+').close()
								## ISSUE
								## AppWiz does not resolve icons for links
						else:
							return
					## have to run asynchron here (!!)
					process.Create(commandline=cmd, flag='asynchron')

							
				
				
				elif data[2]=='data':
					name= self.MakeUniqueFilename(path, data[0], ext=data[1], isdir=False)
					if name:
						fp= open(name, 'wb')
						try:
							fp.write(buffer(data[3])[:])
						finally:
							fp.close()
			
				elif data[2]=='nullfile':
					name= self.MakeUniqueFilename(path, 'New File', isdir=False, ext='.txt')
					if name:
						open(name, 'w+').close()
						
			
				elif data[2]=='filename':
										
					name= self.MakeUniqueFilename(path, data[0], isdir=False, ext=data[1])
					if name:
						if os.path.isfile(data[3]):
							fpOut= None
							fp= open(data[3], 'rb')
							try:
								fpOut= open(name, 'wb')
								fpOut.write(fp.read())
							finally:
								fp.close()
								if fpOut: fpOut.close()
						
						
		
	
	def SubclassParent(self, window):
		if not self._pOldWndProc:
			self._pOldWndProc = user32.SetWindowLongA(window.Hwnd, -4, self._pWndproc)
			if not self._pOldWndProc:
				raise RuntimeError, "could not subclass window"
		else:
			raise RuntimeError, "there is alreaddy a window subclassed"
		
	
	def RestoreParentProc(self, window):
		if self._pOldWndProc:
			user32.SetWindowLongA(window.Hwnd, -4, self._pOldWndProc)
			self._pOldWndProc= 0
		else:
			raise RuntimeError, "no proc found to restore"
	



## test
if __name__=='__main__':
	pass
	for i in GetShellNew()	:	
		print i		
		

					
	