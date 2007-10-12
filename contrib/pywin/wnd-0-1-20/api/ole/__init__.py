
from ctypes.com import ole32

ole32.OleInitialize(None)

class _Cleaner(object):
	def	__del__(self, func=ole32.OleUninitialize):
		try: func()
		except WindowsError: pass

__cleaner =	_Cleaner()
del	_Cleaner
