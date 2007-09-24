
from wnd.wintypes import (user32, LOWORD, HIWORD, 
													LOBYTE, HIBYTE, c_char_p, 
													WINFUNCTYPE, BOOL, HWND, 
													c_uint, WPARAM, LPARAM, 
													create_string_buffer) 
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

DIALOGPROC = WINFUNCTYPE(BOOL, HWND, c_uint, WPARAM, LPARAM)

def DWORD_TOBYTES(dw):	
	return WORD_TOBYTES(LOWORD(dw)) + WORD_TOBYTES(HIWORD(dw))

def WORD_TOBYTES(w): return LOBYTE(w), HIBYTE(w)

def SZ_TOWBYTES(s):
	out= []
	for i in s: out += (ord(i), 0)
	out += (0, 0)
	return out

WM_INITDIALOG       = 272

WS_CHILD           = 1073741824
DS_SETFONT       = 64
WS_VISIBLE = 268435456

WM_INITDIALOG       = 272
WM_CLOSE  = 16