

from wnd.wintypes import (user32, 
													shell32, 
													Structure, 
													c_uint,
													c_ulong,
													c_char, 
													sizeof,
													byref)
from wnd import fwtypes as fw
import atexit
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::	

class TrayIcon(object):
	def __init__(self, Window):
		self.ids= []
		atexit.register(self.Close)
		self.HwndParent= Window.Hwnd
		

	def Foo(self):
		print 'foo------------------------'
	
	def RegisterTrayIcon(self, ID, Icon, tooltip=None):
		if ID in self.ids:
			raise ValueError("ID is alreaddy registered: %s" % ID)
		if not fw.WND_WM_TRAY:
			result= user32.RegisterWindowMessageA(fw.WND_SZ_TRAY_MSG)
			if result: fw.WND_WM_TRAY= result
			else: raise RuntimeError("could not register tray message")
		ni=NOTIFYICONDATA()
		ni.hWnd=self.HwndParent
		ni.uID=ID
		ni.uFlags=1|2	# NIF_MESSAGE|NIF_ICON
		if tooltip:
			ni.uFlags |= 4	# NIF_TIP
			ni.szTip = tooltip[:63]
		ni.uCallbackMessage= fw.WND_WM_TRAY
		ni.hIcon=Icon.handle
		if not shell32.Shell_NotifyIcon(0, byref(ni)):		# NIM_ADD
			raise RuntimeError("could not register tray icon")
		self.ids.append(ID)
   
	
	def SetTrayIconTooltip(self, ID, tooltip):
		ni=NOTIFYICONDATA()
		ni.hWnd=self.HwndParent
		ni.uID=ID
		ni.uFlags =4			# NIF_TIP
		ni.szTip = tooltip[:63]
		if not shell32.Shell_NotifyIcon(1, byref(ni)):		# NIM_MODIFY
			raise RuntimeError("could not set tray icon tooltip")
		
	def SetTrayIconIcon(self, ID, Icon):
		ni=NOTIFYICONDATA()
		ni.hWnd=self.HwndParent
		ni.uFlags= 2		# NIF_ICON 
		ni.hIcon=Icon.handle
		ni.szTip = tooltip[:63]
		if not shell32.Shell_NotifyIcon(1, byref(ni)):		# NIM_MODIFY
			raise RuntimeError("could not set  tray icon icon")
		
	def UnregisterTrayIcon(self, ID):
		ni=NOTIFYICONDATA()
		ni.hWnd=self.HwndParent
		ni.uID=ID
		try: self.ids.remove(ID)
		except: 
			# error here ??
			pass
		if not shell32.Shell_NotifyIcon(2, byref(ni)):		# NIM_DELETE
			raise RuntimeError("could not unregister tray icon")

	def Close(self):
		ni=NOTIFYICONDATA()
		ni.hWnd=self.HwndParent
		error= []
		for i in self.ids:
			ni.uID= i
			if not shell32.Shell_NotifyIcon(2, byref(ni)):		# NIM_DELETE
				error.append(i)
		
		if error:
			raise RuntimeError("could not unregister tray icon(s): id(%s)" % ', '.join(map(str, error)))




class NOTIFYICONDATA(Structure):
	_fields_ = [("cbSize", c_ulong),
					("hWnd", c_ulong),
					("uID", c_uint),
					("uFlags", c_uint),
					("uCallbackMessage", c_uint),
					("hIcon", c_ulong),
					("szTip", c_char*64)]
	def __init__(self): self.cbSize=sizeof(self)	
		

