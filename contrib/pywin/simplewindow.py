"""simple, featureless window"""

from ctypes.wintypes import *

user32 = windll.user32
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
WS_SYSMENU         = 524288

WM_DESTROY = 2
COLOR_WINDOW              = 5

WNDPROC = WINFUNCTYPE(c_int, HANDLE, c_uint, WPARAM, LPARAM)

class WNDCLASS(Structure):
	_fields_ = [("style", c_uint),
					("lpfnWndProc", WNDPROC),
					("cbClsExtra", c_int),
					("cbWndExtra", c_int),
					("hInstance", HANDLE),
					("hIcon", HANDLE),
					("hCursor", HANDLE),
					("hbrBackground", HANDLE),
					("lpszMenuName", LPSTR),
					("lpszClassName", LPSTR)]


#********************************************************************
#********************************************************************

class Window(object):
		
	def __init__(self, title="", x=100, y=100, w=100, h=100):
				
		self.pWndProc= WNDPROC(self.WndProc)
				
		wc = WNDCLASS()
		wc.lpfnWndProc = self.pWndProc
		wc.lpszClassName =  "test-class"
		wc.hbrBackground= COLOR_WINDOW
		atom= user32.RegisterClassA(byref(wc))
		if not atom:
			raise "could not register window classs"
		
		self.hwnd = user32.CreateWindowExA(0, "test-class", "", WS_SYSMENU, x, y, w, h, 0, 0, 0, 0)
		if not self.hwnd: 
			raise "could not create window" 
		
	
	def run(self, show=0): 
		user32.ShowWindow(self.hwnd, show)
		GM, DM=user32.GetMessageA, user32.DispatchMessageA
		msg= MSG()
		pMsg =  byref(msg)
		while GM( pMsg, 0, 0, 0) > 0:
			DM(pMsg)
		

	def WndProc(self, hwnd, msg, wp, lp):
		if msg == WM_DESTROY:
			user32.PostQuitMessage(0)
			return 0
		return user32.DefWindowProcA(hwnd, msg, wp, lp)


#********************************************************************
#********************************************************************

if __name__=='__main__':
	w= Window()
	w.run(1)

