"""Module for keeping track of api handles.
Any class depending on a handle can register its handle here.
The api_handles class keeps track of them and closes all
outstanding handles in its atexit handler.
"""



import atexit
from ctypes import windll

user32= windll.user32
gdi32= windll.gdi32

0#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
__all__ = ["TrackHandler", ]


class _TrackHandler(object):
	
	def __init__(self):
		self.handles = {	'fonts' : [], 'pens' : [], 'brushes' : [], 
		'regions' : [], 	'bitmaps' : [], 'icons' : [], 'cursors' : [],
		'dcs' : []}
		self.errors = self.handles.copy()
	
	
	def IsRegistered(self, type_handle, handle):
		"""Returns True if the handle is registered in the cathegory,
		False otherwise."""
		if self.handles:
			try: 
				self.handles[type_handle].index(handle)
				return True
			except: pass
		return False
		
	def Register(self, type_handle, handle):
		"""Register a handle by category."""
		if self.handles:
			try: self.handles[type_handle].append(handle)
			except: raise KeyError("invalid cathegory: %s" % type_handle)
	
	def Unregister(self, type_handle, handle):
		"""Removes a handle from the tracking list without
		closing it. Fom now on the caller is responsible for
		freeing the handle."""
		try:self.handles[type_handle].remove(handle)
		except:	raise ValueError("no handle found to unregister")
		
	def GetOpen(self):
		"""Returns the dict containing all currently open handles.
		Note:
		All these handles will be closed when the process exits,
		according to the limitations of the atexit module.
		But it could be usefull to check this list from time to time to see
		if if there are handles piling up somewhere."""
		return self.handles
	
	def Close(self):
		"""Close all handles. This is done automatically at exit."""
		DELETEOBJECT = gdi32.DeleteObject
		DESTROYCURSOR = user32.DestroyCursor
		DESTROYICON =  user32.DestroyIcon
		DELETEDC = gdi32.DeleteDC
		#RELEASEDC = user32.ReleaseDC
		flag = False
		for type_handle, handlelist in self.handles.items():
			if type_handle == 'cursors':
				for i in handlelist:
					if not DESTROYCURSOR(i):
						self.errors[type_handle].append(i)
						flag = True
			elif type_handle == 'icons':
				for i in handlelist:
					if not DESTROYICON(i):
						self.errors[type_handle].append(i)
						flag = True
			elif type_handle == 'dcs':
				for i in handlelist:
					if not DELETEDC(i):
						self.errors[type_handle].append(i)
						flag = True
			#elif type_handle == 'dcsfromwindows':
			#	for i in handlelist:
			#		if not RELEASEDC(i):
			#			self.errors[type_handle].append(i)
			#			flag = True
			else:
				for i in handlelist:
					if not DELETEOBJECT(i):
						self.errors[type_handle].append(i)
						flag = True
				
					
		self.handles =None
		if flag:
			raise RuntimeError("could not close handles: %s" % self.errors)

TrackHandler = _TrackHandler()
atexit.register(TrackHandler.Close)

# for export
GetOpenHandles = TrackHandler.GetOpen

			