

from wnd.wintypes import (user32,
													Structure,
													byref,
													BYTE,
													WORD)
from wnd import fwtypes as fw
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
class ACCEL(Structure):
			_fields_ = [("fVirt", BYTE),
							("key", WORD),
							("cmd", WORD)]


#**************************************************
#
#
#
#**************************************************
class AcceleratorTable(object):
	
	# Todo: kick out parent parameter
	def __init__(self, *accels):
		"""Creates an accelerator table.
		Each accelerator should be a tuple (ID, virtual-key, modifier1,
		modifier2, modifier3).
		Where ID is an integer ID (1 to 65,535) virtual-key one of the
		VK_* constants see -> consts.vk module for keycodes
		and modifiers can be a combination of 'shift', 'control', 'alt'.
				
		Accelerators pass te same messages as menus to the parent
		windows message handler. If the accelerator ID matches an
		ID of a menu item of the menu currently attatched to the
		window 'menu open' and 'menu popup' messages
		are send, else only 'menu choice' is send:
			
			'menu open'		as if the menu is about to open
									wp=handle of the menu displayed
									lp=always zero
			'menu popup'		as if a popup is about to open
									wp=handle of the popup displayed
									lp=allways zero
			'menu choice'		The accelerator the user triggered 
									wp=handle of the menu displayed
									lp=tuple(ID-menu-item, flag-accelerator)
										flag-accelerator is True if the message
										comes from an accelerator table,False
										otherwise.
									
		Sample code:
			accel=self.Init('AcceleratorTable', 
			(1001, vk.VK_1, 'control'),
			(1002, vk.VK_2, 'control', 'alt'),
			(1003, vk.VK_3, 'control', 'alt', 'shift')
			)
		
		Background note:
		The reason why we can not tell accelerator and menu
		commands appart is, there is no distinction between them
		in WM_INITMENU and WM_INITMENUPOPUP, while
		WM_COMMAND 'knows' the difference. Some good ID scheme
		is recommended to work with multiple menus and/or
		accelerator tables.
		"""
		modkeys = {'shift':4, 'control':8, 'alt':16}
		arrAccel = (ACCEL*len(accels))()
		for i, data in enumerate(accels):
			modkey = 1	# FVIRTKEY
			for n in data[2:]:
				try:
					modkey |= modkeys[n]
				except:
					raise ValueError("invalid modifier flag '%s'" % n)
			arrAccel[i] = ACCEL(modkey, data[1], data[0])
		self.handle = user32.CreateAcceleratorTableA(
											byref(arrAccel), i+1)
		
		if not self.handle:
			raise RuntimeError("could not create accelerator table")
		fw.TrackHandler.Register('acceleratortables', self.handle)
		self._client_hwndParent = None
					
	def Set(self, Window):
		"""Sets the accelerator table to the gui."""
		if self._client_hwndParent:
			raise RuntimeError("accelerator table alreaddy set")
		Window._base_hAccelerator = self.handle
		self._client_hwndParent = Window.Hwnd

	def Remove(self, Window):
		"""Removes the acceleratot table from the gui."""
		if not self._client_hwndParent:
			raise RuntimeError("accelerator table not set")
		Window._base_hAccelerator = 0
		self._client_hwndParent = None

	def Destroy(self):
		"""Destroys the accelerator table."""
		if self.handle:
			if self._client_hwndParent:
				mn= WND_MENU(self.handle, fw.MNUT_ACCEL, fw.MNUF_REMOVE)
				user32.SendMessageA(self._client_hwndParent, 
										fw.WND_WM_NOTIFY,
										fw.WND_NM_MENU,
										byref(nm))
			TrackHandler.Unregister('acceleratortables', self.handle)
			if not user32.DestroyAcceleratorTable(self.handle):
				raise RuntimeError("could not destroy accelerator table")
			self.handle = 0
			self._client_hwndParent = None


		