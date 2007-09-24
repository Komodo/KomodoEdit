"""


SHChangeNotifyUpdateEntryList
SHChangeNotifySuspendResume


TODO
	- register more then one pIdl to monitor at the same time
	- 'freespace' is not working as expected



Heading into undocumented stuff
instead of SHChangeNotify use some undocumented apis, to
receive change notifications more directly.

thanks to
undocumented windows95
http://www.geocities.com/SiliconValley/4942/index.html

typedef struct {
  LPCITEMIDLIST  pidlPath;			# array of pIdls to monitor
  BOOL           bWatchSubtree;		# 1 or 0 
} NOTIFYREGISTER;


exported by ordinal 2
HANDLE WINAPI SHChangeNotifyRegister(
    HWND   hWnd,										# window to notify
    DWORD  dwFlags,								# SHCNF_*
    LONG   wEventMask,							# SHCNE_*
    UINT   uMsg,											# message to send
	DWORD  cItems,									# nItems to monitor
	LPCNOTIFYREGISTER lpItems);		# NOTIFYREGISTER struct

exported by ordinal 4
BOOL WINAPI SHChangeNotifyUnregister(
     HANDLE hNotify);


NT systems need some special treatement
By default a proxy window is created, that handles a mem map passed
and returns with a pIld array. SHCNF_NO_PROXY prevents this
and returns the mem map directly. The two apis below handle the mem map.

exported by ordinal 644
HANDLE WINAPI SHChangeNotification_Lock(
	HANDLE  hMemoryMap,							# handle of the mem map
	DWORD   dwProcessId,							# the callers process ID
	LPCITEMIDLIST **lppidls,						# [out] pointer to PIDL array
	LPLONG  lpwEventId)								# [out] pointer to event ID

exported by ordinal 645
BOOL WINAPI SHChangeNotification_Unlock(
HANDLE hLock)
"""

import thread
from wnd.api.shell.wintypes import *
from wnd.api import winos, handles
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
class NOTIFYREGISTER(Structure):
	_fields_ = [("pidlPath", POINTER(ITEMIDLIST)),
					("bWatchSubtree", BOOL)]

GetProcAddress.restype= WINFUNCTYPE(c_ulong, c_ulong, c_ulong, c_long, c_uint, c_ulong, POINTER(NOTIFYREGISTER))
SHChangeNotifyRegister = GetProcAddress(shell32._handle, 2)
GetProcAddress.restype= WINFUNCTYPE(BOOL, c_ulong)
SHChangeNotifyUnregister = GetProcAddress(shell32._handle, 4)

WINOS_NAME = winos.Name()

if WINOS_NAME in ("NT", "NT4"):
	raise "ShellNotrify is not tested on NT systems"
	GetProcAddress.restype= WINFUNCTYPE(c_ulong, c_ulong, c_ulong, POINTER(POINTER(ITEMIDLIST)*2), POINTER(c_long))
	SHChangeNotification_Lock = GetProcAddress(shell32._handle, 644)
	GetProcAddress.restype=WINFUNCTYPE(BOOL, c_ulong)
	SHChangeNotification_Unlock = GetProcAddress(shell32._handle, 645)

SHN_FLAGS={
			'renameitem' : 1,
			'create' : 2,
			'delete' : 4,
			'mkdir' : 8,
			'rmdir' : 16,
			'mediainserted' : 32,
			'mediaremoved' : 64,
			'driveremoved' : 128,
			'driveadd' : 256,
			'netshare' : 512,
			'netunshare' : 1024,
			'attributes' : 2048,
			'updatedir' : 4096,
			'updateitem' : 8192,
			'serverdisconnect' : 16384,
			'updateimage' : 32768,
			'driveaddgui' : 65536,
			'renamefolder' : 131072,
			'freespace' : 262144}

#*********************************************************************
#*********************************************************************



class ShellNotify(object):
	def __init__(self, Window, message, callback):
				
		self.Hwnd = Window.Hwnd
		self.MsgCallback = callback
		self.Msg = message
		self.handle = 0

		
	# to register more then on pIdl use:
	#def RegisterEx(self, subtree=False, pIdls):
		#	arrPidl= (PIDL*len(pIdls))(*pIdls)
		#	nfr=NOTIFYREGISTER(arrPidl[0], subtree and 1 or 0)
		#	SHChangeNotifyRegister(self.Hwnd, 1|2|0x800, SHCNE_ALLEVENTS, self.Msg, len(pIdls), byref(nfr))
	
	
	def Register(self, pIdl, *flags):
		#SHCNF_ACCEPT_INTERRUPTS  =	1
		#SHCNF_ACCEPT_NON_INTERRUPTS= 	2
		#SHCNF_NO_PROXY =	0x8000		## NT systems only
		
		if not flags:
			flag= 2147483647 # SHCNE_ALLEVENTS
		else:
			flag= 0
			for i in flags:
				try: flag |= SHN_FLAGS[i]
				except: raise ValueError, "invalid flag: %s" % i
		if self.handle:	self.Close()
		nfr=NOTIFYREGISTER(pIdl, 0)	
		self.handle = SHChangeNotifyRegister(self.Hwnd, 1|2|0x800, flag, self.Msg, 1, byref(nfr))
		#print 'xxx', self.handle
		if not self.handle: raise RuntimeError("could not register shell notify")
							
	
	def Close(self):
		if self.handle:
			result = SHChangeNotifyUnregister(self.handle)
			self.handle = 0
			if not result: raise RuntimeError("could not unregister shell notify")
		else: raise RuntimeError("no pIdl registered")

	
	
	def _Notify(self, hwnd, evtID, arrPidl):
		
		try:
			if evtID==1:	#	SHCNE_RENAMEITEM
				if arrPidl[1]: pIdl2= arrPidl[1]
				else: pIdl2= None
				self.MsgCallback(hwnd, "shellnotify", "rename", (arrPidl[0], pIdl2))
			
			elif evtID==2: # SHCNE_CREATE
				self.MsgCallback(hwnd, "shellnotify", "create", arrPidl[0])
			
			elif evtID==4:	# SHCNE_DELETE
				if arrPidl[1]: pIdl2= arrPidl[1]
				else: pIdl2= None
				self.MsgCallback(hwnd, "shellnotify", "delete", (arrPidl[0], pIdl2))
			
			elif evtID==8: # SHCNE_MKDIR
				self.MsgCallback(hwnd, "shellnotify", "mkdir", arrPidl[0])
			
			elif evtID==16: # SHCNE_RMDIR
				if arrPidl[1]: pIdl2= arrPidl[1]
				else: pIdl2= None
				self.MsgCallback(hwnd, "shellnotify", "rmdir", (arrPidl[0], pIdl2))
			
			elif evtID==32: #SHCNE_MEDIAINSERTED
				self.MsgCallback(hwnd, "shellnotify", "mediainserted", arrPidl[0])
			
			elif evtID==64:  #SHCNE_MEDIAREMOVED
				self.MsgCallback(hwnd, "shellnotify", "mediaremoved", arrPidl[0])
					
			elif evtID==128:  #SHCNE_DRIVEREMOVED
				self.MsgCallback(hwnd, "shellnotify", "driveremoved", arrPidl[0])
						
			elif evtID==256: 	# SHCNE_DRIVEADD
				self.MsgCallback(hwnd, "shellnotify", "drivereadd", arrPidl[0])
				
			elif evtID==512:  #SHCNE_NETSHARE
				self.MsgCallback(hwnd, "shellnotify", "netshare", arrPidl[0])
					
			elif evtID==1024: 	#SHCNE_NETUNSHARE
				self.MsgCallback(hwnd, "shellnotify", "netunshare", arrPidl[0])
					
			elif evtID==2048: #SHCNE_ATTRIBUTES
				self.MsgCallback(hwnd, "shellnotify", "attributes", arrPidl[0])
					
			elif evtID==4096:	#SHCNE_UPDATEDIR
				self.MsgCallback(hwnd, "shellnotify", "updatedir", arrPidl[0])
					
			elif evtID==8192:  #SHCNE_UPDATEITEM
				self.MsgCallback(hwnd, "shellnotify", "updateitem", arrPidl[0])
						
			elif evtID==16384: 	#SCCNE_SERVERDISCONNECT
				self.MsgCallback(hwnd, "shellnotify", "serverdisconnect", arrPidl[0])
						
			elif evtID==131072: # SHCNE_RENAMEFOLDER 
				if arrPidl[1]: pIdl2= arrPidl[1]
				else: pIdl2= None
				self.MsgCallback(hwnd, "shellnotify", "renamefolder", (arrPidl[0], pIdl2))
					
			elif evtID==262144: #SHCNE_FREESPACE
				self.MsgCallback(hwnd, "shellnotify", "freespace", None)
				# could not get this one to work
				# docs claim its the pIdl of the drve, undocumented win95
				# its a DWORD following cb mapping, drive numbers (bit 1 set= drive A).
				# At least on XP none of these do work. 
				
		finally:
			Malloc.Free(arrPidl)
			

		# not implemented
		#elif lp==32768: lp="updateimage" #SHCNE_UPDATEIMAGE
		#elif lp==65536: lp="driveaddgui" #SHCNE_DRIVEADDGUI
		# and some dubious extended events 
		
	
	
	def HandleMessage(self, hwnd, msg, wp, lp):
		if WINOS_NAME in ("NT", "NT4"):	## not tested 
			# NT passes the handle to the mem map in wp and the processID as lp
			arrPidl = (PIDL*2)()
			evtID = c_long()
			hLock = SHChangeNotification_Lock(wp, lp, byref(arrPIDL), pointer(evtID))
			if hLock:
				try: self._Notify(hwnd, evtID.value, arrPidl)
				finally: SHChangeNotification_Unlock(hLock)
			else: raise RuntimeError("lock failed")
		else:
			# wp= (PIDL*2), lp= eventID
			arrPidl = (PIDL*2).from_address(int(wp)) 
			self._Notify(hwnd, lp, arrPidl)
			
				



SHCN_FLAGS= {
'filename':1,
'dirname':2,
'attributes':4,
'size':8,
'lastwrite':16,
'lastaccess':32,
'creation':64,
'security':256
}
WAIT_OBJECT_0 = 0

## REMARKS
## I must assume to have no (zero) experience in using threads..
## so any suggestions or remarks on the code are highly welcome

class ShellChangeNotification(object):
	def __init__(self):
		
		self.timeout= 200
		self.Hwnd= 0
		
		self.threads= {}
		self.Handles= handles.Handles()
		self.lock= thread.allocate_lock()
		
		
	
	def Register(self, path, *flags, **kwargs):
		
		self.Close()
				
		self.timeout= kwargs.get("timeout", self.timeout)
		self.Hwnd= kwargs.get("hwnd", self.Hwnd)
		
		if not flags:
			raise ValueError, "no flags specified"
		flag= 0
		for i in flags:
			try: flag |=SHCN_FLAGS[i]
			except: 
				raise "invalid flag: %s" % i
		
		handle= kernel32.FindFirstChangeNotificationA(path,
									kwargs.get("subtree", None) and 1 or 0, flag)
		if handle ==-1:	# INVALID_HANDLE_VALUE
			raise RuntimeError, "could nor register change notification"
		
		self._StartThread(handle)
				
				
	def Close(self):
		self.lock.acquire()
		for i in self.threads: 
			self.threads[i]= False
		self.lock.release()
	
	def _StartThread(self, notificationHandle):
		h= self.Handles.New()
		self.threads[h]= True
		thread.start_new_thread(self._MonitorChanges, (h, notificationHandle))
		
	def _IsThreadSignaled(self, handle):
		self.lock.acquire()
		result= not self.threads[handle]
		self.lock.release()
		return result
		
	def _CloseThread(self, handle):
		self.lock.acquire()
		self.Handles.Close(handle)
		del self.threads[handle]
		self.lock.release()
	
	
	def _MonitorChanges(self, handle, notificationHandle):
		
		while True:
			result= kernel32.WaitForSingleObject(notificationHandle, 500)
			if self._IsThreadSignaled(handle):
				self._CloseThread(handle)
				break
			
			if result==WAIT_OBJECT_0:
				
				while True:
					if kernel32.WaitForSingleObject(notificationHandle, self.timeout):
						break
					kernel32.FindNextChangeNotification(notificationHandle)
				self.onMSG(self.Hwnd, "shellchange", 0, 0)
						
		kernel32.FindCloseChangeNotification(notificationHandle)
			

						
		
	def onMSG(self, hwnd, msg, wp, lp):
		pass				
