"""listview for the dirlist"""


import os
from wnd.wintypes import (addressof,
												POINT,
												HIWORD,
												LOWORD)
from wnd import gdi
from wnd.api import shell, wintime, winpath
from wnd.api.shell import shelllink
from wnd.api import winpath
from wnd.controls import listview
from wnd.controls.imagelist import SystemImagelist

VK_BACK     = 8
VK_APPS     = 93
ICO_SHARE= 1
ICO_LINK= 2

#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::


class Listview(listview.Listview):
	def __init__(self, mainframe, parent, *styles):
		
		self.Mainframe= mainframe
		
		listview.Listview.__init__(self, parent, 0, 0, 0, 0, *styles)
				
		self.HandleKeyMessage(VK_APPS)
		self.HandleKeyMessage(VK_BACK)
		self.HandleMessage(self.Mainframe.SHN_MSG)
		#self.HandleMessage(self.Msg.WM_MOUSEMOVE)


		self.tippos= None		## trigger tooltips
		self.ID_TIMER1= self.NewTimerID()
		self.ID_TIMER2= self.NewTimerID()
		
		self.DL_SetImagelist('small')
		
		self.lastError= None
		
		lang= self.Mainframe.GetViewLang()
		self.Column(lang.COL_NAME)
		self.Column(lang.COL_SIZE)
		self.Column(lang.COL_MODIFIED)

	
	def SetLang(self, lang):
		self.SetColumnText(0, lang.COL_NAME)
		self.SetColumnText(1, lang.COL_SIZE)
		self.SetColumnText(2, lang.COL_MODIFIED)
	
	
	#---------------------------------------------------------------
	# message handler
	
	def onMSG(self, hwnd, msg, wp, lp):
		
		if msg==self.Mainframe.SHN_MSG:
				if self.Mainframe.SHNotify:
					return self.Mainframe.SHNotify.HandleMessage(hwnd, msg, wp, lp)
		
		elif msg==self.Msg.WM_MOUSEMOVE:
			if not self.HasMouseCapture():
				self.SetMouseCapture()
				try: self.KillTimer(self.ID_TIMER1)
				except: pass
				self.SetTimer(self.ID_TIMER1, 200)
				self.tippos= None
				#print 'the mouse has entered the window'
			else:
				
				pt=POINT(LOWORD(lp), HIWORD(lp))
				rc=self.GetClientRect()
				if not pt.InRect(rc):
					self.ReleaseMouseCapture()
					try: self.KillTimer(self.ID_TIMER1)
					except: pass
					self.Mainframe.Tooltip.HideTip()
					#print 'the mouse has left the window'
		
					
		#elif msg=="releasecapture":
		#	self.SetMouseCapture()
		
		elif msg=="timer":
			
			if wp==self.ID_TIMER2:
				## delayed update
				self.DL_ListFiles(self.Mainframe.Shell.GetCwd())
				self.KillTimer(self.ID_TIMER2)
				
			
			elif wp==self.ID_TIMER1:
				## display item and subitem tooltips if 
				## the item is not fully visible
								
								
				if self.tippos:
					
					pos=self.GetCursorPos()
					if self.tippos==pos:
						
						style= self.GetStyle()
						if 'icon' in style:
							## 'icon' listviews show their own tooltips
							return
						
						pt=POINT(*pos)
						if self.DL_PointInHeader(pt):
							## hitest over header returns item 1
							## sort it out here
							return
						
						result= self.ItemHittest(pt.x, pt.y)
												
						if result:
							pt.ScreenToClient(self.Hwnd)
							nItem= result[0]
							nSubItem= 0
							rc= None
							## get subitem the mouse is over
							if 'report' in style:
								nColumns= self.GetColumnCount()
								for i in range(nColumns):
									rc=self.GetItemRect(nItem, i)
									if i==0:
										if nColumns > 1:
											rc2=self.GetItemRect(nItem, 1)
											rc.right= rc2.left
									
									if pt.InRect(rc):
										nSubItem= i
										break
														
							## problem here:
							## subitem text is displayed with a small offset
							## and there is no way to find out the offsets size.
							## Its 4 pix to each side, independend of the font size
							## so maybe its hard coded, but anyway, 4 is just a wild 
							## guess here 
							rc=self.GetItemLabelRect(nItem, nSubItem)
							if nSubItem:
								rcW= rc.right-rc.left-3 - 8 
							else:
								rcW= rc.right-rc.left-3
							
							text= self.GetItemText(nItem, nSubItem)
							w= self.GetTextExtend(text)[0]
														
							if w >= rcW:
								rc.ClientToScreen(self.Hwnd)
								self.Mainframe.Tooltip.ShowTip(text, rc.left, rc.top)
							
					else:
						self.Mainframe.Tooltip.HideTip()
					self.tippos=None
				else:	
					self.tippos=self.GetCursorPos()
					
		
		
		
		elif msg=='itemchanged':
			self.Mainframe.MsgHandler(hwnd, "itemchanged", 
								wp, 
								(self.StateToString(lp[0]), self.StateToString(lp[1])))
		
		elif msg in ('lmbdouble', 'return'):
			if self.Mainframe.SHContextMenu:
				self.DL_OnReturn(self.Hwnd, self.onMSG)
			else:
				self.Mainframe.MsgHandler(hwnd, "command", self.GetSelectedItem(), 0)
		
		elif msg=='key':
			if wp== VK_BACK:
				self.DL_DirUp()
			elif wp==VK_APPS:
				self.DL_TriggerContextMenu(keyb=True)
		
		elif msg=='setfocus':
			self.Mainframe.Header.DL_HilightHeader(hilight=True, focus=False)
			self.Mainframe.MsgHandler(hwnd, "setfocus", 0, 0)
		
		elif msg=='killfocus':
			self.Mainframe.Header.DL_HilightHeader(hilight=False, focus=False)
			self.Mainframe.MsgHandler(hwnd, "killfocus", 0, 0)

		
		elif msg=='rmbup':
			self.DL_TriggerContextMenu(keyb=False)
		
		elif msg=='endlabeledit':
			return self.DL_OnLabelEdit(hwnd, msg, wp, lp)
		
		elif msg in ('begindrag', 'beginrdrag'):
			if self.Mainframe.DragDrop:
				return self.Mainframe.DragDrop.onDrag(hwnd, msg, wp, lp)
		
		elif msg=='destroy':
			self.Mainframe.Close()
	
		
	
	
	
	
	
	## ?? kick out
	def DL_Update(self):
		## updates the view delayed. Use in SHNotify to filter out
		## multiple updates
		try: self.KillTimer(self.ID_TIMER2)
		except: pass
		self.SetTimer(self.ID_TIMER2, 100)
	
	
	def DL_PointInHeader(self, point):
		## checks if the specified point is within the header control
		## (screen coordinates)
		if 'report' in self.GetStyle():
			hd= self.GetHeaderControl()
			rc= hd.GetWindowRect()
			return point.InRect(rc) 
		return False		

		
	def DL_IsSmallIcon(self):
		return self.Imagelist.GetIconSize()[0] !=gdi.GetSystemMetric('cxicon')
		
	
	def DL_SetImagelist(self, size='small'):
		self.Imagelist= SystemImagelist(size)
		self.SetImagelistSmall(self.Imagelist)
		self.SetImagelistNormal(self.Imagelist)
	
	#----------------------------------------------------------------
	# helper methods

	def DL_SetCursor(self, name):
		cur= gdi.SystemCursor(name)
		cur.Set()
		cur.Close()
	
	def DL_GetPidlAbs(self, nItem):
		lp= self.GetItemLparam(nItem)
		if lp:
			pIdlRel= shell.PIDL.from_address(lp)
			if pIdlRel:
				pIdlRoot= self.Mainframe.Shell.GetCwd()
				pIdl= shell.PidlJoin(pIdlRoot, pIdlRel)
				shell.PidlFree(pIdlRoot)
				if pIdl:
					return pIdl
				else:
					PidlFree(pIdl)
		return shell.PIDL()
	
	
	def DL_GetPidlRel(self, iItem):
		lp= self.GetItemLparam(iItem)
		return self.Mainframe.pIdls[lp]
				
	
	def DL_GetPidlsSelected(self):
		## returns an array of pIdls of the currently selected items or None
		n= self.GetSelectedCount()
		if n:
			arr= (shell.PIDL*n)()
			for n, i in enumerate(self.IterSelected()):
				lp=self.GetItemLparam(i)
				arr[n]= shell.PIDL.from_address(lp)
			return arr
	
	#-----------------------------------------------------------------
	# all the methods for shell notify and drag-drop
	
		
	

	def DL_GetItemIndex(self, pIdl):
		## ## returns the index of an item given its (rel) pIdl or None
		
		result= None		
		name= self.Mainframe.Shell.GetName(pIdl)
		islnk= self.Mainframe.Shell.IsLink(pIdl)
		start= -1
			
		## liks and files or folders can be listed under the same name
		while True:
			n= self.FindExact(name, start)
			
			if n==None: break
			start= n
			ovl= bool(self.GetItemOverlayImage(n) & ICO_LINK)
			if ovl == islnk:
				result= n
				break
		
		return result
		
	
	def DL_HasItem(self, pIdl):
		## checks if the item pIdl (rel) is alreaddy listed or not
		return self.DL_GetItemIndex(pIdl) != None
		
	
	
	def DL_AddPidl(self, pIdl):
		
		## TODO:
		## icons for links get not retrieved 
		
		
		pIdl_tmp= shell.PidlGetLast(pIdl)
		if not self.DL_HasItem(pIdl_tmp):
			
			nNewItem= None
			pIdlRel= None
			
			## REMARKS
			## dono if its a bug but the pIdl passed does not always contain valid information
			## and 'Validate' never worked. So reparse the folder to find the new item...
			## this also solves the 'link icon problem'. Without reparsing links always
			## show a generic file icon insted of the icon of their target. So I guess SHNotify
			## passes one of these 'simple' pIdls it creates on the fly. 
			
			for i in self.Mainframe.Shell:
				if shell.PidlIsEqual(i, pIdl_tmp):
					pIdlRel= i
				else:			
					shell.PidlFree(i)
						
			
			if pIdlRel:
											
				addr= addressof(pIdlRel)
				self.Mainframe.pIdls[addr]= pIdlRel
				name= self.Mainframe.Shell.GetName(pIdlRel)
				attrs= self.Mainframe.Shell.GetAttributes(pIdlRel, shell.SFGAO_SHARE | shell.SFGAO_LINK | shell.SFGAO_FOLDER)
				iIcon= self.Mainframe.Shell.GetIconIndex(pIdlRel)
				if iIcon==None:
					iIcon= 0
				data= None
				if not attrs & shell.SFGAO_FOLDER:
					try: data= self.Mainframe.Shell.GetData(pIdlRel)
					except: pass
				
												
				ovl= 0
				if attrs & shell.SFGAO_SHARE:
					ovl |= ICO_SHARE
				if attrs & shell.SFGAO_LINK:
					ovl |= ICO_LINK
								
				nNewItem= self.Item(name, 
													lp=addr, 
													iImage=iIcon,
													iOverlayImage=ovl)	
			
				## add size and date information
				if data:
					self.SetItemText(nNewItem, 
												1,
												self.Mainframe.FormatInt(data[0]))
					filetime= wintime.FiletimeToLocalFiletime(data[1])
					t= wintime.FiletimeToSystemtime(filetime)
					self.SetItemText(nNewItem, 2, self.Mainframe.FormatTime(t))
						
			
			return nNewItem	
	
	
	def DL_AddPidl2(self, pIdl):
		
		## see remarks in DL_AddPidl
		
		## TODO:
		## icons for links get not retrieved 
				
		nNewItem= None
		if pIdl:
			
			pIdlRel=  shell.PidlGetLast(pIdl)
						
			if not self.DL_HasItem(pIdlRel):
								
				attrs= self.Mainframe.Shell.GetAttributes(pIdlRel, shell.SFGAO_SHARE | shell.SFGAO_LINK)
				ovl= 0
				if attrs & shell.SFGAO_SHARE:
					ovl |= ICO_SHARE
				if attrs & shell.SFGAO_LINK:
					ovl |= ICO_LINK
					
				iIcon= self.Mainframe.Shell.GetIconIndex(pIdlRel)
				if iIcon==None:
					iIcon= 0
				
				self.Mainframe.pIdls[addressof(pIdlRel)]= pIdlRel
				name= self.Mainframe.Shell.GetName(pIdlRel)
				nNewItem= self.Item(name, 
													lp=addressof(pIdlRel), 
													iImage=iIcon,
													iOverlayImage=ovl)	
			
				## add size and date information
				if not self.Mainframe.Shell.IsFolder(pIdlRel):
					## the pIdl passed does not always contain valid information.
					## Its some kind of stub pIdl. Cheep cheat here to update the information
					## stored in the pIdl. There is also some newly documented api to
					## handle this. Currently to lazy searching for it and its to hot outside.
					## also thought Validate might help here, but never seems to work....
					path= self.Mainframe.Shell.GetParseName(pIdlRel)
					pIdl= shell.PidlFromPath(path)
					pidlRel= shell.PidlGetLast(pIdl)
					
					try:
						data= self.Mainframe.Shell.GetData(pIdlRel)
					except:
						data= None
					shell.PidlFree(pIdl)
					
					if data:
						self.SetItemText(nNewItem, 1, str(data[0]))
						filetime= wintime.FiletimeToLocalFiletime(data[1])
						t= wintime.FiletimeToSystemtime(filetime)
						self.SetItemText(nNewItem, 2, 
							'%s.%s.%s %s:%s:%s' % (t.wDay, t.wMonth, t.wYear, t.wHour, t.wMinute, t.wSecond)
							)
			
			return nNewItem
				
							
	
	def DL_RemovePidl(self, pIdl):
		if pIdl:
			pIdlRel= shell.PidlGetLast(pIdl)
			n= self.DL_GetItemIndex(pIdlRel)
			if n != None:
				lp= self.GetItemLparam(n)
				shell.PidlFree(shell.PIDL.from_address(lp))
				del self.Mainframe.pIdls[lp]
				
				self.SetRedraw(False)
				self.RemoveItem(n)
				self.SetRedraw(True)
				self.RedrawClientArea()
				return True
		return False


			
	def DL_RenamePidl(self, pIdlOld, pIdlNew):	
		
		result= None
		pIdl= self.Mainframe.Shell.GetCwd()
		try:
			if shell.PidlIsParent(pIdl, pIdlOld, 1):
				if shell.PidlIsParent(pIdl, pIdlNew, 1):
					## rename

					nameOld= self.Mainframe.Shell.GetName(shell.PidlGetLast(pIdlOld))
					n= self.FindExact(nameOld)
					if n != None:
						## on label edit we should not be able to find the item
											
						lp= self.GetItemLparam(n)
						shell.PidlFree(self.Mainframe.pIdls[lp])
						del self.Mainframe.pIdls[lp]

						pIdl= shell.PidlCopy(shell.PidlGetLast(pIdlNew))
						self.SetItemLparam(n, addressof(pIdl))
						self.Mainframe.pIdls[addressof(pIdl)]= pIdl

						name= self.Mainframe.Shell.GetName(shell.PidlGetLast(pIdlNew))
						self.SetItemText(n, 0, name)
						result= True
				
				else:
					## remove
					result= self.DL_RemovePidl(pIdlOld)
			else:
				if shell.PidlIsParent(pIdl, pIdlNew, 1):
									
					## add
					result= self.DL_AddPidl(pIdlNew) != None
		
		finally:
			shell.PidlFree(pIdl)
		return result

	
	## TODO: test
	def DL_ShareUnsharePidl(self, pIdl, share=True):
		
		pIdlRel= shell.PidlGetLast(pIdl)
		n=  self.DL_GetItemIndex(pIdlRel)
		if n != None:
			ovl= self.GetItemOverlayImage(n)
			if share:
				self.SetItemOverlayImage(n, ovl | ICO_SHARE)
			else:
				self.SetItemOverlayImage(n, ovl & (~ICO_SHARE))
			
	
	#----------------------------------------------------------------------------------------
	# all the file list methods
	
	
	def DL_Refresh(self):
		if self.Mainframe.Header.DL_HasDir():
			return self.DL_ListFiles(self.Mainframe.Shell.GetCwd())
		return False
	
	
	def DL_ListFiles(self, path):
			
		
		old_dirname= self.Mainframe.Shell.GetParseName()
		
		self.Mainframe.Reset()
				
		## stop file lister
		self.Mainframe.FileLister.Stop()
		
		
		if isinstance(path, (int, long)):
			self.Mainframe.Shell.OpenSpecialFolder(path)
		elif isinstance(path, basestring):
			if os.path.isdir(path):
				self.Mainframe.Shell.OpenFolder(path)
			else:
				print 
				try:
					self.Mainframe.Shell.OpenSpecialFolder(self.Mainframe.CLSIDLS[path])
				except:
					self.Mainframe.lastError= "invalid path or CLSIDL: %s" % path
					return False
					
		elif isinstance(path, shell.PIDL):
			self.Mainframe.Shell.SetCwd(path)
		
		
		if self.Mainframe.SHNotify:
			try:
				self.Mainframe.SHNotify.Close()
			except: pass
			
			try:
				self.Mainframe.SHChangeNotify.Close()
			except: pass
						
						
			## register a notification handle, either by path or pIdl
			## TODO desktop is registered by pIdl so changes in this folder
			## use the slower SHNotify approach
			path= self.Mainframe.Shell.GetParseName()
			if winpath.IsDir(path):
				self.Mainframe.SHChangeNotify.Register(
							self.Mainframe.Shell.GetParseName()
							)
			else:
				pIdl= self.Mainframe.Shell.GetCwd()
				self.Mainframe.SHNotify.Register(pIdl)
				shell.PidlFree(pIdl)

		
		## 0.35
		## 0.31	## with new low level pIdl calls
		result= self.Mainframe.FileLister.ListFiles(old_dirname)
		#self.Mainframe.MsgHandler(self.Hwnd, "dirchanged", 0, result)
		return result

			
		


	
	def DL_DirUp(self):
		
		if self.Mainframe.DL_HasDir():
		
			if not self.Mainframe.Shell.IsDesktopFolder():
												
				pIdlRoot= self.Mainframe.Shell.GetCwd()
				
				if shell.ILIsZero(shell.PidlGetNext(pIdlRoot)):
					## PidlGetParent fails here, returning arbitrary memory ??
					shell.PidlFree(pIdlRoot)
					pIdlRoot= shell.PIDL()	 ## next is desktop
								
				else:
					shell.PidlGetParent(pIdlRoot)
								
				name= self.Mainframe.Shell.GetName()
				self.DL_ListFiles(pIdlRoot)
			
							
				## put hilight to level up item
				if winpath.GetRoot(name):
					name= winpath.GetFileName(name)
				result= self.FindExact(name)
				if result != None:
					self.SelectItem(result)
					self.SetFocusItem(result)
					self.EnshureVisible(result)
				return True
		return False
					
	
	
	def DL_OnReturn(self, hwnd, callback):
		
		trigger_verb= True
				
		## get selected item
		n= self.GetSelectedItem()
		if n == None:
			trigger_verb= False
		
		else:
			if self.Mainframe.FileLister.IsNavigateAllowed():
				
				pIdl= self.DL_GetPidlRel(n)
				
				## if its a folder -- list it
				if self.Mainframe.Shell.IsFolder(pIdl):
					pIdlAbs= self.DL_GetPidlAbs(n)
					self.DL_ListFiles(pIdlAbs)
					try: self.SetFocusItem(0)
					except: pass
					trigger_verb= False
				else:
					## check if its a link to a folder
					if self.Mainframe.Shell.IsLink(pIdl):
						
						path= self.Mainframe.Shell.GetParseName(pIdl)
						lnk= shelllink.ShellLink()
						try:
							lnk.Load(path)
						except:
							pass
						else:
							
							pIdl_lnk= lnk.GetPidl()
							if pIdl_lnk:
								## if its link to desktop -- as fallback
								if shell.ILIsZero(pIdl_lnk):		
									self.DL_ListFiles(pIdl_lnk)
								
								else:
									pIdl_lnk2= shell.PidlCopy(pIdl_lnk) 
									cwd= self.Mainframe.Shell.GetCwd()

									pIdl_child= shell.PidlSplit(pIdl_lnk)
									self.Mainframe.Shell.SetCwd(pIdl_lnk)
									isfolder= self.Mainframe.Shell.IsFolder(pIdl_child)
									shell.PidlFree(pIdl_lnk)
									shell.PidlFree(pIdl_child)
									
									## if its a link to a folder -- list it
									if isfolder:
										shell.PidlFree(cwd)
										self.DL_ListFiles(pIdl_lnk2)	## could fallback here if ST goes wrong
										try: self.SetFocusItem(0)
										except: pass
										trigger_verb= False
									else:
										shell.PidlFree(pIdl_lnk2)
										self.Mainframe.Shell.SetCwd(cwd)
			
												
			## trigger default verb for non folder item
			if trigger_verb:	
					
				result= self.Mainframe.MsgHandler(hwnd, "command", n, 0)
				if result !=False:
					if self.Mainframe.SHContextMenu:
						self.Mainframe.SHContextMenu.DL_TriggerDefaultVerb(n)
		
			
	
	
	
	
	def DL_OnLabelEdit(self, hwnd, msg, wp, lp):
		if wp:
			nItem= lp[0]
			pIdlRel= self.DL_GetPidlRel(nItem)
			if self.Mainframe.Shell.CanRename(pIdlRel):
				pIdl= shell.PidlCopy(pIdlRel)
				name= self.Mainframe.Shell.GetParseName()
				if len(name) + len(wp) + 1 <= 260:	# MAX_PATH
					try:
						## pIdl is renamed in-place, so our pIdl list gets updated aswell
						pIdlNew= self.Mainframe.Shell.SetName(wp, pIdlRel)
						shell.PidlFree(pIdl)
						return True
					except: 
						## the shell seems to free the pIdl in case of an error
						## ++ throws a nice messagebox for free
						if shell.Malloc.GetSize(pIdlRel):
							shell.PidlFree(self.Mainframe.pIdls[addressof(pIdlRel)])
						del self.Mainframe.pIdls[addressof(pIdlRel)]
						self.SetItemLparam(nItem, addressof(pIdl))
						self.Mainframe.pIdls[addressof(pIdl)]= pIdl
					
				return False	
	
	
	def DL_TriggerContextMenu(self, keyb=False):
		
		nItem= self.GetSelectedItem()
		if  nItem != None:
			if self.Mainframe.SHContextMenu:
				return self.Mainframe.SHContextMenu.DL_OnContextMenu(self.Hwnd, nItem, keyb=keyb)
				
		else:
			if self.Mainframe.ContextMenu2:
				return self.Mainframe.ContextMenu2.DL_OnContextMenu()

			## no menus? call user directly
		self.Mainframe.MsgHandler(hwnd, "rmbup", 0, 0)
	
	
	def DL_AdjustColumnWidth(self, w=None):
		if w==None:
			w= self.GetClientRect().ToSize()[2]
		w= w/5
		self.SetColumnWidth(0, w*2)
		self.SetColumnWidth(1, w)
		self.SetColumnWidth(2, w*2)
		
		
	
	#-----------------------------------------------------------------------------------------
	
