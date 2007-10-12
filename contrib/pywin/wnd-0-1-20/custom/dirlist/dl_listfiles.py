"""handles file listing and sorting for the view"""


from wnd.api import shell, wintime, winpath
from ctypes import (addressof,
									Structure,
									GetLastError,
									FormatError,
									byref,
									c_uint,
									c_int,
									c_long,
									c_char_p)
import thread, threading, time
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

class ListFiles(object):
	def __init__(self, mainframe):
		self.Mainframe= mainframe
		
		self.SendMessage= self.Mainframe.Listview.SendMessage
		self.LV= self.Mainframe.Listview
		self.SH= self.Mainframe.Shell
		self.SH_GETATTRS      =    self.Mainframe.Shell.GetAttributes
		self.SH_GETNAME          =      self.Mainframe.Shell.GetName
		self.SH_GETPARSENAME  = self.Mainframe.Shell.GetParseName
		self.SH_GETICONINDEX     =     self.Mainframe.Shell.GetIconIndex
		self.SH_GETDATA     =   self.Mainframe.Shell.GetData
		
			
		self.sorttype= 'type'
		self.sortdirection= 'ascending'
		self.listall= True
		self.filespec= None
		self.spec_match_folder= False		
		self.allow_navigate= True
		self.handle_errors= True

		
		self.event= threading.Event()
		self.event.set()
		self.stop_thread= False
				
		self.Reset()

		
	def SetFilespec(self, filespec, matchfolders=False):
		if filespec== '*': self.filespec= None
		else: self.filespec= filespec
		self.spec_match_folder= matchfolders
		
	
	def GetFilespec(self):
		if self.filespec==None:
			return '*', self.spec_match_folder
		return self.filespec, self.spec_match_folder
	
	
	def AllowNavigate(self, Bool, hideheader=True):
		if Bool:
			self.allow_navigate= True
			self.Mainframe.Header.Enable()
			self.Mainframe.Header.Show()
		else:
			self.allow_navigate= False
			self.Mainframe.Header.Disable()
			self.Mainframe.Header.Hide()
			
		self.Mainframe.Container.OffsetWindowSize(1, 0)
		self.Mainframe.Container.OffsetWindowSize(-1, 0)

		
	def IsNavigateAllowed(self):
		return self.allow_navigate
	
	def ShowFolders(self, Bool):
		self.listall= bool(Bool)
		self.Mainframe.Listview.DL_Refresh()
		
		
	def AreFoldersVisible(self):
		return self.listall
	
		
	
	
	def Stop(self):
		## stops the ListDetails thread

		if self.stop_thread==False:
			self.stop_thread= True
			if not self.event.isSet():
				self.event.wait(0.01)
												
	
	
	## dono what errors may come in here
	## ?? log them to get an overview ??
	def HandleError(self):
		
		if self.handle_errors:
			
			from wnd.api import msgbox
			errno= GetLastError()
			

			## path to be listed could not be found...
			## fallback on last valid folder if the view is in 'listall' mode
			if errno == ERROR_PATH_NOT_FOUND:
				lang= self.Mainframe.GetViewLang()
				path= self.Mainframe.Header.GetItemText(0)
				msg= '%s\n%s' % (path, FormatError(errno))
				msgbox.Msg(self.Mainframe.Hwnd, msg, lang.ERR_MSGBOX_TITLE, 'ok', 'systemmodal')

				if self.listall:
					pIdl= self.Mainframe.Shell.GetCwd()
					while True:
						shell.PidlGetParent(pIdl)

						if shell.ILIsZero(pIdl):
							shell.PidlFree(pIdl)
							pIdl= None
						
						try:
							self.Mainframe.Shell.SetCwd(pIdl)
							pIdl= None
							self.ListFiles()
							break
						except:
							pass
										
						## just in case
						if pIdl==None:	
							break
			
			## default
			else:
				self.Mainframe.Listview.Beep('asterisk')
		

					
					
	def ListDetails(self):
		## adds icons and details to items
		## TODO
		## could speed the thread up by using low level listview calls

		self.event.clear()
		
		try:
			pIdls= self.Mainframe.pIdls
			for i in self.LV:
									
				if self.stop_thread:
					break
				
				pIdl= pIdls[self.LV.GetItemLparam(i)]
				
				iIcon= self.SH_GETICONINDEX(pIdl)
				if iIcon== None:
					iIcon= 0
				self.LV.SetItemImage(i, 0, iIcon)
								
				## flag nolistdetails here
				
				data= self.SH_GETDATA(pIdl)
				if data:
					size, filetime= data
						
					if not self.SH.IsFolder(pIdl):
						self.LV.SetItemText(i, 1, self.Mainframe.FormatInt(size))
					self.LV.SetItemText(i, 2, self.Mainframe.FormatTime(filetime))
				
									
		except Exception, d: 
			## TODO
			## 30% of the time we exit the thread here via exception
			## havn't found out yet why ??
			## ++ breaking the loop via lock resulted in deadlocks 
			## every now and then
			## would somee more elaborate thread worker 
			## help please !!
			#raise Exception, d
			pass
			
		self.event.set()
		
		
	
	def Reset(self):
		self.root    =     []
		self.virtroot  =  []
		self.folders    =     []
		self.virtfolders    =    []
		self.files     =       []
	
	
	
		
	def ListFiles(self, old_dirname):
		"""lists files of the current shell folder.	"""
		
		#t1= time.clock()

				
		self.Mainframe.lastError= None
		self.LV.DL_SetCursor('wait')
		self.LV.SetRedraw(False)		
		
				
		if self.sorttype=='date':
			result= self.ListByDate()
		elif self.sorttype=='name':
			result= self.ListByName()
		elif self.sorttype=='size':
			result= self.ListBySize()
		elif self.sorttype=='type':
			result= self.ListByType()
		
		self.LV.Clear()
		if result:
			result= False
			try:
				self.SetItems()
				result= True
			except: pass
		else:
			self.Reset()
			self.LV.Clear()
		self.LV.DL_SetCursor('arrow')
	
		self.Reset()
		self.LV.SetRedraw(True)
		self.LV.DL_SetCursor('arrow')
		
		#if 'report' in self.LV.GetStyle():
		self.stop_thread= False
		thread.start_new_thread(self.ListDetails, ())
		
		if self.Mainframe.Header:
			self.Mainframe.Header.SetItemText(0, self.Mainframe.Shell.GetName())
				
		self.Mainframe.MsgHandler(0, "dirchanged", result,  			
							(old_dirname, self.Mainframe.Shell.GetParseName()))
		
		return result		
	
	

	def SetSortType(self, fSort='type', direction='ascending'):
		## adjusts sort options

		if fSort not in ('date', 'name', 'size', 'type'):
			raise ValueError, "invalid sort flag: %s" % fSort
		if direction not in ('ascending', 'descending'):
			raise ValueError, "invalid direction flag: %s" % direction
		self.sorttype= fSort
		self.sortdirection= direction
	
	
	def GetSortType(self):
		return self.sorttype, self.sortdirection
	
	
	def PidlGetData(self, pIdl, attrs):
		## return data required to list an item or None if it does not match
		## the current filespec

		name= self.SH_GETNAME(pIdl)	
				
		## return generic icon indexes here
		## the real icons will be aded threaded later
		if attrs & SFGAO_FOLDER:
			if self.filespec and self.spec_match_folder:
				if not winpath.MatchSpec(name, self.filespec):
					return
			
			iIcon= 3
			ovl= 0
		else:	
			if self.filespec:
				if not winpath.MatchSpec(name, self.filespec):
					return
			
			iIcon= 0
			if attrs & SFGAO_LINK:
				ovl = OVERLAY_LINK
			else:
				ovl= 0
				
		if attrs & SFGAO_SHARE:
			ovl |= OVERLAY_SHARE
		
		addr= addressof(pIdl)
		self.Mainframe.pIdls[addr]= pIdl
				
		return name, iIcon, ovl, addr
		
	
	
	def PidlGetSystemTime(self, pIdl):
			## returns tuple(time)
			
			data= self.SH_GETDATA(pIdl)
			if data:
				ft= data[1]
				st= wintime.FiletimeToSystemtime(ft)
				return st.wYear, st.wMonth, st.wDay, st.wHour, st.wMinute, st.wMilliseconds
		

	
	
	## --- sorting an listing -------------------------------
	
	def ListByDate(self):
						
		try:
						
			## check if we're in th efile system part of the namespace
			is_fs= winpath.GetRoot(self.SH.GetParseName()) 
									
			for i in self.SH:
				
												
				attrs= self.SH_GETATTRS(i, FLAGS)
										
				
				if attrs & SFGAO_FOLDER:
					if self.listall:
						data= self.PidlGetData(i, attrs)
						if not data:
							shell.PidlFree(i)
							continue
						
						name, iIcon, ovl, addr= data
						st= self.PidlGetSystemTime(i)
											
						if is_fs:
							self.folders.append((st, name.lower(), name, iIcon, ovl, addr))
						else:
						
							if attrs & SFGAO_FILESYSTEM:
								if attrs & SFGAO_FILESYSANCESTOR:
									self.root.append((st, self.SH_GETPARSENAME(i).lower(), name, iIcon, ovl, addr))
								else:
									self.folders.append((st, name.lower(), name, iIcon, ovl, addr))
							else:
								if attrs & SFGAO_FILESYSANCESTOR:
									self.virtroot.append((st, name.lower(), name, iIcon, ovl, addr))
								else:	
									self.virtfolders.append((st, name.lower(), name, iIcon, ovl, addr))
					
					else:
						shell.PidlFree(i)
				
				else:	# regular files
					data= self.PidlGetData(i, attrs)
					if not data:
						shell.PidlFree(i)
						continue
					name, iIcon, ovl, addr= data
										
					st= self.PidlGetSystemTime(i)
					self.files.append((st, name.lower(), name, iIcon, ovl, addr))
					
		except Exception, d:
			#raise Exception, d
			self.HandleError()
			self.Mainframe.SetLastError(Exception, d)
			return False
		return True		
	
	
	
	def ListByName(self):
						
		try:
						
			## check if we're in th efile system part of the namespace
			is_fs= winpath.GetRoot(self.SH.GetParseName()) 	
			
			for i in self.SH:
				
				attrs= self.SH_GETATTRS(i, FLAGS)
												
				if attrs & SFGAO_FOLDER:
					if self.listall:
						data= self.PidlGetData(i, attrs)
						if not data:
							shell.PidlFree(i)
							continue
						
						name, iIcon, ovl, addr= data
						
						if is_fs:
							self.folders.append((name.lower(), None, name, iIcon, ovl, addr))
						
						else:
							if attrs & SFGAO_FILESYSTEM:
								if attrs & SFGAO_FILESYSANCESTOR:
									self.root.append((self.SH_GETPARSENAME(i).lower(), None, name, iIcon, ovl, addr))
								else:
									self.folders.append((name.lower(), None, name, iIcon, ovl, addr))
							else:
								if attrs & SFGAO_FILESYSANCESTOR:
									self.virtroot.append((name.lower(), None, name, iIcon, ovl, addr))
								else:	
									self.virtfolders.append((name.lower(), None, name, iIcon, ovl, addr))
					
					else:
						shell.PidlFree(i)

				else:	# regular files
					data= self.PidlGetData(i, attrs)
					if not data:
						shell.PidlFree(i)
						continue
					
					name, iIcon, ovl, addr= data
					self.files.append((name.lower(), name, name, iIcon, ovl, addr))
					
		except Exception, d:
			#raise Exception, d
			self.HandleError()
			self.Mainframe.SetLastError(Exception, d)
			return False
		return True	

	
	def ListBySize(self):
					
		try:
			
			## check if we're in th efile system part of the namespace
			is_fs= winpath.GetRoot(self.SH.GetParseName()) 			
			
			for i in self.SH:
				
				attrs= self.SH_GETATTRS(i, FLAGS)
												
				if attrs & SFGAO_FOLDER:
					if self.listall:
						data= self.PidlGetData(i, attrs)
						if not data:
							shell.PidlFree(i)
							continue
						
						name, iIcon, ovl, addr= data
					
						if is_fs:
							self.folders.append((name.lower(), None, name, iIcon, ovl, addr))
						
						else:
							if attrs & SFGAO_FILESYSTEM:
								if attrs & SFGAO_FILESYSANCESTOR:
									self.root.append((self.SH_GETPARSENAME(i).lower(), None, name, iIcon, ovl, addr))
								else:
									self.folders.append((name.lower(), None, name, iIcon, ovl, addr))
							else:
								if attrs & SFGAO_FILESYSANCESTOR:
									self.virtroot.append((name.lower(), None, name, iIcon, ovl, addr))
								else:	
									self.virtfolders.append((name.lower(), None, name, iIcon, ovl, addr))
						
					else:
						shell.PidlFree(i)
				
				else:	# regular files
					data= self.PidlGetData(i, attrs)
					if not data:
						shell.PidlFree(i)
						continue
					
					sh_data= self.SH_GETDATA(i)
					if sh_data:
						size= sh_data[0]
					else:
						size= 0		## ??
										
					name, iIcon, ovl, addr= data
					self.files.append((size, name.lower(), name, iIcon, ovl, addr))
					
		except Exception, d:
			self.HandleError()
			self.Mainframe.SetLastError(Exception, d)
			return False
		return True			
			
		
	
	def ListByType(self):
		
		try:
						
			## check if we're in th efile system part of the namespace
			is_fs= winpath.GetRoot(self.SH.GetParseName()) 
						
			for i in self.SH:
				
				attrs= self.SH_GETATTRS(i, FLAGS)
												
				if attrs & SFGAO_FOLDER:
					if self.listall:
						data= self.PidlGetData(i, attrs)
						if not data:
							shell.PidlFree(i)
							continue
						
						name, iIcon, ovl, addr= self.PidlGetData(i, attrs)
						
						if is_fs:
							self.folders.append((name.lower(), None, name, iIcon, ovl, addr))
						
						else:
							if attrs & SFGAO_FILESYSTEM:
								if attrs & SFGAO_FILESYSANCESTOR:
									self.root.append((self.SH_GETPARSENAME(i).lower(), None, name, iIcon, ovl, addr))
								else:
									self.folders.append((name.lower(), None, name, iIcon, ovl, addr))
							else:
								if attrs & SFGAO_FILESYSANCESTOR:
									self.virtroot.append((name.lower(), None, name, iIcon, ovl, addr))
								else:	
									self.virtfolders.append((name.lower(), None, name, iIcon, ovl, addr))
								
					else:
						shell.PidlFree(i)
				
				else:	# regular files
					data= self.PidlGetData(i, attrs)
					if not data:
						shell.PidlFree(i)
						continue
					
					name, iIcon, ovl, addr= data
					
					x= name.rfind('.')
					if x > -1:
						tmp_name = name[:x].lower()
						tmp_ext= name[x+1:].lower()
					else:
						tmp_ext=  ''
						tmp_name = name
										
					self.files.append((tmp_ext, tmp_name, name, iIcon, ovl, addr))
					
		except Exception, d:
			self.HandleError()
			self.Mainframe.SetLastError(Exception, d)
			return False
		return True		
	
	

	
	def SetItems(self):
		# TODO
		# custom SetItems to allow the user to set the items to the view
		
		
		#LVM_INSERTITEM = 4103
		counter = 0
		hwnd= self.LV.Hwnd
		lvi= LV_ITEM()
		lvi.mask=  lvi.LVIF_TEXT | lvi.LVIF_IMAGE|lvi.LVIF_PARAM | lvi.LVIF_STATE
		pLvi= byref(lvi)
						
		if self.root:
			self.root.sort()
			if self.sortdirection=='descending': self.root.reverse()
			for foo, foo2, name, iIcon, ovl, lp in self.root:
				lvi.pszText= name
				lvi.iImage = iIcon
				lvi.state= ovl
				lvi.lParam= lp
				lvi.iItem= counter
				self.SendMessage(hwnd, 4103, counter,  pLvi)
				counter += 1
				
		if self.virtroot:
			self.virtroot.sort()
			if self.sortdirection=='descending': self.virtroot.reverse()
			for foo, foo2, name, iIcon, ovl, lp in self.virtroot:
				lvi.pszText= name
				lvi.iImage = iIcon
				lvi.state= ovl
				lvi.lParam= lp
				lvi.iItem= counter
				self.SendMessage(hwnd, 4103, counter,  pLvi)
				counter += 1
				
		if self.virtfolders:
			self.virtfolders.sort()
			if self.sortdirection=='descending': self.virtfolders.reverse()
			for foo, foo2, name, iIcon, ovl, lp in self.virtfolders:
				lvi.pszText= name
				lvi.iImage = iIcon
				lvi.state= ovl
				lvi.lParam= lp
				lvi.iItem= counter
				self.SendMessage(hwnd, 4103, counter,  pLvi)
				counter += 1
		
		if self.folders:
			self.folders.sort()
			if self.sortdirection=='descending': self.folders.reverse()
			for foo, foo2, name, iIcon, ovl, lp in self.folders:
				lvi.pszText= name
				lvi.iImage = iIcon
				lvi.state= ovl
				lvi.lParam= lp
				lvi.iItem= counter
				self.SendMessage(hwnd, 4103, counter, pLvi)
				counter += 1
		
		if self.files:
			self.files.sort()
			if self.sortdirection=='descending': self.files.reverse()
			for foo, foo2, name, iIcon, ovl, lp in self.files:
				lvi.pszText= name
				lvi.iImage = iIcon
				lvi.state= ovl
				lvi.lParam= lp
				lvi.iItem= counter
				self.SendMessage(hwnd, 4103, counter, pLvi)
				counter += 1
				
			
		

	
	def SortFiles(self):
		## sorts files either 'date', 'name', 'size', 'type'
		## 'ascending' or 'descending'

		pIdls= self.Mainframe.pIdls
		
			
		def sortfAsc(lp1, lp2, lp):
											
			pIdl1= pIdls[lp1]
			pIdl2= pIdls[lp2]

			a1= self.SH_GETATTRS(pIdl1, FLAGS_S)
			a2= self.SH_GETATTRS(pIdl2, FLAGS_S)

			isroot1= a1 &FLAGS_S==ROOT
			isroot2= a2 & FLAGS_S==ROOT
			result= cmp(isroot2, isroot1)
			if result: return result
			
			result= cmp(a2 & FLAGS_S==VROOT, a1 & FLAGS_S==VROOT)
			if result: return result
			
			result= cmp(a2 & FLAGS_S==VFOLDER, a1 & FLAGS_S==VFOLDER)
			if result: return result
			
			result= cmp(a2 & FLAGS_S==FOLDER, a1 & FLAGS_S==FOLDER)
			if result: return result
			
						
			if lp==SORT_DATE or lp==SORT_SIZE:
				data1= self.SH_GETDATA(pIdl1)
				data2= self.SH_GETDATA(pIdl2)
				if lp==SORT_DATE:
					if data1 and data2:
						return wintime.CompareFiletime(data1[1], data2[1])
				elif lp==SORT_SIZE:
					
					if data1 and data2:
						return cmp(data1[0], data2[0])
				if data1 and not data2: return 1
				if not data1 and data2: return -1
				return 0
			
			
			if isroot1:
				name1=  self.SH_GETPARSENAME(pIdl1).lower()
			else:
				name1=  self.SH_GETNAME(pIdl1).lower()
			if isroot2:
				name2=  self.SH_GETPARSENAME(pIdl2).lower()
			else:
				name2=  self.SH_GETNAME(pIdl2).lower()

						
			if lp==SORT_TYPE:
				x= name1.rfind('.')
				if x > -1:
					tmp_name1 = name1[:x].lower()
					tmp_ext1= name1[x+1:].lower()
				else:
					tmp_ext1=  ''
					tmp_name1 = name1
				y= name2.rfind('.')
				if y > -1:
					tmp_name2 = name2[:x].lower()
					tmp_ext2= name2[y+1:].lower()
				else:
					tmp_ext2=  ''
					tmp_name2 = name2
				result= cmp(tmp_ext1, tmp_ext2)
				if not result:
					result= cmp(tmp_name1, tmp_name2)
				return result
			
			## default
			return cmp(name1, name2)		
	
	
		
		def sortfDesc(lp1, lp2, lp):
											
			pIdl1= pIdls[lp1]
			pIdl2= pIdls[lp2]

			a1= self.SH_GETATTRS(pIdl1, FLAGS_S)
			a2= self.SH_GETATTRS(pIdl2, FLAGS_S)

			isroot1= a1 &FLAGS_S==ROOT
			isroot2= a2 & FLAGS_S==ROOT
			result= cmp(isroot2, isroot1)
			if result: return result
			
			result= cmp(a2 & FLAGS_S==VROOT, a1 & FLAGS_S==VROOT)
			if result: return result
			
			result= cmp(a2 & FLAGS_S==VFOLDER, a1 & FLAGS_S==VFOLDER)
			if result: return result
			
			result= cmp(a2 & FLAGS_S==FOLDER, a1 & FLAGS_S==FOLDER)
			if result: return result
			
						
			if lp==SORT_DATE or lp==SORT_SIZE:
				data1= self.SH_GETDATA(pIdl1)
				data2= self.SH_GETDATA(pIdl2)
				if lp==SORT_DATE:
					if data1 and data2:
						return wintime.CompareFiletime(data2[1], data1[1])
				elif lp==SORT_SIZE:
					
					if data2 and data1:
						return cmp(data2[0], data1[0])
				if data1 and not data2: return 1
				if not data1 and data2: return -1
				return 0
			
			
			if isroot1:
				name1=  self.SH_GETPARSENAME(pIdl1).lower()
			else:
				name1=  self.SH_GETNAME(pIdl1).lower()
			if isroot2:
				name2=  self.SH_GETPARSENAME(pIdl2).lower()
			else:
				name2=  self.SH_GETNAME(pIdl2).lower()

						
			if lp==SORT_TYPE:
				x= name1.rfind('.')
				if x > -1:
					tmp_name1 = name1[:x].lower()
					tmp_ext1= name1[x+1:].lower()
				else:
					tmp_ext1=  ''
					tmp_name1 = name1
				y= name2.rfind('.')
				if y > -1:
					tmp_name2 = name2[:x].lower()
					tmp_ext2= name2[y+1:].lower()
				else:
					tmp_ext2=  ''
					tmp_name2 = name2
				result= cmp(tmp_ext2, tmp_ext1)
				if not result:
					result= cmp(tmp_name2, tmp_name1)
				return result
			
			## default
			return cmp(name2, name1)		
		
		
		if self.sorttype=='name': fSort= SORT_NAME
		elif self.sorttype=='date': fSort= SORT_DATE
		elif self.sorttype=='size': fSort= SORT_SIZE
		elif self.sorttype=='type': fSort= SORT_TYPE		
		else: 
			self.sorttype= 'type'
			raise ValueError, "invalid sort flag: %s" % fSort
		
		
		self.LV.DL_SetCursor('wait')
		self.LV.SetRedraw(False)
		
		if self.sortdirection=='ascending':
			self.LV.SortCB(sortfAsc, fSort)
		elif self.sortdirection=='descending':
			self.LV.SortCB(sortfDesc, fSort)
		
		self.LV.DL_SetCursor('arrow')
		self.LV.SetRedraw(True)



#***************************************************************************

def  INDEXTOOVERLAYMASK(i): return i << 8

## undocumented indicees of ahred and link overlays in the system imagelist
## does not work for NT4, for NT4 you would have to add the overlay icons
## manually to the imagelist
ICO_SHARE= 1
ICO_LINK= 2
OVERLAY_SHARE=  INDEXTOOVERLAYMASK(ICO_SHARE)	 
OVERLAY_LINK=  INDEXTOOVERLAYMASK(ICO_LINK)


SFGAO_FOLDER        =     shell.SFGAO_FOLDER
SFGAO_FILESYSTEM     =     shell.SFGAO_FILESYSTEM
SFGAO_FILESYSANCESTOR   =       shell.SFGAO_FILESYSANCESTOR
SFGAO_SHARE       =     shell.SFGAO_SHARE
SFGAO_LINK   =    shell.SFGAO_LINK

SORT_NAME= 1
SORT_DATE= 2
SORT_SIZE= 3
SORT_TYPE= 4


## item flags for overlay images sorting and listing
FLAGS_O= SFGAO_LINK | SFGAO_SHARE
FLAGS_S     =      SFGAO_FOLDER | SFGAO_FILESYSTEM | SFGAO_FILESYSANCESTOR
FLAGS     =    FLAGS_O | FLAGS_S


FOLDER      =     SFGAO_FOLDER | SFGAO_FILESYSTEM
ROOT          =     FOLDER | SFGAO_FILESYSANCESTOR
VROOT         =     SFGAO_FOLDER | SFGAO_FILESYSANCESTOR
VFOLDER      =    SFGAO_FOLDER
FILE            =    0




class LV_ITEM(Structure):
	LVIF_TEXT              = 1
	LVIF_IMAGE             = 2
	LVIF_PARAM             = 4
	LVIF_STATE             = 8
	LVIF_INDENT            = 16
	LVIF_NORECOMPUTE       = 2048
	LVIS_FOCUSED         =   1
	LVIS_SELECTED        =   2
	_fields_ = [("mask", c_uint),
						("iItem", c_int),
						("iSubItem", c_int),
						("state", c_uint),
						("stateMask", c_uint),
						("pszText", c_char_p),	##
						("cchTextMax", c_int),
						("iImage", c_int),
						("lParam", c_long),
						("iIndent", c_int)]




ERROR_PATH_NOT_FOUND    =         3

#################################
##	- excludehidden
	##	- excludesystem
	##	- listspec
	##	- filesonly		## done
	##	- sortname
	##	- sortext			## done
	##	- sortsize
	##	- sortdate
	##	- ...
	#####################################

	