
"""
TODO

	
	- ownerdrawing
	- the default item does not support lParam an custom checkmarks
		I don't think the Item method should be cluttered with params.
		Keep it simple. Better to add some more item creation methods. 
	- menu items displaying a bitmap
	- ...and some others

"""


from wnd.controls.menu.header import (user32, 
																		TrackHandler,
																		HIWORD,
																		LOWORD,
																		WNDPROC,)

from wnd.controls.menu.popup import Popup
from wnd.controls.menu.methods import MenuMethods
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

class Menu(Popup, MenuMethods):

	def __init__(self):
		self.handle = user32.CreateMenu()
		TrackHandler.Register('menus', self.handle)
		Popup.__init__(self, self.handle)
		self._client_hwndParent = None


class MenuFromTemplate(Popup, MenuMethods):
	
	def __init__(self, template):
		self._client_template= template
		hMenu= user32.LoadMenuIndirectA(template)
		if not hMenu: raise ValueError, "could not create menu (invalid template)"
		self.handle= hMenu
		TrackHandler.Register('menus', self.handle)
		Popup.__init__(self, self.handle)
		self._client_hwndParent = None


"""************************************************



************************************************"""
class  ContextMenu(object):
	def __init__(self):
		self._client_pWndProc= WNDPROC(self.onMESSAGE)
		self._client_pOldWndProc= 0

	
	def _client_Subclass(self, hwnd, restore=False):
		if restore:
			oldProc= user32.SetWindowLongA(hwnd, -4, self._client_pOldWndProc)
			if not oldProc:
				raise RuntimeError("could not restore window proc")
			self._client_pOldWndProc= 0
		else:
			self._client_pOldWndProc= user32.SetWindowLongA(hwnd, -4, self._client_pWndProc)
			if not self._client_pOldWndProc:
				raise RuntimeError("could not subclass window")
	

	
	def Popup(self, Window, Popup, x, y, *flags):
		if self._client_pOldWndProc: return		## block here
		
		flag = 0
		if flags:
			tpm_flags = {'rightbutton':2,'center':4,'right':8,'vcenter':16,
			'bottom':32,'nonotify':128,'returncmd':256,'subclass':0}
			for i in flags:
				try: flag |= tpm_flags[i]
				except: raise ValueError("invalid flag: %s" % i)
		if isinstance(Popup, (int, long)):
			handle = Popup
		else: handle = Popup.handle
		if 'subclass' in flags:
			self._client_Subclass(Window.Hwnd, restore=False)
			
		result = user32.TrackPopupMenuEx(handle, flag, x, y, Window.Hwnd, None)
		if 'subclass' in flags:
			self._client_Subclass(Window.Hwnd, restore=True)
		if result: return result


 	
	
	def onMESSAGE(self, hwnd, msg, wp, lp):
		if msg==278: # WM_INITMENU
			self.onMSG(hwnd, "menu open", wp, 0)
			return 1

			
		elif msg==279:		# WM_INITMENUPOPUP
			if HIWORD(lp):	# system menu
				pass
			else:					# menu
				self.onMSG(hwnd, "menu popup", wp, 0)
				return 1
		
							
		
		return user32.CallWindowProcA(self._client_pOldWndProc, hwnd, msg, wp, lp)
		
	
	def onMSG(self, hwnd, msg, wp, lp):
		pass
			

			
		
		