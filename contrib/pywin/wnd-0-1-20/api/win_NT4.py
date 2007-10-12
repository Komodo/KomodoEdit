
"""NT4 specific methods, psapi.dll EnumProcesses and stuff here"""

from wnd.wintypes import *
#***************************************************

class platformspecific(object):
	"""Currently a dummy class"""
	ENUM_FINDFIRST = 1
	ENUM_EXCLUDEHIDDEN = 2
	
	def __init__(self): pass

	def processlist(self): return 'not implemented'
	def threadlist(self): return 'not implemented'
	def caption(self, hwnd): return 'not implemented'
	def threadwindows(self, hwnd, *flags): return 'not implemented'
	def exefilepath(self, hwnd): return 'not implemented'
	def exefilename(self, hwnd): return 'not implemented'
	def handle(self, caption): return 'not implemented'