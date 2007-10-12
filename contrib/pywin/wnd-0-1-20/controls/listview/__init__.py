"""
LAST VISITED 28.03.05


NOT IMPLEMENTED
	
	LVM_CREATEDRAGIMAGE
	LVM_GETCALLBACKMASK
	LVM_GETHOTCURSOR
	LVM_GETHOTITEM
	LVM_GETHOVERTIME
	LVM_GETISEARCHSTRING
	LVM_GETITEMSPACING
	LVM_GETNUMBEROFWORKAREAS
	LVM_GETORIGIN
	LVM_GETSELECTIONMARK
	LVM_GETTOOLTIPS
	LVM_GETUNICODEFORMAT		## no const in lv_msgs
	LVM_GETVIEWRECT
	LVM_GETWORKAREAS
	LVM_SETCALLBACKMASK
	LVM_SETHOTCURSOR
	LVM_SETHOTITEM
	LVM_SETHOVERTIME
	LVM_SETICONSPACING
	LVM_SETITEMPOSITION32			## or LVM_SETITEMPOSITION
	LVM_SETSELECTIONMARK
	LVM_SETTOOLTIPS
	LVM_SETUNICODEFORMAT		## no const in lv_msgs
	LVM_SETWORKAREAS
	LVM_UPDATE 


TODO
	
	- Get/Set overlay image
	- Get/Set state image
	
	- customdraw
		NOTIFYITEMDRAW works
		NOTIFYPOSTPAINT does not
		NOTIFYITEMERASE not implemented, dono if it works
		NOTIFYPOSTERASE not implemented, dono if it works
	
	- getdispinfo


NOTES
	
	- labeledit
		edit control can not be subclassed (leaks).
		

"""




from ctypes import create_string_buffer
from wnd.wintypes import InitCommonControlsEx
from wnd.controls.listview.methods import ListviewMethods
from wnd.controls.listview.header import Msgs, Styles
from wnd.controls.base import control
from wnd.controls.base.methods import ControlMethods
from wnd.controls.listview.header import COMPAREFUNC
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
ICC_LISTVIEW_CLASSES   = 1 
InitCommonControlsEx(ICC_LISTVIEW_CLASSES)

LVIS_FOCUSED           = 1
LVIS_SELECTED          = 2
LVIS_CUT               = 4
LVIS_DROPHILITED       = 8
LVIS_GLOW              = 16
LVIS_ACTIVATING        = 32

#*********************************************************************
#*********************************************************************

class Listview(ListviewMethods, control.BaseControl, ControlMethods):
		
	def __init__(self, parent,  x, y, w, h, *styles):
		self.Style= Styles
		self.Msg= Msgs 
		
		
		styles += 'subclass', 'shareimagelists'
		title = ''
		control.BaseControl.__init__(self, parent, "SysListView32", title, x, y, w, h, *styles)
		self._client_buffer = create_string_buffer(512)
		self._client_keyboardMsgs = []
		self._client_p_SortFunc = COMPAREFUNC(self._client_SortFunc)
		self._client_CompFunc = None
	

class ListviewFromHandle(ListviewMethods, control.ControlFromHandle, ControlMethods):
	
	def __init__(self, hwnd, *styles):
		self.Style= Styles
		self.Msg= Msgs 
			
		styles += 'subclass',
		control.ControlFromHandle.__init__(self, hwnd, *styles)
		self.SetStyle('shareimagelists')
		self._client_buffer = create_string_buffer(512)
		self._client_keyboardMsgs = []
		self._client_p_SortFunc = COMPAREFUNC(self._client_SortFunc)
		self._client_CompFunc = None
		
