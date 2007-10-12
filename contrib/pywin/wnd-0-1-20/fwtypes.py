"""framework defined types"""


from wnd.wintypes import (user32, 
												comctl32, 
												Structure,
												POINTER,
												addressof,
												byref,
												sizeof,
												memmove,
												UINT_MAX,
												NMHDR,
												HIWORD,
												LOWORD,
												c_ulong, 
												c_uint, 
												c_long,
												c_ushort,
												c_short,
												c_ubyte,
												c_char,
												c_void_p,
												create_string_buffer,
												MAKELONG,
												COPYDATASTRUCT) 

import sys, atexit
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

WND_GUIMAIN = False									## main window created True/False
WND_MSGRESULT_TRUE = 123456789
WND_MAX_CLASSNAME = 64
WND_N_TIMER_IDS = 10000							# counter
WND_ERRORLEVEL = 0									# counter
WND_MAXERROR = 0

# control id ranges
WND_ID_MDICHILD_MIN= 5000					# min/max IDs for MDI child windows
WND_ID_MDICHILD_MAX= 5999
WND_ID_CONTROL_MIN= WND_ID_MDICHILD_MAX	+1 # min ID for controls


# Shell_NotifyIcon message
WND_SZ_TRAY_MSG = "wnd_tray_msg{D1A29F00-F917-11D9-B552-00112FF53A26}"
WND_WM_TRAY = None								# RegisterWindowMessage(
																			#			WND_SZ_TRAY_MSG)
																			#			...done by TrayIcon class

# copy data
SZ_GUID_COPYDATA= "{88077500-F881-11D9-B552-00112FF53A26}"	 # cookie
WND_COPYDATA_MAXDATA = 10000000	# arbitrary
# message ids for WM_COPYDATA
WND_CD_GUID = 1


# wnd notify
SZ_WND_NOTIFY= "wnd_notify_msg{E4FB9FC0-F917-11D9-B552-00112FF53A26}"
WND_WM_NOTIFY = user32.RegisterWindowMessageA(SZ_WND_NOTIFY)
if not WND_WM_NOTIFY: raise "could not register notify message"

# notification codes (passed as wParam of the message)
WND_NM_APPCREATED = 1	# not used currently
WND_NM_MENU = 2					# lp= struct WND_MENU 
WND_NM_APPBAR = 3				# not used currently
WND_NM_MSGREFLECT = 4	# lp= struct WND_MSGREFLECT 
WND_NM_EXCEPTION = 5			# lp= struct WND_EXCEPTION 
WND_NM_DLGDISPATCH = 6	# lp= hwnd or 0 to clear
														# modeless dialogboxes should set and clear this
														# on creatinon/destruction to enable keyboard handling

WND_NM_ISMAINWINDOW = 7 # lp= 0. Returns WND_MSGRESULT_TRUE for
														#				mainwindows
WND_NM_ISFWWINDOW = 8		# lp= 0.  Returns WND_MSGRESULT_TRUE for framework
														#				windows or childwindows
WND_NM_GETGUID = 9				# lp= hwndReceiver. Will respond with a WM_COPYDATA
														#										to the receiver passing the GUID

class WND_MSGREFLECT(Structure):
	_fields_ = [("hwndFrom", c_ulong),	# who is reflecting
					("msg", c_uint),						# the message reflected	
					("wParam", c_uint),					# its wParam
					("lParam", c_long),					# its lParam
					("fReturn", c_ushort)]			# filled in by receiver -->
																		#				...True/False
																		# True: return the return value,
																		# False: continue processing

MNUT_MENU= 1
MNUT_ACCEL= 2
MNUF_REMOVE= 1
class WND_MENU(Structure):
	_fields_ = [("handle", c_ulong),		# handle menu/accelerator
						("type", c_ushort),			# MNUT_*
						("code", c_ushort)]			# what to do: MNUF_*
								

EXC_EXCEPTION= 1
EXC_FATAL= 2
EXC_MAXERROR= 3
class WND_EXCEPTION(Structure):
	_fields_= [("hwndFrom", c_ulong),		# who is sending
						("type", c_short)]					# EXC_*


# <- end wnd notify


#  framwork defined messages and styles
# so base classes should update their styles and messages from the classes below
WS_BASE_DEBUG = 1
WS_BASE_DEBUGALL = 2
WND_DEBUGMASK= 	WS_BASE_DEBUG | WS_BASE_DEBUGALL


class wnd_control_styles:
	prefix = ['WS_', 'WS_EX_', 'WS_BASE_', 'WS_CLIENT_']
	WS_BASE_DEBUG = WS_BASE_DEBUG
	WS_BASE_DEBUGALL = WS_BASE_DEBUGALL

	WS_BASE_SUBCLASS = 64		# used for controls only
		

class wnd_window_styles:
	prefix = ['WS_', 'WS_EX_', 'WS_BASE_', 'WS_CLIENT_']
	WS_BASE_DEBUG = WS_BASE_DEBUG
	WS_BASE_DEBUGALL = WS_BASE_DEBUGALL
		
	WS_BASE_MOVE = 16				# drag window by its client area 
															#### does not workk for dialogs	
	WS_BASE_DIALOGLIKE = 32	# enables dialoglike keyboard
															# handling. Can not be set
															# at runtime.

class wnd_window_msgs:
	WND_WM_NOTIFY= WND_WM_NOTIFY


"""************************************************************
 some exceptions
************************************************************"""
# raised only by a mainwindow when a childwindow signals an exception
class ChildwindowExit(Exception): pass


"""***********************************************************
small class returning the next ID for a child window
***********************************************************"""
class _ID(object):
	def __init__(self): 
		self.stack= []
		self.n= WND_ID_CONTROL_MIN
	
	def Recycle(self, ID):
		if ID not in self.stack:
			self.stack.append(ID)
		else: raise "could not recycle ID: %s" % ID
	
	def New(self):
		if self.stack:
			return self.stack.pop()
		self.n += 1
		return self.n

ID= _ID()


class Handles(object):
	def __init__(self, initval=0):
		import thread
		
		self.handles= [initval, ]
		self.lock= thread.allocate_lock()
		
	
	def Close(self, handle):
		self.lock.acquire()
		try:
			self.handles.remove(handle)
		except: 
			self.lock.release()
			raise ValueError, "no handle found to close"
		self.lock.release()
	
	def New(self):
		self.lock.acquire()
		result= None
		tmp_h= self.handles[:]
		s= len(self.handles)
		for n, i in enumerate(tmp_h):
			if n+1 < s:
				if self.handles[n+1] > i+1:
					self.handles.insert(n+1, i+1)
					result=  i+1
					break
						
			else:
				self.handles.append(i+1)
				result=  i+1
		
		self.lock.release()
		return result		



"""***************************************************************
 filter class for message loops to print out formated message strings

Init with the class containing the messages supported by the window
and the requested debug level

In th emessage loop pass the message and params to the hadleMesage
method. Return value is either None, if the debugger did not
 process the message or a tuple(msg, formated string) if so.

reflected messages are marked with a postfix "(re=hwndFrom)"
+ wp and lp point to the parameters of the reflected, not to the onse
of the reflecting message

***************************************************************"""
def GetDebugger(style, msgClass):
	if style & WND_DEBUGMASK:
			return Debugger(msgClass,	style & WND_DEBUGMASK)
		

class Debugger(object):
		
	def __init__(self, msgs, dbgmask):
		
		self.msg= "%s=%s, hwnd=%s, wp=%s, lp=%s" 
		self.remsg= "%s=%s, hwnd=%s, wp=%s, lp=%s    (re=%s)"
		# WM_NCHITTEST, WM_SETCURSOR, WM_MOUSEMOVE, WM_NCMOUSEMOVE
		self.msgFilter= 132, 32, 512, 160
					
		if dbgmask & WS_BASE_DEBUG: 
			pass
		elif dbgmask & WS_BASE_DEBUGALL:
			self.msgFilter= ()
		self.msgNames = msgs.__dict__.keys()
		self.msgValues = msgs.__dict__.values()
	
	
	def MsgName(self, msg):
		try: 
			return self.msgNames[self.msgValues.index(msg)]
		except: 
			return 'UNKNOWN MSG'
	
	def GetNm(self, lp):
		nm = NMHDR.from_address(lp)
		try:
			n = self.msgValues.index(nm.code)
			return self.msgNames[n], nm.code
		except:	
			return 'UNKNOWN MSG', nm.code
					
	
	def HandleMessage(self, hwnd, msg, wp, lp):
		
		if msg not in self.msgFilter:
			s, msgOut = None, msg
						
			if msg==78:	# WM_NOTIFY
				## expand notify messages
				name, code= self.GetNm(lp)
				s= self.msg % (name, code, hwnd, wp, lp)
			
			elif msg==WND_WM_NOTIFY: 
				
				if wp== WND_NM_MSGREFLECT:
					## expand reflected messages
					mr= WND_MSGREFLECT.from_address(lp)
					if mr.msg== 78:	# WM_NOTIFY
						msgOut= mr.msg
						name, code= self.GetNm(mr.lParam)
						s= self.remsg % (name, 
														code, 
														hwnd, 					
														mr.wParam,
														mr.lParam,
														mr.hwndFrom)
					else:
						msgOut= mr.msg
						s= self.remsg % (self.MsgName(mr.msg),
														mr.msg, 
														hwnd,			 	
														mr.wParam,
														mr.lParam,
														mr.hwndFrom)
				else:
					s= self.msg % (self.MsgName(msg), msg, hwnd,  wp, lp)
			else:
				s= self.msg % (self.MsgName(msg), msg, hwnd,  wp, lp)
			return msgOut, s
		return None

	
"""****************************************************************************
 class keeping track of api handles

NOTES
 
 reason timers are not tracked here is that hwnd has to be valid
 by the time the timer is closed. So atexit is a no op here 

 menus have to be handled very carefully.
 Closing an alreaddy closed menu is a severe error.
 Closing a menu attatched to a gui on exit will keep the message loop
 running... and so on.
****************************************************************************"""
class _TrackHandler(object):
	
	def __init__(self):
		self.handles = {'menus':[],'acceleratortables':[],'imagelists':[]}
	
	def Register(self, type_handle, handle):
		self.handles[type_handle].append(handle)
	
	def Unregister(self, type_handle, handle):
		self.handles[type_handle].remove(handle)
	
	def GetOpen(self): return self.handles
	
	def Close(self):
		error = {}
		for type_handle, handlelist in self.handles.items():
			if type_handle == 'menus':
				for i in handlelist:
					if not user32.DestroyMenu(i):
						try: error[type_handle].append(i)
						except: error[type_handle] = [i, ]
			elif type_handle == 'acceleratortables':
				for i in handlelist:
					if not user32.DestroyAcceleratorTable(i):
						try: error[type_handle].append(i)
						except: error[type_handle] = [i, ]
			elif type_handle == 'imagelists':
				for i in handlelist:
					if not comctl32.ImageList_Destroy(i):
						try: error[type_handle].append(i)
						except: error[type_handle] = [i, ]
		if error: 
			sys.stderr.write('**************************\n')
			sys.stderr.write('TrackHandler error\n')
			sys.stderr.write('could not close the following handles:\n')
			for type_handle, handlelist in error.items():
				sys.stderr.write('	%s\n' % type_handle)
				for i in handlelist:
					sys.stderr.write('		%s\n' % str(i))
			sys.stderr.write('**************************\n')
		
TrackHandler = _TrackHandler()
atexit.register(TrackHandler.Close)


"""******************************************************************
Sets or clears the MsgReflect flag for a window

By default a control sets the fReturn flag in the MSGREFLECT struct
to 1 when being passed a reflected message, to indicate that the control
passing the message should not pass the message to DefWindowProc in 
response.
This causes trouble with controls whos parent relies on the messages
from their childwindow being passed (dample. edit controls of comboboxes).
For these controls the MsgReflect flag should be cleared to enshure
default processing

******************************************************************"""
def SetFlagMsgReflect(window, Bool):
	if hasattr(window, '_base_fMsgReflect'):
		window._base_fMsgReflect= Bool and 1 or 0


"""********************************************************************
handlers for reflecting messages

windows and controls should use IsReflectMessage
dialog boxes IsDialogReflectMessage

The handlers check if a message should be reflected to
a control, sending it. Return value is None if it is not a message to be
relected.

Place this in your windowproc to make the controls
work correctly.

result= fw.IsReflectMessage(hwnd, msg, wp, lp)
if result != None: return result
else:
	# process messages


NOTESS
	Default processing in win32 api is that some messages like
	WM_COMMAND or WM_NOTIFY are passed to the parent window
	so that it can process them.
	This is a noop for framework stuff, where all control classes
	should be kept as encapsulated as possible. So the most 
	simple mechanism to enshure this is to reflect the messages
	send by a control to its parent right away, and let the childwindow
	do all the processing on its own.

Haven't checked this, but as far as I can see this is the only obstacle
to tackle if you want to use the controls from another framework
Only thing they rely on is a parent window class with an attribute
Hwnd and this handler.

********************************************************************"""

def ReflectMessage(hwnd, hwndTo, msg, wp, lp):
		
	msgr= WND_MSGREFLECT(hwnd, msg, wp, lp)
	result =user32.SendMessageA(hwndTo, 
														WND_WM_NOTIFY,
														WND_NM_MSGREFLECT, 
														addressof(msgr))
	if msgr.fReturn: return result
		
			
def IsReflectMessage(hwnd, msg, wp, lp):
	
	if msg==273:	# WM_COMMAND 
		if lp: return ReflectMessage(hwnd, lp, msg, wp, lp)
			
	elif msg==276:	# WM_HSCROLL
		if lp: return ReflectMessage(hwnd, lp, msg, wp, lp)
					
	elif msg==277:	# WM_VSCROLL
		if lp: return ReflectMessage(hwnd, lp, msg, wp, lp)
	
	elif msg==78:	# WM_NOTIFY
		nm = NMHDR.from_address(lp)
		return ReflectMessage(hwnd, nm.hwndFrom, msg, wp, lp)
							
	elif msg==43:	# WM_DRAWITEM
		# NOTE
		# can not reflect to comboboxes (ODT_COMBOBOX)
		# they do block all messages here
		# ?? do it anyway
		if wp:
			return ReflectMessage(hwnd, user32.GetDlgItem(hwnd, wp), msg, wp, lp)
		## let menu messages slip
		
	elif msg==44:	# WM_MEASUREITEN
		# NOTE
		# can not reflect to comboboxes (ODT_COMBOBOX)
		# they do block all messages here
		# ?? do it anyway
		if wp:
			return ReflectMessage(hwnd, user32.GetDlgItem(hwnd, wp),msg, wp, lp)
		## let menu messages slip
	
	return None



def IsDialogReflectMessage(hwnd, msg, wp, lp, dlgmode):
	#print dlgmode
	## TODO: test
	
	## filter WM_COMMAND for dialog boxes
	if msg==273:	# WM_COMMAND 
		
		#print wp, lp
		if lp: 
			if dlgmode=='modeless':
				return ReflectMessage(hwnd, lp, msg, wp, lp)
			
			if lp !=1:			# IDOK
				if lp != 2:		# IDCANCEL
					#DM_GETDEFID      = WM_USER + 0
					result= user32.SendMessageA(hwnd, 1024, 0, 0)
					
					if HIWORD(result) == 21323:	 # DC_HASDEFID
						defID= user32.GetDlgItem(hwnd, LOWORD(result))
						
						if defID != lp:
							return ReflectMessage(hwnd, lp, msg, wp, lp)
					else:
						return ReflectMessage(hwnd, lp, msg, wp, lp)	
		
	elif msg==276:	# WM_HSCROLL
		if lp: return ReflectMessage(hwnd, lp, msg, wp, lp)
					
	elif msg==277:	# WM_VSCROLL
		if lp: return ReflectMessage(hwnd, lp, msg, wp, lp)
	
	elif msg==78:	# WM_NOTIFY
		nm = NMHDR.from_address(lp)
		return ReflectMessage(hwnd, nm.hwndFrom, msg, wp, lp)
							
	elif msg==43:	# WM_DRAWITEM
		# NOTE
		# can not reflect to comboboxes (ODT_COMBOBOX)
		# they do block all messages here
		# ?? do it anyway
		return  ReflectMessage(hwnd, user32.GetDlgItem(hwnd, wp), msg, wp, lp)
		
	elif msg==44:	# WM_MEASUREITEN
		# NOTE
		# can not reflect to comboboxes (ODT_COMBOBOX)
		# they do block all messages here
		# ?? do it anyway
		return ReflectMessage(hwnd, user32.GetDlgItem(hwnd, wp),msg, wp, lp)
		
	return None


"""*****************************************************************************************
Copy Data handlers

CopyData(hwndSource, hwndDest, lp, data, reserved = 0)
	Copies data to another window

	hwndSource = the source window for the data
	hwndDest = the destination window
	lp = user defined parameter (range 0-65535)
	data = data to send (may be any string)
	reserved = if 1 the message is handled internally, setting a var _base_copyDataResult
						not notifying the user, if 0 	the user will receive a 'copydata' message in 
						the handler of its window

	Return value: True if the receiver returned True, False otherwise
	

HandleCopyData(hwnd, msg, wp, lp)

	Handles WM_COPYDATA in a messageloop

	Return value: the data being copied (as string) or None if the message
								does not conform framework rules


For the framework to recognize a WM_COPYDATA as 'friendly' the data is
prefixed internally with the GUID SZ_GUID_COPYDATA. 

*****************************************************************************************"""
WM_COPYDATA                   = 74

def CopyData(hwndSource, hwndDest, lp, data, reserved = 0):
	p= create_string_buffer(SZ_GUID_COPYDATA + data)
	## do not include NULL byte in cbData
	cd= COPYDATASTRUCT(MAKELONG(lp, reserved), sizeof(p) -1, addressof(p))
	return bool(user32.SendMessageA(hwndDest, WM_COPYDATA, hwndSource, byref(cd)))
	
def HandleCopyData(hwnd, msg, wp, lp):
	cd = COPYDATASTRUCT.from_address(lp)
		
	# make shure only trustable data gets in here 
	if WND_COPYDATA_MAXDATA >= cd.cbData >=  len(SZ_GUID_COPYDATA): 
		data= (c_char*cd.cbData).from_address(cd.lpData)
		if data[:len(SZ_GUID_COPYDATA)] == SZ_GUID_COPYDATA:
			return (cd.dwData, ''.join(data[len(SZ_GUID_COPYDATA):]))

	
		

	
