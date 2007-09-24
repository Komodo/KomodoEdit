"""
TODO

	- GetTokenStats is not documented


"""



from wnd.api.privleges.wintypes import *
#**********************************************************************************

__all__= []

def _AdjustPrivleges(hProcess, fEnable, *privleges):
	if not hProcess: hProcess= kernel32.GetCurrentProcess()
	hToken= c_ulong()
	if not advapi32.OpenProcessToken(hProcess,
																	32, # TOKEN_ADJUST_PRIVILEGES
																	byref(hToken)):
		raise WinError(GetLastError())
	
	try:
		luid= LUID()
		attrs= []
		for i in privleges:
			if not advapi32.LookupPrivilegeValueA(None, i, byref(luid)):
				raise WinError(GetLastError())
			attrs.append(LUID_AND_ATTRIBUTES(luid.value, fEnable and 2 or 0))	# 2= SE_PRIVILEGE_ENABLED
		
		if attrs:
			tp= setupTOKEN_PRIVILEGES(len(attrs))()
			tp.PrivilegeCount= len(attrs)
			tp.Privileges= (LUID_AND_ATTRIBUTES*len(attrs))(*attrs)
			if not advapi32.AdjustTokenPrivileges(hToken,
																	0,						# fDisableAll
																	byref(tp),
																	sizeof(tp),
																	None,				# prev state priveleges
																	None				# sizeof prevState
																	):
				raise WinError(GetLastError())
	finally: 
		kernel32.CloseHandle(hToken)


def _StatToken(hToken):
	ts= TOKEN_STATISTICS()
	cbNeeded= DWORD()
	#TokenStatistics         = 10
	if not advapi32.GetTokenInformation(hToken, 10, byref(ts), sizeof(ts), byref(cbNeeded)):
		raise WinError(GetLastError())
	return ts

def _GetPrivleges(hProcess):
	if not hProcess: hProcess= kernel32.GetCurrentProcess()
	hToken= c_ulong()
	if not advapi32.OpenProcessToken(hProcess,
																	8,		# TOKEN_QUERY
																	byref(hToken)):
		raise WinError(GetLastError())
	try:
		stat= _StatToken(hToken)
		tp= setupTOKEN_PRIVILEGES(stat.PrivilegeCount)()
		cbNeeded= DWORD()
		if not advapi32.GetTokenInformation(hToken, 3, byref(tp), sizeof(tp), byref(cbNeeded)):
			raise WinError(GetLastError())
	finally:
		kernel32.CloseHandle(hToken)
	return tp.Privileges


def _TranslatePrivlegeAttrs(attr):
	out= []
	if attr & 1==1:	#SE_PRIVILEGE_ENABLED_BY_DEFAULT
		out.append('enabled_by_default')
	if attr & 2==2:	# 	SE_PRIVILEGE_ENABLED
		out.append('enabled')
	#if attr & 2147483648==2147483648:	# SE_PRIVILEGE_USED_FOR_ACCESS
	#	out.append('used_for_access')
	return out

#********************************************************************************	
#********************************************************************************	
def EnablePrivleges(hProcess, *privleges, **kwargs):
	return _AdjustPrivleges(hProcess, True, *privleges)
	
def DisablePrivleges(*privleges, **kwargs):
	return _AdjustPrivleges(kwargs.get('hProcess'), False, *privleges)


__all__.append("EnablePrivleges")
__all__.append("DisablePrivleges")

def GetPrivlegeInfo(hProcess, privlege):
	out= []
	luid= LUID()
	if not advapi32.LookupPrivilegeValueA(kwargs.get('hProcess'), privlege, byref(luid)):
				raise WinError(GetLastError())
	
	priv= _GetPrivleges(hProcess)
	for i in priv:
		if i.Luid==luid.value:
			out= _TranslatePrivlegeAttrs(i.Attributes)
			break
	return out
	
__all__.append("GetPrivlegeInfo")

def EnumPrivleges(hProcess):
	priv= _GetPrivleges(hProcess)
	p= create_string_buffer(256)
	cbName= DWORD()
	for i in priv:
		# cbName holds the buffer size [in] and the required buffer size [out]
		cbName.value= sizeof(p)
		advapi32.LookupPrivilegeNameA(None, byref(LUID(i.Luid)), p, byref(cbName))
		if cbName.value > sizeof(p)-1:
			p= create_string_buffer(cbName.value +1)
			if not advapi32.LookupPrivilegeNameA(None, byref(LUID(i.Luid)), p, byref(cbName)):
				raise WinError(GetLastError())
		yield p.value, _TranslatePrivlegeAttrs(i.Attributes)


__all__.append("EnumPrivleges")



## not documented	 ######################################
def GetTokenStats(hProcess):
	hToken= c_ulong()
	TOKEN_QUERY             = 8
			
	if not hProcess: hProcess= kernel32.GetCurrentProcess()
	if advapi32.OpenProcessToken(hProcess, TOKEN_QUERY, byref(hToken)):
		try:
			result= _StatToken(hToken.value)
		finally:
			kernel32.CloseHandle(hToken.value)
	else:
		raise RuntimeError, "could not oopen token"
	return result
			
__all__.append("GetTokenStats")

#*****************************************************************************

def test():
	for i in EnumPrivleges(None):
		print i
	
	EnablePrivleges(None, 'SeShutdownPrivilege')
	r= GetPrivlegeInfo(None, 'SeShutdownPrivilege')
	print r
	DisablePrivleges(None, 'SeShutdownPrivilege')
	r= GetPrivlegeInfo(None, 'SeShutdownPrivilege')
	print r

#test()
