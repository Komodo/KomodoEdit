
"""
TODO
	- pIdl
		should be POINTER(POINTER(IDL)) as far as I know not POINTER(IDL) 
"""

from comtypes import IUnknown, STDMETHOD, HRESULT, GUID
from wnd.api.ole import ole32
from comtypes.persist import IPersist
IPersistFile = IPersist
# Why would anyone use IPersistFile to manage files in Python??? - EP [2007-08-28]
from comtypes import CLSCTX_INPROC_SERVER
from wnd.api.shell.wintypes import (LPSTR, 
																	c_int,
																	LOCALE,
																	POINTER,
																	byref,
																	sizeof,
																	WIN32_FIND_DATAA,
																	DWORD,
																	PIDL,
																	WORD,
																	HWND,
																	LOBYTE,
																	HIBYTE,
																	MAKEWORD,
																	MAKELONG,
																	create_string_buffer)

#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
CLSID_ShellLink = GUID("{00021401-0000-0000-C000-000000000046}")

class IShellLinkA(IUnknown):
    _iid_ = GUID("{000214EE-0000-0000-C000-000000000046}")
    _methods_ = IUnknown._methods_ + [
        STDMETHOD(HRESULT, "GetPath", (LPSTR, c_int, POINTER(WIN32_FIND_DATAA), DWORD)),
        STDMETHOD(HRESULT, "GetIDList", (POINTER(PIDL),)),
        STDMETHOD(HRESULT, "SetIDList", ( PIDL,)),
        STDMETHOD(HRESULT, "GetDescription", (LPSTR, c_int)),
        STDMETHOD(HRESULT, "SetDescription", (LPSTR,)),
        STDMETHOD(HRESULT, "GetWorkingDirectory", (LPSTR, c_int)),
        STDMETHOD(HRESULT, "SetWorkingDirectory", (LPSTR,)),
        STDMETHOD(HRESULT, "GetArguments", (LPSTR, c_int)),
        STDMETHOD(HRESULT, "SetArguments", (LPSTR,)),
        STDMETHOD(HRESULT, "GetHotkey", (POINTER(WORD),)),
        STDMETHOD(HRESULT, "SetHotkey", (WORD,)),
        STDMETHOD(HRESULT, "GetShowCmd", (POINTER(c_int),)),
        STDMETHOD(HRESULT, "SetShowCmd", (c_int,)),
        STDMETHOD(HRESULT, "GetIconLocation", (LPSTR, c_int, POINTER(c_int))),
        STDMETHOD(HRESULT, "SetIconLocation", (LPSTR, c_int)),
        STDMETHOD(HRESULT, "SetRelativePath", (LPSTR, DWORD)),
        STDMETHOD(HRESULT, "Resolve", (HWND, DWORD)),
        STDMETHOD(HRESULT, "SetPath", (LPSTR,))
        ]



SLGP_SHORTPATH      = 0x0001
SLGP_UNCPRIORITY    = 0x0002
SLGP_RAWPATH        = 0x0004

STGM_READ   =            0

#SLR_NO_UI           = 0x0001
#SLR_ANY_MATCH       = 0x0002
#SLR_UPDATE          = 0x0004
#SLR_NOUPDATE        = 0x0008
SLR_FLAGS= {'no_ui':1,'any_match':2,'update':4,'noupdate':8}

SHOWSTATES=['hidden','normal', 'minimized','maximized']	## enum

#**********************************************************************
#**********************************************************************

class ShellLink(object):
		
	def __init__(self):
		self.pIShellLink=  POINTER(IShellLinkA)()
		ole32.CoCreateInstance(byref(CLSID_ShellLink),
					   0,
					   CLSCTX_INPROC_SERVER,
					   byref(IShellLinkA._iid_),
					   byref(self.pIShellLink))
		self._buffer= create_string_buffer(260 +1)

	
	def SetArgs(self, args):
		self.pIShellLink.SetArguments(args)
	
	def GetArgs(self):
		self.pIShellLink.GetArguments(self._buffer, sizeof(self._buffer))
		return self._buffer.value
	
	
	def SetTarget(self, path):
		self.pIShellLink.SetPath(unicode(path))
	
	def GetTarget(self):
		fd= WIN32_FIND_DATAA()
		self.pIShellLink.GetPath(self._buffer, sizeof(self._buffer), byref(fd), SLGP_RAWPATH)
		return self._buffer.value
	
		
	def SetDescription(self, text):
		self.pIShellLink.SetDescription(text)
	
	def GetDescription(self):
		self.pIShellLink.GetDescription(self._buffer, sizeof(self._buffer))
		return self._buffer.value

		
	def SetHotkey(self, vk, *modkeys):
		if not vk:
			self.pIShellLink.SetHotkey(0)
		else:
			flags = {'shift':1, 'control':2, 'alt':4, 'extended':8}
			modkey = 0
			if modkeys:
				for i in modkeys:
					try: modkey |= flags[i]
					except: raise ValueError, "invalid modkey flag: %s" % i
			self.pIShellLink.SetHotkey(MAKEWORD(vk, modkey))
	
	def GetHotkey(self):
		dw= WORD()
		self.pIShellLink.GetHotkey(byref(dw))
		VK = LOBYTE(dw.value)
		modkey = HIBYTE(dw.value)
		out = [VK, ]
		if modkey:
			flags = {1:'shift', 2:'control',4:'alt',8:'extended'}
			for i in flags:
				if modkey & i:
					out.append(flags[i])
		return out

			
	def SetIcon(self, path, i):
		self.pIShellLink.SetIconLocation(path, i)
	
	def GetIcon(self):
		i= c_int()
		self.pIShellLink.GetIconLocation(self._buffer, sizeof(self._buffer), byref(i))
		return self._buffer.value, i.value

	
	def SetShowCommand(self, cmd):
		try:
			cmd= SHOWSTATES.index(cmd)
		except:
			raise ValueError, "invalid commad: %s" % cmd
		self.pIShellLink.SetShowCmd(cmd)
	
	def GetShowCommand(self):
		cmd= c_int()
		self.pIShellLink.GetShowCmd(byref(cmd))
		try:
			return SHOWSTATES[cmd.value]
		except: return 'unknown'
	
		
	def SetDir(self, path):
		self.pIShellLink.SetWorkingDirectory(path)
	
	def GetDir(self):
		self.pIShellLink.GetWorkingDirectory(self._buffer, sizeof(self._buffer))
		return self._buffer.value
	
		
	def Resolve(self, flag=None, hwnd=None, timeout=0):
		if flag:
			try:
				flag= SLR_FLAGS[flag]
			except:
				raise ValueError, "invalid flag: %s" % flag
			if flag==1:	# SLR_NO_UI
				flag= MAKELONG(flag, timeout)
		else:
			flag= 0
		self.pIShellLink.Resolve(hwnd and hwnd or 0, flag)
	
	def Save(self, path):
		pIPersistFile = POINTER(IPersistFile)()
		self.pIShellLink.QueryInterface(byref(IPersistFile._iid_), byref(pIPersistFile))
		pIPersistFile.Save(unicode(path), True)
		del pIPersistFile

	def IsDirty(self):
		pIPersistFile = POINTER(IPersistFile)()
		self.pIShellLink.QueryInterface(byref(IPersistFile._iid_), byref(pIPersistFile))
		result=  pIPersistFile.IsDirty()
		del pIPersistFile
		return not result
	
	def Load(self, path):
		pIPersistFile = POINTER(IPersistFile)()
		self.pIShellLink.QueryInterface(byref(IPersistFile._iid_), byref(pIPersistFile))
		pIPersistFile.Load(unicode(path, LOCALE), STGM_READ)
		del pIPersistFile

		
	def SetPidl(self, pIdl):
		self.pIShellLink.SetIDList(pIdl)
	
	def GetPidl(self):
		pIdl= PIDL()
		self.pIShellLink.GetIDList(byref(pIdl))
		return pIdl
	

	
if __name__=='__main__':
	
	import os, sys
	
	path= os.path.join(os.getcwd(), 'HelloWorld.lnk.lnk')
	target= os.path.join(sys.prefix, 'python.exe')

	lnk= ShellLink()
	print '-----------------------------'
	try: 
		lnk.Load(path)
		print 'IsDirty=', lnk.IsDirty(), '<loaded>'
	except: 
		print 'IsDirty=', lnk.IsDirty(), '<new>'
		
	
	lnk.SetTarget(target)
	lnk.SetArgs('-i -c "print \'Hello world from your shortcut!\'"')
	lnk.SetDir(sys.prefix)
	lnk.SetDescription('test description here')
	lnk.SetHotkey(33, 'alt')
	lnk.SetIcon(os.path.join(sys.prefix, 'py.ico'), 0)
	lnk.SetShowCommand('maximized')
	
	print 'pIdl=', lnk.GetPidl()
	print 'target=', lnk.GetTarget()
	print 'args=', lnk.GetArgs()
	print 'dir=', lnk.GetDir()
	print 'description=', lnk.GetDescription()
	print 'hotkey=', lnk.GetHotkey()
	print 'icon=', lnk.GetIcon()
	print 'show=', lnk.GetShowCommand()
	print 'IsDirty=', lnk.IsDirty()
	
	lnk.Save(path)
	print  'IsDirty=', lnk.IsDirty(), '<saved>'

	
