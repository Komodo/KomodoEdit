"""


TODO
	
	EnumResNames returns the identifyers of resources not their names
	for default resources so you can not use it in calls to functions 
	
"""


from api.wintypes import *

kernel32 = windll.kernel32

#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

ENUMRESTYPEPROC= WINFUNCTYPE(
							BOOL,
							HANDLE,
							c_void_p,	# may be c_uint or c_char_p...
							LONG)
ENUMRESNAMEPROC= WINFUNCTYPE(
							BOOL,
							HANDLE,
							c_void_p,	# ...same here
							c_void_p,	# ...same here
							LONG)

RT_TYPES= {
			'cursor' : 1,
			'bitmap' : 2,
			'icon' : 3,
			'menu' : 4,
			'dialog' : 5,
			'string' : 6,
			'fontdir' : 7,
			'font' : 8,
			'accelerator' : 9,
			'rcdata' : 10,
			'messagetable' : 11,
			'group_cursor' : 12,
			'group_icon' : 14,
			'version' : 16,
			'dlginclude' : 17,
			'plugplay' : 19,
			'vxd' : 20,
			'anicursor' : 21,
			'aniicon' : 22,
			'html' : 23,
			'manifest' : 24}

#***************************************************

class Resources(object):
	
	def __init__(self, module):
		
		if isinstance(module, (int, long)): self.hModule= module
		else: self.hModule = module._handle
		
		self.out = None
		self._p_enumrestypes = ENUMRESTYPEPROC(self._ResTypesProc)
		self._p_enumresnames = ENUMRESNAMEPROC(self._ResNameProc)
				
		self.restypes = [		# ... 0-24
					None, 'cursor','bitmap','icon','menu',
					'dialog','string','fontdir','font',
					'accelerator','rcdata','messagetable','group_cursor',
					None,'group_icon',None, 'version',
					'dlginclude',None,'plugandplay','vxd',
					'anicursor','aniicon','html',	'manifest']
							
	def _ResTypesProc(self, hModule, lpszType, lparam):
		if HIWORD(lpszType):
				self.out.append(c_char_p(lpszType).value.lower())
		else:
			self.out.append(self.restypes[lpszType])
		return 1
		
	def _ResNameProc(self, hModule, lpszType, lpszName, lParam):
		if HIWORD(lpszName):
			self.out.append(c_char_p(lpszName))
		else:
			self.out.append(lpszName)
		return 1

	
	def Walk(self):
		"""Returns an iterator over all resource names in a
		module, Return value is a list [resType, [resNames]]
		for each resource in turn."""
		for i in self.ListTypes():
			yield [i, self.ListNames(i)]
		
	
	def ListTypes(self):
		"""Returns a list of all defined resource names."""
		self.out = []
		if not kernel32.EnumResourceTypesA(self.hModule, self._p_enumrestypes, 0):
			raise "could not enum restypes"
		result = self.out
		self.out = None
		return result

		
	
	def ListNames(self, resType):
		try: 
			r = self.restypes.index(resType)
			if r !=None:
				resType = r
		except: pass
		self.out = []
		if not kernel32.EnumResourceNamesA(self.hModule, resType, ENUMRESNAMEPROC(self._ResNameProc), 0):
			raise "resource type not found"
		result = self.out
		self.out = None
		return result

	
	#def FindResource(self, resType, resName):
	#	try: 
	#		r = self.restypes.index(resType)
	#		if r !=None:
	#			resType = r
	#	except: pass
	#	hRes= kernel32.FindResourceA(self.hModule, resName, resType)
	#	if not hRes: raise "could not locate resource"
	#	handle= kernel32.LoadResource(self.hModule, hRes)
	#	if not handle: raise "could not locate resource"
	#	return handle


#def LoadResource(self, resType. resName):
#	self.hModule
#	pass
	
	#def findresource(self, resType, name):
	#	if not kernel32.FindResourceA(self.hModule, resType, name):
	#		raise 'cold not locate resource'
	#	pass




#**************************************************
#r = Resources(windll.shell32)


#r = Resources(windll.comctl32)
#avail= r.ListNames('icon')

#if 'cursor' in avail:



