"""shell context self.Menu handler for the dirlist"""


import os
from wnd.api import shell, clipboard 
from wnd.controls.menu import Menu, ContextMenu
from wnd.wintypes import POINT
from wnd.api.shell import shellnew, shelllink

#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

WM_INITMENUPOPUP    = 279


## shell ontextmenu
SH_POPUPID = 1
SH_MINID = SH_POPUPID + 1
SH_MAXID = SH_MINID + 29999


## second self.Contextmenu
MENU2_POPUPID= SH_MAXID + 1
MENU2_MINID = MENU2_POPUPID + 1



IDM_NEWFILE= MENU2_MINID +1
IDM_NEWFOLDER= MENU2_MINID +2

IDM_PASTE= MENU2_MINID +3
IDM_PASTE_LINK= MENU2_MINID +4


## popup View
IDM_VIEW= MENU2_MINID + 20
IDM_VIEW_DETAILS= IDM_VIEW + 2
IDM_VIEW_LIST= IDM_VIEW + 3
IDM_VIEW_ICONVIEW= IDM_VIEW + 4

IDM_VIEW_ICO= IDM_VIEW + 5
IDM_VIEW_SMICO= IDM_VIEW + 6

## popup Sort
IDM_SORT= MENU2_MINID + 40

IDM_SORT_DATE= IDM_SORT + 1
IDM_SORT_NAME= IDM_SORT + 2
IDM_SORT_SIZE= IDM_SORT + 3
IDM_SORT_TYPE= IDM_SORT + 4
IDM_SORT_ASC= IDM_SORT + 5
IDM_SORT_DESC= IDM_SORT + 6


MENU2_MAXID = MENU2_MINID + 100



IDM_SHELL_NEW=  MENU2_MAXID + 1
SHNEW_MINID = IDM_SHELL_NEW + 1
SHNEW_MAXID = SHNEW_MINID + 1000


ID_MAX= SHNEW_MAXID





class SHContextMenu(shell.ShellContextMenu):
	def __init__(self, mainframe):
		
		self.Mainframe= mainframe
		
		shell.ShellContextMenu.__init__(self, SH_MINID, SH_MAXID)
		self.onMSG= self.Mainframe.MsgHandler

		self.Menu= Menu()
		self.Contextmenu= ContextMenu()
		self.Popup= self.Menu.Popup('sh_contextmenu', SH_POPUPID)
				

	## ??
	def Close(self):
		self.Menu.Close()
	
	
		
	def DL_OnContextMenu(self, hwnd, nItem, keyb=True):
				
		## TODO
		## invoke self.Menu on VK_MENU. either display on 0, 0 or on the current selection
		
		self.Mainframe.lastError= None
		
				
		result= self.Mainframe.MsgHandler(hwnd, "shell_contextmenu", "int", nItem)
		if result==False: return False
		if keyb:
			## calculate context self.Menu pos if invoked from keyboard
			rc= self.Mainframe.Listview.GetItemRect(nItem, 0)
			rc.ClientToScreen(self.Mainframe.Listview.Hwnd)
			rc2= self.Mainframe.Listview.GetItemIconRect(nItem, 0)
			x, y= rc.left + (((rc2.right- rc2.left)*3)/2), rc.bottom - ((rc.bottom-rc.top)/3)
				
		else:
			x, y= self.Mainframe.Listview.GetCursorPos()		
			
		
		arr= self.Mainframe.Listview.DL_GetPidlsSelected()
		if not arr: return False
			
		
		## init context self.Menu
		if result:
			flags = result
		else:	
			if self.Mainframe.Shell.CanRename(arr) and len(arr)==1:
				flags= 'canrename',
			else:
				flags= ()
				
		self.Menu.Clear(self.Popup.handle)
		
		pIdlRoot= self.Mainframe.Shell.GetCwd()
		result= SHContextMenu.QueryContextMenu(self, pIdlRoot, arr, self.Popup.handle, *flags)
		shell.PidlFree(pIdlRoot)
		
		
		if not result:
			self.Mainframe.lastError= self.GetLastError()
			return False
		
		## subclass parent and popup self.Menu
		result= self.Mainframe.MsgHandler(hwnd, "shell_contextmenu", "open", self.Popup)	
		SHContextMenu.SubclassParent(self, self.Mainframe.Listview)
		try:
			ID= self.Contextmenu.Popup(
							self.Mainframe.Listview,
							result and result.handle or self.Popup.handle, 
							x,
							y,
							'returncmd')
		except Exception, d:
			self.SetLastError(Exception, d)
		SHContextMenu.RestoreParentProc(self, self.Mainframe.Listview)	
		
		
		## invoke command
		if not self.lastError:
			cmd= SHContextMenu.GetCommandString(self, ID).lower()
			if cmd=='rename':
				if nItem != None:
					if 'editlabels' in self.Mainframe.Listview.GetStyle():
						self.Mainframe.Listview.EditLabel(nItem)
				## TODO: rename item
				pass
						
			else:
				if not SHContextMenu.InvokeCommand(self, ID, point=POINT(x, y)):
					self.Mainframe.lastError= self.GetLastError()
					if not self.lastError:
						self.Mainframe.MsgHandler(hwnd, "shell_contextmenu", "command", ID)	
					
		SHContextMenu.Reset(self)
		self.Mainframe.MsgHandler(hwnd, "shell_contextmenu", "close", not self.lastError)
	
		
	def DL_TriggerDefaultVerb(self, nItem):
		# some QueryContextMenu + GetDefaultItem on the self.Menu filled in by the shell
					
		self.Mainframe.lastError= None
					
		lp= self.Mainframe.Listview.GetItemLparam(nItem)
		if lp:
			pIdl= shell.PIDL.from_address(lp)
			if not shell.ILIsZero(pIdl):
				self.Menu.Clear(self.Popup.handle)
				
				pIdlRoot= self.Mainframe.Shell.GetCwd()
				result= SHContextMenu.QueryContextMenu(self, pIdlRoot, pIdl, self.Popup.handle, 'defaultonly')
				shell.PidlFree(pIdlRoot)
				
				if result:
					ID= self.Popup.GetDefaultItem()
					if SHContextMenu.IsMenuID(self, ID):
						if SHContextMenu.GetCommandString(self, ID).lower()=='rename':
							nItem= self.Mainframe.Listview.GetSelectedItem()
							if nItem != None:
								if 'editlabels' in self.Mainframe.Listview.GetStyle():
									self.Mainframe.Listview.EditLabel(nItem)
								
						else:
							if not SHContextMenu.InvokeCommand(self, ID):
								self.lastError= SHContextMenu.GetLastError(self)
						SHContextMenu.Reset(self)

				else:
					self.Mainframe.lastError= self.GetLastError()
		
		return not self.lastError
		

		

#***************************************************************************
#***************************************************************************

class ContextMenu2(shellnew.ShellNewMenu):
	def __init__(self, mainframe):
		self.Mainframe= mainframe
		
		shellnew.ShellNewMenu.__init__(self, SHNEW_MINID, SHNEW_MAXID)
				
		self.Menu= Menu()
		self.Contextmenu= ContextMenu()
		
		self.Popup= self.Menu.Popup('ContextMenu2', MENU2_POPUPID)
		
		
		lang= self.Mainframe.GetViewLang()
		
		self.Popup.Item(lang.NEWFILE, IDM_NEWFILE)
		self.Popup.Item(lang.NEWFOLDER, IDM_NEWFOLDER)

		self.Popup.Separator(0)
		
		self.Popup.Item(lang.PASTE, IDM_PASTE)
		self.Popup.Item(lang.PASTE_LINK, IDM_PASTE_LINK)

		self.Popup.Separator(0)
				
		pop= self.Popup.Popup(lang.SORT, IDM_SORT)
		pop.Item(lang.SORT_DATE, IDM_SORT_DATE)
		pop.Item(lang.SORT_NAME, IDM_SORT_NAME)
		pop.Item(lang.SORT_SIZE, IDM_SORT_SIZE)
		pop.Item(lang.SORT_TYPE, IDM_SORT_TYPE)
		pop.Separator(0)
		pop.Item(lang.SORT_ASC, IDM_SORT_ASC)
		pop.Item(lang.SORT_DESC, IDM_SORT_DESC)
				
		pop= self.Popup.Popup(lang.VIEW, IDM_VIEW)
		pop.Item(lang.VIEW_DETAILS, IDM_VIEW_DETAILS)
		pop.Item(lang.VIEW_LIST, IDM_VIEW_LIST)
		pop.Item(lang.VIEW_ICON, IDM_VIEW_ICONVIEW)

		pop.Separator(0)
		pop.Item(lang.VIEW_ICONLARGE, IDM_VIEW_ICO)
		pop.Item(lang.VIEW_ICONSMALL, IDM_VIEW_SMICO)
						
		self.Popup.Separator(0)
		
		self.Popup.Popup(lang.SHELL_NEW, IDM_SHELL_NEW)

		
		
	def SetLang(self, lang):
		self.Menu.SetItemText(IDM_NEWFILE, lang.NEWFILE)
		self.Menu.SetItemText(IDM_NEWFOLDER, lang.NEWFOLDER)
		self.Menu.SetItemText(IDM_PASTE, lang.PASTE)
		self.Menu.SetItemText(IDM_PASTE_LINK, lang.PASTE_LINK)
		self.Menu.SetItemText(IDM_SORT, lang.SORT)
		self.Menu.SetItemText(IDM_SORT_DATE, lang.SORT_DATE)
		self.Menu.SetItemText(IDM_SORT_NAME, lang.SORT_NAME)
		self.Menu.SetItemText(IDM_SORT_SIZE, lang.SORT_SIZE)
		self.Menu.SetItemText(IDM_SORT_TYPE, lang.SORT_TYPE)
		self.Menu.SetItemText(IDM_SORT_ASC, lang.SORT_ASC)
		self.Menu.SetItemText(IDM_SORT_DESC, lang.SORT_DESC)
		self.Menu.SetItemText(IDM_VIEW, lang.VIEW)
		self.Menu.SetItemText(IDM_VIEW_DETAILS, lang.VIEW_DETAILS)
		self.Menu.SetItemText( IDM_VIEW_LIST, lang.VIEW_LIST)
		self.Menu.SetItemText(IDM_VIEW_ICONVIEW, lang.VIEW_ICON)
		self.Menu.SetItemText(IDM_VIEW_ICO, lang.VIEW_ICONLARGE)
		self.Menu.SetItemText(IDM_VIEW_SMICO, lang.VIEW_ICONSMALL)
		self.Menu.SetItemText(IDM_SHELL_NEW, lang.SHELL_NEW)
		
		
	
	def DL_OnContextMenu(self):
		
		x, y= self.Mainframe.Listview.GetCursorPos()
		self.SubclassParent(self.Mainframe.Listview)
		try:
			ID= self.Contextmenu.Popup(
							self.Mainframe.Listview,
							self.Popup.handle, 
							x,
							y,
							'returncmd')
		finally:
			self.RestoreParentProc(self.Mainframe.Listview)
			
		if self.IsMenuID(ID):
			
			if self.Mainframe.Shell.IsDesktopFolder():
				path= shell.GetSpecialFolderPath(shell.CLSIDL_DESKTOP)
				if path:
					self.InvokeCommand(ID, path)
			else:
				self.InvokeCommand(ID, self.Mainframe.Shell.GetParseName())
		else:
			
			if ID== IDM_NEWFILE:
				error= True
				pIdl= None
				path= self.MakeUniqueFilename(
							self.Mainframe.Shell.GetParseName(), 
							self.Mainframe.GetViewLang().NEWFILE,
							'.txt', 
							isdir=False
						)
				if path:
					try:
						open(path, 'w').close()
						pIdl= shell.PidlFromPath(path)
						n= self.Mainframe.Listview.DL_AddPidl(pIdl)
						if n !=None:
							if 'editlabels' in self.Mainframe.Listview.GetStyle():
								self.Mainframe.Listview.EditLabel(n)
							error= False
					except: pass
					
				if error:
					if pIdl:
						shell.PidlFree(pIdl)	
					self.Mainframe.Listview.Beep('asterisk')
			
			
			elif ID==IDM_NEWFOLDER:
				error= True
				pIdl= None
				path= self.MakeUniqueFilename(
							self.Mainframe.Shell.GetParseName(), 
							self.Mainframe.GetViewLang().NEWFOLDER,
							ext= '', 
							isdir=True
						)
				if path:
					try:
						os.mkdir(path)
						pIdl= shell.PidlFromPath(path)
						n= self.Mainframe.Listview.DL_AddPidl(pIdl)
						if n !=None:
							if 'editlabels' in self.Mainframe.Listview.GetStyle():
								self.Mainframe.Listview.EditLabel(n)
							error= False
					except: pass
					
				if error:
					if pIdl:
						shell.PidlFree(pIdl)	
					self.Mainframe.Listview.Beep('asterisk')
			
				
			elif ID==IDM_PASTE:
				if clipboard.IsFormatAvailable(clipboard.cf.hdropfiles):
					self.Mainframe.Listview.DL_SetCursor('wait')
					
					do= clipboard.GetDataObject()
					hdrop= clipboard.cf.hdropfiles()
					do.GetData(hdrop)
					files= hdrop.value
					hdrop.value= None
					if self.Mainframe.Shell.IsDesktopFolder():
						root= shell.GetSpecialFolderPath(shell.CLSIDL_DESKTOP)
					else:
						root= self.Mainframe.Shell.GetParseName()
					shell.CopyFiles(files, root)
					self.Mainframe.Listview.DL_SetCursor('arrow')

							
			elif ID==IDM_PASTE_LINK:
				if clipboard.IsFormatAvailable(clipboard.cf.hdropfiles):
					do= clipboard.GetDataObject()
					hdrop= clipboard.cf.hdropfiles()
					do.GetData(hdrop)
					files= hdrop.value
					hdrop.value= None
					
					if self.Mainframe.Shell.IsDesktopFolder():
						root= shell.GetSpecialFolderPath(shell.CLSIDL_DESKTOP)
					else:
						root= self.Mainframe.Shell.GetParseName()
					for i in files:
						name= os.path.split(i)[1]
						name, ext= os.path.splitext(name)
						name= self.MakeUniqueFilename(root, name, ext='.lnk')
						if name:
							lnk= shelllink.ShellLink()
							lnk.SetTarget(i)
							lnk.Save(name)

			## view submenu
							
			elif ID==IDM_VIEW_LIST:
				self.Mainframe.SetStyle('list')
			elif ID==IDM_VIEW_DETAILS	:
				self.Mainframe.SetStyle('report')	
			elif ID==	IDM_VIEW_ICONVIEW:
				self.Mainframe.SetStyle('icon')	
			elif ID==IDM_VIEW_ICO:
				self.Mainframe.SetStyle('largeicon')
			elif ID==IDM_VIEW_SMICO:
				self.Mainframe.SetStyle('-largeicon')
			
			
			## sort submenu
			
			elif ID==IDM_SORT_SIZE:
				self.Mainframe.FileLister.SetSortType(fSort='size')
				self.Mainframe.FileLister.SortFiles()
			
			elif ID==IDM_SORT_DATE:
				self.Mainframe.FileLister.SetSortType(fSort='date')
				self.Mainframe.FileLister.SortFiles()
							
			elif ID==IDM_SORT_NAME:
				self.Mainframe.FileLister.SetSortType(fSort='name')
				self.Mainframe.FileLister.SortFiles()
							
			elif ID==IDM_SORT_TYPE:
				self.Mainframe.FileLister.SetSortType(fSort='type')
				self.Mainframe.FileLister.SortFiles()
							
			elif ID==IDM_SORT_ASC:
				self.Mainframe.FileLister.SetSortType(direction='ascending')
				self.Mainframe.FileLister.SortFiles()
				
			elif ID==IDM_SORT_DESC:
				self.Mainframe.FileLister.SetSortType(direction='descending')
				self.Mainframe.FileLister.SortFiles()
						
			
	
	def HandleMessage(self, hwnd, msg, wp, lp):
		if msg==WM_INITMENUPOPUP:
			ShNew= self.Menu.GetPopup(IDM_SHELL_NEW)
			View= self.Menu.GetPopup(IDM_VIEW)
			Sort= self.Menu.GetPopup(IDM_SORT)

						
			if clipboard.IsFormatAvailable(clipboard.cf.hdropfiles):
				self.Menu.Enable(IDM_PASTE)
				self.Menu.Enable(IDM_PASTE_LINK)
			else:
				self.Menu.Disable(IDM_PASTE)
				self.Menu.Disable(IDM_PASTE_LINK)
			
			if wp==View.handle:
				if self.Mainframe.Listview.DL_IsSmallIcon():
					check=  IDM_VIEW_SMICO
				else:
					check= IDM_VIEW_ICO
				self.Menu.CheckRadioItem(IDM_VIEW_ICO, IDM_VIEW_SMICO, check)
								
				styles= self.Mainframe.Listview.GetStyle()
				if 'report' in styles:
					check= IDM_VIEW_DETAILS
				elif 'icon' in styles:
					check= IDM_VIEW_ICONVIEW
				else:
					check= IDM_VIEW_LIST
				self.Menu.CheckRadioItem(IDM_VIEW_DETAILS, IDM_VIEW_ICONVIEW, check)
						
			
			elif wp==Sort.handle:
				check= None
				sorttype= self.Mainframe.FileLister.sorttype
				if sorttype=='date':
					check= IDM_SORT_DATE
				elif sorttype=='name':
					check= IDM_SORT_NAME
				elif sorttype=='size':
					check= IDM_SORT_SIZE
				elif sorttype=='type':
					check= IDM_SORT_TYPE
				if check:
					self.Menu.CheckRadioItem(IDM_SORT_DATE,  IDM_SORT_TYPE, check)
				
				check= None
				sortdirection= self.Mainframe.FileLister.sortdirection
				if sortdirection=='ascending':
					check= IDM_SORT_ASC
				elif sortdirection=='descending':
					check= IDM_SORT_DESC
				if check:
					self.Menu.CheckRadioItem(IDM_SORT_ASC,  IDM_SORT_DESC, check)

			
			elif wp==ShNew.handle:
				self.Menu.Clear(ShNew.handle)
				shellnew.ShellNewMenu.QueryShellNewMenu(self, ShNew)
			
					
		return shellnew.ShellNewMenu.HandleMessage(self, hwnd, msg, wp, lp)

	
	
