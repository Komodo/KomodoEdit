
from wnd.wintypes import (COPYDATASTRUCT,
												WNDPROC,
												user32,
												sizeof,
												addressof,
												byref,
												c_char,
												c_int,
												c_long,
												c_ulong,
												LOWORD,
												HIWORD,
												WINFUNCTYPE,
												create_string_buffer)

from wnd import fwtypes as fw
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
WM_COPYDATA = 74
ENUMWINDOWSPROC = WINFUNCTYPE(c_int, c_ulong, c_long)

#*********************************************************************************
#*********************************************************************************
class CopyData(object):

	def __init__(self):
		self._pWndProc = WNDPROC(self._WndProc)
		self._pOldWndProc = 0
		self._pEnumWindowsProc = ENUMWINDOWSPROC(self._EnumWindowsProc)
		self._dwResult = c_ulong()
		
		self._tmp_result = None
		self._tmp_GUID = None
		self._tmp_hwnd = 0
		

	# CopyData helper methods -------------------------------------------------------------

	def _EnumWindowsProc(self, hwnd, lp):
		if self._tmp_result: 
			return 0	# break the loop
		
		queryGUID = False
		if hwnd != self._tmp_hwnd:
		
			if lp == 0:	# main windows
				## query if the window is a framework window
				result = user32.SendMessageTimeoutA(
																	hwnd, 
																	fw.WND_WM_NOTIFY,
																	fw.WND_NM_ISFWWINDOW,
																	self._tmp_hwnd,
																	2,			# SMTO_ABORTIFHUNG
																	5,		# nTimeout
																	byref(self._dwResult))
				if result:
					if self._dwResult.value == fw.WND_MSGRESULT_TRUE:
						queryGUID = True
						
			elif lp== 1:		# child windows
				queryGUID = True
				
			if queryGUID:
				# query window for its GUID
				user32.SendMessageTimeoutA(
																		hwnd, 
																		fw.WND_WM_NOTIFY,
																		fw.WND_NM_GETGUID,
																		self._tmp_hwnd,
																		2,			# SMTO_ABORTIFHUNG
																		5,		# nTimeout
																		byref(self._dwResult))
												
				if not self._tmp_result:
					## not result yet... enum childwindows all the way down
					user32.EnumChildWindows(hwnd, self._pEnumWindowsProc, 1)
		
		return 1
			
			
	def _WndProc(self, hwnd, msg, wp, lp):
		
		if msg== WM_COPYDATA:
			if not self._tmp_result:
				result= fw.HandleCopyData(hwnd, msg, wp, lp)
				if result:
					if HIWORD(result[0]):
						if LOWORD(result[0])==fw.WND_CD_GUID:
							if result[1]==self._tmp_GUID:
								self._tmp_result= wp
								return 1
		return user32.CallWindowProcA(self._pOldWndProc, hwnd, msg, wp, lp)
		
	
	# CopyData methods ----------------------------------------------------------------	
	
	def FindGUID(self, hwnd, GUID):
		self._tmp_hwnd = hwnd
		self._tmp_GUID = GUID
		self._tmp_result = None
		
		## subclass the window to catch WM_COPYDATA in response to our query
		self._pOldWndProc= user32.SetWindowLongA(hwnd, -4, self._pWndProc)
		if not self._pOldWndProc:
			raise RuntimeError, "could not subclass window"
				
		user32.EnumWindows(self._pEnumWindowsProc, 0)

		# restore old proc
		user32.SetWindowLongA(hwnd, -4, self._pOldWndProc)
		return self._tmp_result
		
	
	def CopyData(self, hwndSource, hwndDest, lp, data, noprefix=False):
		## TODO
		## what if the window is hung ??
		## can not use timeout here, noone knows how long it will take 
		## for the window to process the message 
		if noprefix:
			p= create_string_buffer(data)
		else:
			if lp > 0xffff:
				raise ValueError, "lp must be <= 0xFFFF"
			p= create_string_buffer(fw.SZ_GUID_COPYDATA + data)
		## do not include NULL byte in cbData
		cd= COPYDATASTRUCT(lp, sizeof(p) -1, addressof(p))
		return bool(user32.SendMessageA(hwndDest, WM_COPYDATA, hwndSource, byref(cd)))





