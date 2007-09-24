

from wnd.wintypes import *
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

MB_RETCODES = {
	1 : 'ok',
	2 : 'cancel',
	3 : 'abort',
	4 : 'retry',
	5 : 'ignore',
	6 : 'yes',
	7 : 'no'}

MB_FLAGS ={
		'appmodal' : 0,
		'defbutton1' : 0,
		'ok' : 0,
		'okcancel' : 1,
		'abortretryignore' : 2,
		'yesnocancel' : 3,
		'yesno' : 4,
		'retrycancel' : 5,
		'canceltrycontinue' : 6,
		'iconerror' : 16,
		'iconhand' : 16,
		'iconstop' : 16,
		'iconquestion' : 32,
		'iconexclamation' : 48,
		'iconwarning' : 48,
		'iconasterisk' : 64,
		'iconinformation' : 64,
		'usericon' : 128,
		'defbutton2' : 256,
		'defbutton3' : 512,
		'defbutton4' : 768,
		'systemmodal' : 4096,
		'taskmodal' : 8192,
		'help' : 16384,
		'nofocus' : 32768,
		'setforeground' : 65536,
		'default_desktop_only' : 131072,
		'topmost' : 262144,
		'right' : 524288,
		'rtlreading' : 1048576}

#********************************************************************

def Msg(hwnd, message, title, *styles):
	if not hwnd: hwnd=0
	if not isinstance(hwnd, (int, long)):
		raise ValueError, "eror arg1, hwnd required, found type:" % type(hwnd)
	style= 0
	for i in styles:
		try: style |= MB_FLAGS[i]
		except: raise "invalid style: %s" % i
	try:
		return MB_RETCODES[user32.MessageBoxA(hwnd, message, title, style)]
	except: return 'unknown'

#r=Msg(None, 'hello', 'foo', 'yesnocancel', 'systemmodal', 'setforeground', 'iconhand')

