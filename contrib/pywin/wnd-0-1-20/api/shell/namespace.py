"""
TODO
	- _GetName if STRRET_WSTR is returned, free it with Malloc
	- _GetName, check if shlwapi.StrRetToBufA is present in IE < 5
		but non functional	
	- errorckeck all allocated pIdls
	


"""


from wnd.api.shell.wintypes import *
from wnd.api.shell.shellicon import (IExtractIcon,
																	IShellIcon, 
																	SHGetCachedImageIndex
																	)
from wnd.api.shell.contextmenu import (IContextMenu,
																			IContextMenu2,
																			IContextMenu3,
																			GetContextMenuVersion)
from wnd.api.shell.functions import (PidlCopy, 
																	PidlJoin,
																	PidlSplit,
																	PidlGetParent,
																	PidlFree,
																	ILIsZero)
from wnd.api.shell.consts import *
		
#***************************************************
# TODO: 
#		some methods specially GetAttributesOf suport parsing
#				of PIDL arrays: implement

#		- the desktop PIDL is not allocated using Malloc. GetCwd might cause
#			some problems here in the long run
#			
#
# DONE:
#
#******************************************************************************

class ShellNamespace(object):
	""""
	This class seems to confuse mallocspy. Have to test on this.
	"""
	
	def __init__(self):
		
		self.pIShellFolder = POINTER(IShellFolder)()
		shell32.SHGetDesktopFolder(byref(self.pIShellFolder))
		self.pIdl=PIDL(ITEMIDLIST())
		self.ret = STRRET()
		self.cwDir=self.pIShellFolder, self.pIdl 
		# for faster access init IShellIcon
					
	
	def Close(self):
		pFolder, pIdl =  self.cwDir
		PidlFree(pIdl)
		del pFolder
		del self.pIShellFolder
		self.pIShellFolder = None	
		
	
	
	def IterItems(self, folders=True, nonfolders=True, hidden=True):
		flags= 0
		if folders:
			flags |= SHCONTF_FOLDERS
		if nonfolders:
			flags |= SHCONTF_NONFOLDERS
		if hidden:
			flags |= SHCONTF_INCLUDEHIDDEN
		enum =  POINTER(IEnumIDList)()
		self.cwDir[0].EnumObjects(0, flags, byref(enum))
		fetched = c_ulong()
		EnumNext=enum.Next
		while True:
			pIdl = PIDL()
			if EnumNext(1, byref(pIdl), byref(fetched)): break
			yield pIdl
	
	
	def __iter__(self):
		flags = SHCONTF_FOLDERS | SHCONTF_NONFOLDERS | SHCONTF_INCLUDEHIDDEN
		enum =  POINTER(IEnumIDList)()
		self.cwDir[0].EnumObjects(0, flags, byref(enum))
		fetched = c_ulong()
		EnumNext=enum.Next
		while True:
			pIdl = PIDL()
			if EnumNext(1, byref(pIdl), byref(fetched)): break
			yield pIdl
	
	def OpenFolder(self, path):
		path = unicode(path, LOCALE)
		eaten = c_ulong()
		attrs = c_ulong()
		pIdl = PIDL(ITEMIDLIST())
		self.pIShellFolder.ParseDisplayName(0, None, path, 
							byref(eaten), byref(pIdl), byref(attrs))
		return self.SetCwd(pIdl)
	
	def OpenSpecialFolder(self, CLSIDL):
		pIdl = PIDL(ITEMIDLIST()) 
		shell32.SHGetSpecialFolderLocation(0, CLSIDL, byref(pIdl))
		return self.SetCwd(pIdl)
	
	def DirUp(self):
		if self.cwDir[0] == self.pIShellFolder: return False
		newPidl= PidlCopy(self.cwDir[1])
		PidlGetParent(newPidl)
		return self.SetCwd(newPidl)

	def DirDown(self, pIdl):
		newPidl = PidlJoin(self.cwDir[1], pIdl)
		## leave free to the caller ??
		#PidlFree(pIdl)
		self.SetCwd(newPidl)
	
	def GetCwd(self):
		#if self.cwDir[0] == self.pIShellFolder: return self.cwDir[1]
		return PidlCopy(self.cwDir[1])
	
	def SetCwd(self, pIdl):
		# TODO: still pretty bugy here
		# Printer folder raises ACCESS DENIED error
		# on COMPointer_del_
			
		if pIdl== None or not pIdl:		# switch to desktop folder
			pIShellFolder, pIdl = self.pIShellFolder, self.pIdl
		elif pIdl[0].mkid.cb==0:		# desktop folder
			PidlFree(pIdl)
			pIShellFolder, pIdl = self.pIShellFolder, self.pIdl
		else:
			pIShellFolder = POINTER(IShellFolder)()
			self.pIShellFolder.BindToObject(pIdl, None, byref(IShellFolder._iid_), byref(pIShellFolder))
			pIShellFolder.AddRef()
			
		if  self.cwDir[0] != self.pIShellFolder:	# desktop folder
			self.cwDir[0].Release()
		
		PidlFree(self.cwDir[1])
		self.cwDir= pIShellFolder, pIdl
		
	
	def IsDesktopFolder(self):
		if self.cwDir[0]== self.pIShellFolder:
			return True
		return False
		
			
	#--------------------------------------------------------------------
	# special methods 

	def Compare(self, pIdl1, pIdl2, lp=0):
		result = self.cwDir[0].CompareIDs(lp, pIdl1, pIdl2)
		return c_short(result & 0xFFFF).value
	
	def CompareExt(self, pIdl1, pIdl2, lp=0):
		# Welcome to the bottleneck !
		# fighting for every milisecond here
		# when sorting windows\\system this is called 10.000 times and up
		
		pIShellFolder = self.cwDir[0]
				
		# check if one pIdl points to a root drive or folder 
		# SFGAO_FILESYSANCESTOR =  0x10000000
		# SFGAO_FOLDER      =    0x20000000
		isFolder1 = False
		attrs1 = c_ulong(0x10000000|0x20000000)
		pIShellFolder.GetAttributesOf(1, byref(pIdl1), byref(attrs1))
		attrs1 = attrs1.value
		attrs2 = c_ulong(0x10000000|0x20000000)
		pIShellFolder.GetAttributesOf(1, byref(pIdl2), byref(attrs2))
		attrs2 = attrs2.value
		# compare folder
		fGet=0
		cmpExtension = True
		if attrs1 & 0x20000000 and not attrs2 & 0x20000000:
			return -1
		elif not attrs1 & 0x20000000 and attrs2 & 0x20000000:
			return 1
		# both are folders, so check if they are drives
		elif attrs1 & 0x20000000 and attrs2 & 0x20000000:
			if attrs1 & 0x10000000 and not attrs2 & 0x10000000:
				return -1
			elif not attrs1 & 0x10000000 and attrs2 & 0x10000000:
				return 1
			elif attrs1 & 0x10000000 and attrs2 & 0x10000000:
				fGet = SHGDN_FORPARSING = 0x8000
			cmpExtension = False
				
		# no result yet  ...get both names
		name1= self._GetName(pIShellFolder, pIdl1, fGet).lower()
		name2= self._GetName(pIShellFolder, pIdl2, fGet).lower()
		if name1 == name2: 
			return 0
		
		if cmpExtension:		# ...compare files by extension
			n1 = name1.rfind('.')
			if n1 > -1: ext1 = name1[n1+1:]
			else:ext1 = ''
			n2 = name2.rfind('.')
			if n2 > -1: ext2 = name2[n2+1:]
			else:ext2 = ''
			if ext1 > ext2: 
				return 1
			elif ext1 < ext2: 
				return -1
					
		# ...no result yet, compair by name
		if name1 > name2: return 1
		elif name1 < name2: return -1
		return 0
		# done it...		
	
	
	def GetIconIndex(self, pIdl=None):
		## curious about future aproaches of how to get the icon index
		## most of the mess is caused by the pIdl=None parameter.
		## But then... dono if SHMapPIDLToSystemImageListIndex
		## is capable of doing the job up to SHGetCachedImageIndex.
				
		## simplest aproach first
		if pIdl:
			result= SHMapPIDLToSystemImageListIndex(self.cwDir[0], pIdl, None)
			if result != -1:
				return result
				
		# ... not found. Most icons indexes are retrieved like this, but does not work for links
		n = c_int()
		if not self.IsLink(pIdl):
			pIShellIcon = POINTER(IShellIcon)()
			try:
				self.pIShellFolder.QueryInterface(REFIID(IShellIcon._iid_),	byref(pIShellIcon))
				if pIdl:
					result = pIShellIcon.GetIconOf(pIdl, 0, byref(n))
				else:	
					result = pIShellIcon.GetIconOf(self.cwDir[1], 0, byref(n))
				del pIShellIcon
				if not result: return n.value
			except: pass
		
		# ...not found, try IEtractIcon.GetIconLocation
		pIExtractIcon = POINTER(IExtractIcon)()
		if pIdl:
			try:
				self.cwDir[0].GetUIObjectOf(0, 1, byref(pIdl), 
					REFIID(IExtractIcon._iid_), byref(c_uint()), byref(pIExtractIcon))
			except: return
		else:
			try:
				self.pIShellFolder.GetUIObjectOf(0, 1, byref(self.cwDir[1]), 
					REFIID(IExtractIcon._iid_), byref(c_uint()), byref(pIExtractIcon))
			except: return
		flags = c_uint()
		p = create_string_buffer(260 +1)	# MAX_PATH
		pIExtractIcon.GetIconLocation(0, addressof(p), sizeof(p), 
													byref(n), byref(flags))
		del pIExtractIcon
		## this nifty api returns the icon index by iconpath/index and adds it if its
		## not present in the system imagelist
		result=SHGetCachedImageIndex(p.value, n.value, 0)
		if result > -1: 
			return result
			
	
	
	
	def GetContextMenu(self, version, pIdl=None):
		"""Returns the IContextMenu pointer for a folder or file.
		TODO: version is currently not implemented
		"""
				
		if self.IsDesktopFolder():	# desktop has no context menu
			if pIdl:
				if ILIsZero(pIdl):
					return None
			else:
				return None
		if pIdl:
			pIShellFolder = self.cwDir[0]
		else:	
			pIShellFolder,pIdl=self.pIShellFolder,self.cwDir[1]
		try:
			Menu, version=  GetContextMenuVersion(pIShellFolder, pIdl, version)
			return Menu, version
		except: pass
		
		
		
	def GetDataObject(self, pIdl=None):
		if self.IsDesktopFolder():	# desktop has no context menu
			if pIdl:
				if ILIsZero(pIdl):
					return None
			else:
				return None
				
		from wnd.api.ole.dataobject import DataObjectPointer
		dataobj= DataObjectPointer()
		
		n = c_int()
		if pIdl:
			if isinstance(pIdl, Array):
				self.cwDir[0].GetUIObjectOf(0, len(pIdl), byref(pIdl[0]), 
					dataobj.refiid, byref(c_uint()), dataobj.ptr)
			else:
				self.cwDir[0].GetUIObjectOf(0, 1, byref(pIdl), 
					dataobj.refiid, byref(c_uint()), dataobj.ptr)
		else:
			self.pIShellFolder.GetUIObjectOf(0, 1, byref(self.cwDir[1]), 
				dataobj.refiid, byref(c_uint()), dataobj.ptr)
		return dataobj
		
	
	def GetDropTarget(self, pIdl=None):
		from wnd.api.ole.dragdrop import DropTargetPointer
		dropt= DropTargetPointer()
		n = c_int()
		try:
			if pIdl:
				self.cwDir[0].GetUIObjectOf(0, 1, byref(pIdl), 
						dropt.refiid, byref(c_uint()), dropt.ptr)
			else:
				self.pIShellFolder.GetUIObjectOf(0, 1, byref(self.cwDir[1]), 
					dropt.refiid, byref(c_uint()), dropt.ptr)
		
			return dropt
		except: pass
		
		
	
	#--------------------------------------------------------------------
	# pIdl methods

	def ParseDisplayName(self, path):
		path = unicode(path, LOCALE)
		eaten = c_ulong()
		#attrs = c_ulong()
		pIdl = PIDL()
		self.pIShellFolder.ParseDisplayName(0, None, path, 
							byref(eaten), byref(pIdl), None)
		return pIdl
	
	#-------------------------------------------------------------------------
	# all the attributes here
	try:
		# check if StrRetToBuf is defined
		StrRetToBuf
		def _GetName(self, pIShellFolder, pIdl, flag):
			pIShellFolder.GetDisplayNameOf(pIdl, flag, byref(self.ret))
			StrRetToBuf(byref(self.ret), pIdl, NAME_BUFFER, MAX_PATH + 1)
			return NAME_BUFFER.value
	except:
		def _GetName(self, pIShellFolder, pIdl, flag):
			pIShellFolder.GetDisplayNameOf(pIdl, flag, byref(self.ret))
			if self.ret.uType==0:					# STRRET_WSTR
				return self.ret._.pOleStr			# ?? free the string with
																	# malloc.Free did not work ??
			elif self.ret.uType==1:					# STRRET_OFFSET
				return string_at(addressof(pIdl[0]) + self.ret._.uOffset)
			elif self.ret.uType==2:					# STRRET_CSTR
				return self.ret._.cStr	
	
	
	def GetName(self, pIdl=None):
		if pIdl: return self._GetName(self.cwDir[0], pIdl, 0)
		return self._GetName(self.pIShellFolder, self.cwDir[1], 0)
	
	def GetParseName(self, pIdl=None):
		if pIdl: return self._GetName(self.cwDir[0], pIdl, SHGDN_FORPARSING)
		return self._GetName(self.pIShellFolder, self.cwDir[1], SHGDN_FORPARSING)
		
	def GetAddressBarName(self, pIdl=None):
		if pIdl: return self._GetName(self.cwDir[0], pIdl, SHGDN_FORADDRESSBAR)
		return self._GetName(self.pIShellFolder, self.cwDir[1], SHGDN_FORADDRESSBAR)
	
	
	def SetName(self, name, pIdl=None):
		if not pIdl:
			pIShellFolder,pIdl=self.pIShellFolder,self.cwDir[1]
		else:pIShellFolder = self.cwDir[0]
		SHGDN_INFOLDER          = 1
		pIShellFolder.SetNameOf(0, pIdl, c_wchar_p(name), SHGDN_INFOLDER, byref(pIdl))
		return pIdl

	
	
	def GetData(self, pIdl):
		# SHGDFIL_FINDDATA  =      1
		data= WIN32_FIND_DATAA()
		if shell32.SHGetDataFromIDListA(self.cwDir[0], pIdl, 1, byref(data), sizeof(WIN32_FIND_DATAA)):
			return None
		#MAXDWORD   =  0xffffffff  
		return ((data.nFileSizeHigh * 0xffffffff) + data.nFileSizeLow,
						data.ftLastWriteTime) 

	
	def GetAttributes(self, pIdl, attrs):
		
		if pIdl:
			attrs = c_ulong(attrs)
			if isinstance(pIdl, Array):
				self.cwDir[0].GetAttributesOf(len(pIdl), byref(pIdl[0]), byref(attrs))
			else:
				self.cwDir[0].GetAttributesOf(1, byref(pIdl), byref(attrs))
			return attrs.value

		else:
			## have to use this till I get XXXGetAttributes to work on the current directory  
			## pretty slow. 
			flag= 8|2048				# SHGFI_PIDL | SHGFI_ATTRIBUTES
			shfi= SHFILEINFO()
			if attrs:
				shfi.dwAttributes = attrs
				flag |= 131072		# SHGFI_ATTR_SPECIFIED
			result= shell32.SHGetFileInfo(self.cwDir[1], 0, byref(shfi), sizeof(SHFILEINFO), flag)
			if result:
				return shfi.dwAttributes
			raise RuntimeError, "could not retrieve attributes"
		
				
	def XXXGetAttributes(self, pIdl, attrs, nItems=1):
		## never got this to work reliably. So use SHGetFileInfo instead
		attrs = c_ulong(attrs)
		if pIdl:
			self.cwDir[0].GetAttributesOf(nItems, byref(pIdl), byref(attrs))
		else:
			if self.IsDesktopFolder():
				self.pIShellFolder.GetAttributesOf(nItems, byref(self.cwDir[1]), byref(attrs))
			else:
				## the messy and non working part, retrieving attrs for the current folder
				pIdl= None
				pIdl2= None
				pIdlFolder= None
				try:
					pIdl= self.GetCwd()
					pIdl2= PidlCopy(pIdl) 
					pIdlFolder= PidlSplit(pIdl2)
					self.DirUp()
					self.pIShellFolder.GetAttributesOf(nItems, byref(pIdlFolder), byref(attrs))
					self.SetCwd(pIdl)
					pIdl= None	 ## shell is taking care now
				finally:
					if pIdl: PidlFree(pIdl)
					if pIdl2: PidlFree(pIdl2)
					if pIdlFolder: PidlFree(pIdlFolder)
		return attrs.value
		
	
	def IsReadOnly(self, pIdl=None):
		"""Returns True if the item is readonly.
		Having some problems here. Returns allways False"""
		return bool(self.GetAttributes(pIdl, SFGAO_READONLY) & SFGAO_READONLY)
	
	def IsFolder(self, pIdl=None):
		return bool(self.GetAttributes(pIdl,SFGAO_FOLDER) & SFGAO_FOLDER)

	def IsFileSystem(self, pIdl=None):
		return bool(self.GetAttributes(pIdl, SFGAO_FILESYSTEM) & SFGAO_FILESYSTEM)
		
	def IsRemovable(self, pIdl=None):
		return bool(self.GetAttributes(pIdl, SFGAO_REMOVABLE) & SFGAO_REMOVABLE)
	
	def IsLink(self, pIdl=None):
		return bool(self.GetAttributes(pIdl,SFGAO_LINK) & SFGAO_LINK)

	def IsHidden(self, pIdl=None):
		return bool(self.GetAttributes(pIdl, SFGAO_HIDDEN) & SFGAO_HIDDEN)
		
	def IsShared(self, pIdl=None):
		return bool(self.GetAttributes(pIdl, SFGAO_SHARE) & SFGAO_SHARE)
	
	def IsDropTarget(self, pIdl=None):
		return bool(self.GetAttributes(pIdl, SFGAO_DROPTARGET) & SFGAO_DROPTARGET)
		
	def IsNonEnumerated(self, pIdl=None):
		return bool(self.GetAttributes(pIdl, SFGAO_NONENUMERATED) & SFGAO_NONENUMERATED)
		
	def IsBrowsable(self, pIdl=None):
		return bool(self.GetAttributes(pIdl, SFGAO_BROWSABLE) & SFGAO_BROWSABLE)

	def IsCompressed(self, pIdl=None):
		return bool(self.GetAttributes(pIdl, SFGAO_COMPRESSED) & SFGAO_COMPRESSED)
	
	def IsNewContent(self, pIdl=None):
		return bool(self.GetAttributes(pIdl, SFGAO_NEWCONTENT) & SFGAO_NEWCONTENT)

	def IsGhosted(self, pIdl=None):
		return bool(self.GetAttributes(pIdl, SFGAO_GHOSTED) & SFGAO_GHOSTED)

	def HasPropertySheet(self, pIdl=None):
		return bool(self.GetAttributes(pIdl, SFGAO_HASPROPSHEET) & SFGAO_HASPROPSHEET)
	
	def HasSubFolder(self, pIdl=None):
		return bool(self.GetAttributes(pIdl, SFGAO_HASSUBFOLDER)	& SFGAO_HASSUBFOLDER)
		
	def IsFileSystemAnchestor(self, pIdl=None):
		return bool(self.GetAttributes(pIdl, SFGAO_FILESYSANCESTOR) & SFGAO_FILESYSANCESTOR)
	
	def HasFileSystemSubFolder(self, pIdl=None):
		#warnings.warn("HasFileSystemSubFolder is deprecated, use  IsFileSystemAnchestor instead", DeprecationWarning, stacklevel=2)
		return bool(self.GetAttributes(pIdl, SFGAO_FILESYSANCESTOR) & SFGAO_FILESYSANCESTOR)
	
	def CanRename(self, pIdl=None):
		return bool(self.GetAttributes(pIdl, SFGAO_CANRENAME) & SFGAO_CANRENAME)
	
	def CanDelete(self, pIdl=None):
		return bool(self.GetAttributes(pIdl, SFGAO_CANDELETE) & SFGAO_CANDELETE )
	
	def CanCopy(self, pIdl=None):
		return bool(self.GetAttributes(pIdl, DROPEFFECT_COPY) & DROPEFFECT_COPY)
		
	def CanMove(self, pIdl=None):
		return bool(self.GetAttributes(pIdl, DROPEFFECT_MOVE) & DROPEFFECT_MOVE)

	def CanLink(self, pIdl=None):
		return bool(self.GetAttributes(pIdl, DROPEFFECT_LINK) & DROPEFFECT_LINK)
				
	
	def Validate(self, pIdl=None):
		attrs = c_ulong(SFGAO_VALIDATE)
		if pIdl:
			if isinstance(pIdl, Array):
				self.cwDir[0].GetAttributesOf(len(pIdl), byref(pIdl[0]), byref(attrs))
			else:
				self.cwDir[0].GetAttributesOf(1, byref(pIdl), byref(attrs))
		else:
			self.cwDir[0].GetAttributesOf(0, byref(self.cwDir[1]), byref(attrs))
		
			
	def PrintAttrs(self, pIdl=None):
		print
		print 'GetName: ', self.GetName(pIdl)
		print 'GetParseName: ', self.GetParseName(pIdl)
		print 'GetAddressBarName: ', self.GetAddressBarName(pIdl)
		print '        IsFileSystem: ', self.IsFileSystem(pIdl)
		print '        IsRemovable: ', self.IsRemovable(pIdl)
		print '        IsFolder: ', self.IsFolder(pIdl)
		print '        IsLink: ', self.IsLink(pIdl)
		print '        IsShared: ', self.IsShared(pIdl)
		print '        IsBrowsable: ', self.IsBrowsable(pIdl)
		print '        IsCompressed: ', self.IsCompressed(pIdl)
		print '        IsNewContent: ', self.IsNewContent(pIdl)
		print '        IsNonEnumerated: ', self.IsNonEnumerated(pIdl)
		print '        IsDropTarget: ', self.IsDropTarget(pIdl)
		print '        IsGhosted: ', self.IsGhosted(pIdl)
		print '        HasSubFolder: ', self.HasSubFolder(pIdl)
		print '        IsFileSystemAnchestor: ', self.IsFileSystemAnchestor(pIdl)
		print '        IsReadonly: ', self.IsReadOnly(pIdl)
		print '        IsHidden: ', self.IsHidden(pIdl)
		print '        CanRename: ', self.CanRename(pIdl)
		print '        CanDelete: ', self.CanDelete(pIdl)
		print '        CanCopy: ', self.CanCopy(pIdl)
		print '        CanMove: ', self.CanMove(pIdl)
		print '        CanLink: ', self.CanLink(pIdl)
		print '        HasPropertySheet: ', self.HasPropertySheet(pIdl)
		


