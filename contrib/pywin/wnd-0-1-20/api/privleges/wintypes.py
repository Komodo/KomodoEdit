from ctypes.wintypes import (Structure, windll, sizeof, byref, DWORD, c_longlong, c_ulong, WinError, GetLastError, create_string_buffer, c_uint) 

advapi32= windll.advapi32
kernel32= windll.kernel32
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::


LUID= c_longlong

class LUID_AND_ATTRIBUTES(Structure):
	_pack_= 2
	_fields_ = [("Luid", LUID),
					("Attributes", DWORD)]

def setupTOKEN_PRIVILEGES(n):
	class TOKEN_PRIVILEGES(Structure):
		#_pack_= 2
		_fields_ = [("PrivilegeCount", DWORD),
						("Privileges", LUID_AND_ATTRIBUTES*n)]	# var length aray
	return TOKEN_PRIVILEGES


class TOKEN_STATISTICS(Structure):
	_fields_ = [("TokenId", LUID),
					("AuthenticationId", LUID),
					("ExpirationTime", c_longlong),
					("TokenType", c_uint),	##
					("ImpersonationLevel", c_uint),	##
					("DynamicCharged", DWORD),
					("DynamicAvailable", DWORD),
					("GroupCount", DWORD),
					("PrivilegeCount", DWORD),
					("ModifiedId", LUID)]


PRIVELGES= ('SeShutdownPrivilege', 
'SeCreateTokenPrivilege',
'SeAssignPrimaryTokenPrivilege',
'SeLockMemoryPrivilege',
'SeIncreaseQuotaPrivilege',
'SeUnsolicitedInputPrivilege',
'SeMachineAccountPrivilege',
'SeTcbPrivilege',
'SeSecurityPrivilege',
'SeTakeOwnershipPrivilege',
'SeLoadDriverPrivilege',
'SeSystemProfilePrivilege',
'SeSystemtimePrivilege',
'SeProfileSingleProcessPrivilege',
'SeIncreaseBasePriorityPrivilege',
'SeCreatePagefilePrivilege',
'SeCreatePermanentPrivilege',
'SeBackupPrivilege',
'SeRestorePrivilege',
'SeShutdownPrivilege',
'SeDebugPrivilege',
'SeAuditPrivilege',
'SeSystemEnvironmentPrivilege',
'SeChangeNotifyPrivilege',
'SeRemoteShutdownPrivilege'
)

