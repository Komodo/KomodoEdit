


# NOT USED OR DOCOMENTED CURRENTLY






from wnd.wintypes import *
from api import winos
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
def getshelliconcache():
	"""getshelliconcache returns the two imagelists the shell uses
	for its icon display. 
	Return value is a tuple (imaglist large, imagelist small), two
	initialized imagelists.
	Note: 
	on win9x systems the imagelists are actually copies of the shells
	icon	cache, so freeing their handles will not do any harm to the
	system. 
	"""		
			
	GPA = windll.KERNEL32.GetProcAddress
	osname = winos.Name()
	isNT = False
	if osname not in ('win3.1', 'win95', 'win98'):
		# NT systems we have to call IconInit first
		isNT = True
		GPA.restype = WINFUNCTYPE(BOOL, BOOL) 
		IconInit = GPA(shell32._handle, 660)
		if IconInit:
			IconInit(1)
				
	GPA.restype = WINFUNCTYPE(INT, POINTER(HANDLE), POINTER(HANDLE))
	shell_GetImageLists = GPA(shell32._handle, 71) 
	if not shell_GetImageLists:
		raise 'retrieving function shell_GetImageLists failed'
		
	small = HANDLE()
	large = HANDLE()
	if not shell_GetImageLists(byref(large), byref(small)):
		raise 'could not retrieve shell icon caches'
	
	# To make it easier for the framework if the system is win9x we
	# make a copy if the imagelists 
	large = large.value
	small = small.value
	if not isNT:
		large  = comctl32.ImageList_Duplicate(large)
		small  = comctl32.ImageList_Duplicate(small)
	
	if not (large and small):
		raise 'could not retrieve shell icon caches'
	return (imagelistfromhandle(large),
				imagelistfromhandle(small))


def GetShellIconCache():
	"""Returns the handles to the shells icon cache as
	tuple(small-icons, large-icons). 
	
	Note:
	(win98 only)
	When using this icon cache with listviews make shure
	LVS_SHAREIMAGELISTS style is set, otherwise the system
	losses its icon cache when the listview is destroyed. The
	frameworks imagelists	set this style by default.
	
	"""		
	GPA = windll.KERNEL32.GetProcAddress
	osname = winos.Name()
	
	isNT = False
	if osname not in ('win3.1', 'win95', 'win98'):
		# NT systems we have to call IconInit first
		GPA.restype = WINFUNCTYPE(BOOL, BOOL) 
		IconInit = GPA(shell32._handle, 660)
		if IconInit:
			IconInit(1)
				
	GPA.restype = WINFUNCTYPE(INT, POINTER(HANDLE), POINTER(HANDLE))
	shell_GetImageLists = GPA(shell32._handle, 71) 
	if not shell_GetImageLists:
		raise 'retrieving shell_GetImageLists failed'
		
	small = HANDLE()
	large = HANDLE()
	if not shell_GetImageLists(byref(large), byref(small)):
		raise 'could not retrieve imagelist'
	return  small.value, large.value
		

