
from wnd.controls.menu.header import *
from wnd.controls.menu.popup import Popup
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::


	
class MenuMethods:	
	
	def Set(self, Window):
		if self._client_hwndParent:
			raise RuntimeError("menu is alreaddy atatched to a window")
		oldmenu = user32.GetMenu(Window.Hwnd)
		if oldmenu == self.handle:
			raise RuntimeError("menu is alreaddy attatched to the window")
		else:
			TrackHandler.Unregister('menus', self.handle)
			if not user32.SetMenu(Window.Hwnd, self.handle):
				raise RuntimeError("could not set menu")
			if not user32.DrawMenuBar(Window.Hwnd):
				raise RuntimeError("could not redraw menu bar")
			if oldmenu:
				TrackHandler.Register('menus', self.handle)
			self._client_hwndParent = Window.Hwnd
			
	def Remove(self, Window):
		if self._client_hwndParent:
			raise RuntimeError("menu is not atatched to the window")
		if not self.handle==user32.GetMenu(Window.Hwnd):
			raise RuntimeError("menu is not attatched to the window")
		TrackHandler.Register('menus', self.handle)
		if not user32.SetMenu(Window.Hwnd, 0):
			raise RuntimeError("could not remove menu")
		if not user32.DrawMenuBar(Window.Hwnd):
			raise RuntimeError("could not redraw menu bar")
		self._client_hwndParent = None
				
	def Close(self):
		if self.handle:
			if self._client_hwndParent:
				nm= fw.WND_MENU(self.handle, fw.MNUT_MENU, fw.MNUF_REMOVE)
				user32.SendMessageA(self._client_hwndParent, 
														fw.WND_WM_NOTIFY,
														fw.WND_NM_MENU,
														byref(nm))
			try:	# we can not know if the menu is currently in use
				TrackHandler.Unregister('menus', self.handle)
			except: pass
			if not user32.DestroyMenu(self.handle):
				raise RuntimeError("could not destroy menu")
			self.handle=0
			self._client_hwndParent = None

	def IsMenuOf(self, Window):
		if user32.GetMenu(Window.Hwnd)==self.handle:
			return True
		return False	
	#--------------------------------------------------------------------
				
	def GetSubMenu(self, ID):
		mi= MENUITEMINFO()
		mi.fMask=MIIM_SUBMENU
		if not user32.GetMenuItemInfoA(self.handle, ID, 0, byref(mi)):
			raise RuntimeError("could not retrieve item info")
		if mi.hSubMenu:
			return mi.hSubMenu
		else:
			raise RuntimeError("no submenu found")
	
	def GetPopup(self, ID):
		try: return Popup(handle=self.GetSubMenu(ID))
		except: raise RuntimeError("no Popup item found")
	#------------------------------------------------------------------------
	def RemoveItem(self, ID):
		if not user32.DeleteMenu(self.handle, ID, 0):
			raise RuntimeError("could not remove item")
	
	
	def IsEnabled(self, ID):
		mi= MENUITEMINFO()
		mi.fMask =  MIIM_STATE
		if not user32.GetMenuItemInfoA(self.handle, ID, 0, byref(mi)):
			raise RuntimeError("could not retrieve item state")
		if mi.fState & MFS_DISABLED:
			return False
		return True
		
	def Enable(self, ID):
		result=user32.EnableMenuItem(self.handle, ID, 0)
		if result==-1:	raise RuntimeError("could not disable item")
		elif result: return True
		return False
		
	def Disable(self, ID):
		result=user32.EnableMenuItem(self.handle, ID, 3)
		if result==-1:	raise RuntimeError("could not disable item")
		return not result
		
	def IsChecked(self, ID):
		mi= MENUITEMINFO()
		mi.fMask =  MIIM_STATE
		if not user32.GetMenuItemInfoA(self.handle, ID, 0, byref(mi)):
			raise RuntimeError("could not retrieve item state")
		return bool(mi.fState & MFS_CHECKED)
			
	def Check(self, ID):
		result = user32.CheckMenuItem(self.handle, ID, MF_CHECKED)
		if result==-1:	raise RuntimeError("could not check item")
		return not result
			
	def Uncheck(self, ID):
		result = user32.CheckMenuItem(self.handle, ID, 0)==-1
		if result==-1: raise RuntimeError("could not check item")
		return not result
			
	def CheckUncheck(self, ID):
		if not self.Check(ID): self.Uncheck(ID)
				
	def CheckRadioItem(self, startID, stopID, ID):
		if not user32.CheckMenuRadioItem(self.handle, startID, stopID, ID, 0):
			raise RuntimeError("could not check radio item")
 
	def GetItemText(self, ID):
		mi= MENUITEMINFO()
		mi.fMask =  MIIM_TYPE
		mi.dwTypeData=addressof(self._client_buffer)
		mi.cch = sizeof(self._client_buffer)
		if not user32.GetMenuItemInfoA(self.handle, ID, 0, byref(mi)):
			raise RuntimeError("could not retrieve item text")
		return self._client_buffer.value
	
	def SetItemText(self, ID, text):
		# first fill out the item type member
		mi= MENUITEMINFO()
		mi.fMask =  MIIM_TYPE
		mi.dwTypeData = 0
		mi.cch = 0
		if not user32.GetMenuItemInfoA(self.handle, ID, 0, byref(mi)):
			raise RuntimeError("could not retrieve item info")
		# ...set the text
		mi.dwTypeData=self._client_TruncText(text)
		if not user32.SetMenuItemInfoA(self.handle, ID, 0, byref(mi)):
			raise RuntimeError("could set item text")
		
	def SetItemLparam(self, ID, lParam):
		mi= MENUITEMINFO()
		# fill out the item type member
		mi= MENUITEMINFO()
		mi.fMask =  MIIM_TYPE
		mi.dwTypeData = 0
		mi.cch = 0
		if not user32.GetMenuItemInfoA(self.handle, ID, 0, byref(mi)):
			raise RuntimeError("could not retrieve item info")
		# ...set lParam
		mi.fMask =  MIIM_DATA
		mi.dwItemData= lParam
		if not user32.SetMenuItemInfoA(self.handle, ID, 0, byref(mi)):
			raise RuntimeError("could set item lParam")

	def GetItemLparam(self, ID):
		mi= MENUITEMINFO()
		mi.fMask =  MIIM_DATA
		if not user32.GetMenuItemInfoA(self.handle, ID, 0, byref(mi)):
			raise RuntimeError("could not retrieve item text")
		return mi.dwItemData 
	
	#------------------------------------------------------------------
		
	def Clear(self, hMenu=None):
		if not hMenu:
			hMenu= self.handle
		n = user32.GetMenuItemCount(hMenu)
		for i in range(n):
			user32.DeleteMenu(hMenu, 0, MF_BYPOSITION)
		
		
	def Walk(self, hMenu=None):
		if not hMenu:
			hMenu=self.handle
		n = user32.GetMenuItemCount(hMenu)
		mi= MENUITEMINFO()
		for i in range(n):
			mi.fMask = 2 #  MIIM_ID
			user32.GetMenuItemInfoA(hMenu, i, 1, byref(mi))
			handle = user32.GetSubMenu(hMenu, i)
			if handle:
				yield handle, self.ListItems(handle)
				for i in self.Walk(handle): 
					yield i
	
	
			
	def IsSeparator(self, ID):
		MIIM_TYPE       = 16
		MFT_SEPARATOR      = 2048
		mi= MENUITEMINFO()
		mi.fMask = MIIM_TYPE
		mi.dwTypeData = 0
		mi.cch = 0
		if not user32.GetMenuItemInfoA(self.handle, ID, 0, byref(mi)):
			raise RuntimeError("could not retrieve item info")
		return bool(mi.fType & MFT_SEPARATOR)
			
	def IsItem(self, ID):
		MIIM_SUBMENU    = 4
		MIIM_TYPE       = 16
		MFT_SEPARATOR      = 2048
		mi= MENUITEMINFO()
		mi.fMask = MIIM_SUBMENU|MIIM_TYPE
		mi.dwTypeData = 0
		mi.cch = 0
		if not user32.GetMenuItemInfoA(self.handle, ID, 0, byref(mi)):
			raise RuntimeError("could not retrieve item info")
		return not mi.fType & (MFT_MENUBARBREAK|MFT_MENUBREAK|MFT_SEPARATOR) # ?? MFT_BITMAP ??
		
	def IsPopup(self, ID):
		MIIM_SUBMENU    = 4
		mi= MENUITEMINFO()
		mi.fMask = MIIM_SUBMENU
		if not user32.GetMenuItemInfoA(self.handle, ID, 0, byref(mi)):
			raise RuntimeError("could not retrieve item info")
		return bool(mi.hSubMenu)
		
	def IsMenuBreak(self, ID):
		MFT_MENUBREAK      = 64
		MIIM_TYPE       = 16
		mi= MENUITEMINFO()
		mi.fMask = MIIM_TYPE
		mi.dwTypeData = 0
		mi.cch = 0
		if not user32.GetMenuItemInfoA(self.handle, ID, 0, byref(mi)):
			raise RuntimeError("could not retrieve item info")
		return bool(mi.fType & MFT_MENUBREAK)
			
	def _client_SetState(self, ID, state, set=True):
		"""Helper method. Sets or clears a style. Return value is
		True if the style changed, False otherwise."""
		MIIM_TYPE    = 16
		# fill out the item type member
		mi= MENUITEMINFO()
		mi.fMask =  MIIM_TYPE
		mi.dwTypeData=addressof(self._client_buffer)
		mi.cch = sizeof(self._client_buffer)
		if not user32.GetMenuItemInfoA(self.handle, ID, 0, byref(mi)):
			raise RuntimeError("could not retrieve item info")
		# ...set or clear the state
		if set:
			if mi.fType & state:
				flag=False
			else:
				mi.fType |= state
				flag=True
		else:
			if mi.fType & state:
				mi.fType &= ~state
				flag=True
			else:
				flag=False
		mi.dwTypeData=addressof(self._client_buffer)
		if not user32.SetMenuItemInfoA(self.handle, ID, 0, byref(mi)):
			raise RuntimeError("could set item info")
		return flag
	
	def SetMenuBreak(self, ID):
		MFT_MENUBREAK   = 64
		return self._client_SetState(ID, MFT_MENUBREAK, set=True)
	
	def ClearMenuBreak(self, ID):
		MFT_MENUBREAK   = 64
		return self._client_SetState(ID, MFT_MENUBREAK, set=False)
		
	def IsMenuBarBreak(self, ID):
		MFT_MENUBARBREAK   = 32
		MIIM_TYPE       = 16
		mi= MENUITEMINFO()
		mi.fMask = MIIM_TYPE
		mi.dwTypeData = 0
		mi.cch = 0
		if not user32.GetMenuItemInfoA(self.handle, ID, 0, byref(mi)):
			raise RuntimeError("could not retrieve item info")
		return bool(mi.fType & MFT_MENUBARBREAK)
			
	def SetMenuBarBreak(self, ID):
		MFT_MENUBARBREAK   = 32
		return self._client_SetState(ID, MFT_MENUBARBREAK, set=True)
		
	def ClearMenuBarBreak(self, ID):
		MFT_MENUBARREAK   = 32
		return self._client_SetState(ID, MFT_MENUBARREAK, set=False)