

from wnd.controls.menu.header import *
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::


class Popup(object):
	"""Popup class returned by the Menu methods
	'Popup', 'InsertPopup' and 'GetPopup'."""

	_client_buffer = create_string_buffer(261)
		
	def __init__(self, handle=None, parentHandle=None):
		if handle: self.handle=handle
		else:
			if parentHandle:	self.handle=parentHandle
			else:	self.handle = user32.CreatePopupMenu()
	
	def _client_TruncText(self, text):
		"""Truncates text to _client_buffer. Return value is
		the address of the buffer."""
		n = len(text)
		szeof = sizeof(self._client_buffer) -1
		if n > szeof: text = '%s...\x00' % text[:szeof-3]
		else: text = '%s\x00' % text
		self._client_buffer.raw = text + '\x00'
		return addressof(self._client_buffer)			
	
	def SetTextMax(self, n):
		if n > 2:
			if n != sizeof(self._client_buffer):
				self._client_buffer = create_string_buffer(n+1)
		else:
			raise ValueError("max text should be atleast 3 chars")
	
	def GetTextMax(self):
		return sizeof(self._client_buffer) -1
	
	def Item(self, title, ID, *flags):
		return self.InsertItem(title, -1, ID, *flags)
			
	def InsertItem(self, title, IDbefore, ID,*flags):
		itemState=0
		itemType=0
		if flags:
			#'menubarbreak': 32,'menubreak':64,
			state_flags={'disabled' : 3,'checked' : 8,'default':4096}
			type_flags = {'menubarbreak': 32,'menubreak':64, 'ownerdraw':256}
			for i in flags:
				try: itemState |= state_flags[i]
				except: 
					try: itemType |= type_flags[i]
					except: raise ValueError("invalid flag: '%s'" % i)
		mi= MENUITEMINFO()
		mi.fMask = MIIM_TYPE|MIIM_ID|MIIM_STATE 
		mi.fState = itemState
		mi.fType = itemType
		mi.dwTypeData=self._client_TruncText(title)
		mi.wID = ID
		if not user32.InsertMenuItemA(self.handle, IDbefore, 0, byref(mi)):
			raise RuntimeError("could not insert Item")
	
	def Popup(self, title, ID, *flags):
		return self.InsertPopup(title, -1, ID, *flags)
	
	def InsertPopup(self, title, IDbefore, ID, *flags):
		itemState=0
		if flags:
			state_flags={'disabled' : 3}
			for i in flags:
				try: itemState |= state_flags[i]
				except: 
					raise ValueError("invalid flag: '%s'" % i)
		popup = Popup()
		mi= MENUITEMINFO()
		mi.fMask = MIIM_TYPE | MIIM_ID | MIIM_SUBMENU | MIIM_STATE
		mi.fState = itemState
		mi.fType=0
		mi.hSubMenu =popup.handle
		mi.dwTypeData= self._client_TruncText(title)
		mi.wID = ID
		if not user32.InsertMenuItemA(self.handle, IDbefore, 0, byref(mi)):
			raise RuntimeError("could not insert Popup")
		return popup
	
	def Separator(self, ID, *flags):
		return self.InsertSeparator(-1, ID, *flags)
		
	def InsertSeparator(self, IDbefore, ID, *flags):
		itemType= MFT_SEPARATOR  = 2048
		if flags:
			type_flags = {'menubarbreak': 32,'menubreak':64}
			for i in flags:
				try: itemType |= type_flags[i]
				except: raise ValueError("invalid flag: '%s'" % i)
		mi= MENUITEMINFO()
		mi.fMask = MIIM_TYPE|MIIM_ID
		mi.fType = itemType
		mi.wID = ID
		if not user32.InsertMenuItemA(self.handle, IDbefore, 0, byref(mi)):
			raise RuntimeError("could not insert Separator")
		
	def GetItemCount(self):
		result=user32.GetMenuItemCount(self.handle)
		if result==-1:
			raise RuntimeError("could not retrieve item count")
		return result
	
	def SetDefaultItem(self, ID):
		if not user32.SetMenuDefaultItem(self.handle, ID, 0):
			raise RuntimeError("could not set default item")
  
	def GetDefaultItem(self):
		result=user32.GetMenuDefaultItem(self.handle, 0, 0)
		if result==-1:	return None
		return result
		
	def ClearDefaultItem(self):
		if user32.GetMenuDefaultItem(self.handle, 0, 0)==-1:
			return False
		if not user32.SetMenuDefaultItem(self.handle, -1, 0):
			raise RuntimeError("could not set default item")
		return True

	
	def ListItems(self, hMenu=None):
		if not hMenu:
			hMenu=self.handle
		n = user32.GetMenuItemCount(hMenu)
		mi= MENUITEMINFO()
		out= []
		for i in range(n):
			mi.fMask = 2 #  MIIM_ID
			user32.GetMenuItemInfoA(hMenu, i, 1, byref(mi))
			out.append(mi.wID)
		return out