"""Framework entry... """

__version__= "0.1.20"


from wnd.wintypes import user32 as _user32
from wnd import fwtypes as _fw
from wnd.controls.window import Window
from wnd.controls.dialog import Dialog


WND_PATH= __file__[:__file__.rfind('\\')]
WND_RESPATH = '%s\\res' % WND_PATH
WND_LIBPATH= '%s\\libs' % WND_PATH 
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

def SetMaxError(n): _fw.WND_MAXERROR= n
def GetMaxError(n): return _fw.WND_MAXERROR
def GetErrorLevel(): return _fw.WND_ERRORLEVEL
def SetErrorLevel(n): _fw.WND_ERRORLEVEL= n
def DecreaseErrorLevel(): _fw.WND_ERRORLEVEL-= 1
	
def Debug(*cathegory):
	
	def PrintUser():
		print
		print 'OPEN USER HANDLES:---------------------------------'
		for i in _fw.TrackHandler.GetOpen().items():
			print i
		print
	
	def PrintGDI():
		from wnd.gdi.trackhandles import TrackHandler
		print 'OPEN GDI HANDLES:---------------------------------'
		for i in TrackHandler.GetOpen().items():
			print i
		print
	
	def PrintLeaks():
		import gc
		print 'LEAKS FOUND:---------------------------------'
		gc.set_debug(gc.DEBUG_LEAK)
		leaks = gc.collect()
		print '%s LEAKS"' % leaks
		print
	
	avail=(
	('user', PrintUser),
	('gdi', PrintGDI),
	('leaks', PrintLeaks)
	)
	
	if cathegory:
		for i in cathegory:
			flag= False
			for name, func in avail:
				if name==i: func()
				flag=True
			if not flag: raise ValueError, "invalid cathegory: %s" % i
	else:
		for name, func in avail: func()
	
	
def RegisterWindowMessage(name):
	msg = _user32.RegisterWindowMessageA(name)
	if not msg: raise RuntimeError, "could not register message"
	return msg


