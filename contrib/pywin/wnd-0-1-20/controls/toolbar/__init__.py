"""


NOTES
	

NOT IMPLEMENTED
	
	 NM_CHAR 
	 NM_CUSTOMDRAW
	 TBN_CUSTHELP
	 NM_KEYDOWN 
	 TBN_GETOBJECT
	
	
	
	 TB_GETANCHORHIGHLIGHT
	 TB_GETBITMAPFLAGS
	 TB_GETHOTITEM
	 TB_GETINSERTMARK
	 TB_GETINSERTMARKCOLOR
	 TB_GETOBJECT
	 TB_GETSTATE
	 TB_GETSTYLE
	 TB_GETTEXTROWS
	 TB_GETUNICODEFORMAT
	 TB_INDETERMINATE
	 TB_INSERTMARKHITTEST
	 TB_ISBUTTONINDETERMINATE
	 TB_MAPACCELERATOR
	 TB_SAVERESTORE
	 TB_SETANCHORHIGHLIGHT
	 TB_SETDRAWTEXTFLAGS
	 TB_SETINSERTMARK
	 TB_SETINSERTMARKCOLOR
	 TB_SETMAXTEXTROWS
	 TB_SETPARENT
	 TB_SETSTATE
	 TB_SETSTYLE
	T B_SETUNICODEFORMAT

	
	def SetInsetmarkColor(self, colorref):
		return self.SendMessage(self.Hwnd, self.Msg.TB_SETINSERTMARKCOLOR , 0, colorref)
	
	
	def AddBitmap(self, ID, hInst=None):
		# not complete yet. Second member is the resource identifier as UINT.
		if not hInst: 
			hInst=4294967295		# HINST_COMMCTRL
			#hInst=-1
			try: ID={'stdsmall':0,'stdlarge': 1,'viewsmall':4,
						'viewlarge':5,'histsmall':8,'histlarge':9}[ID]
		tbmp= TBADDBITMAP(hInst, ID)
		result= self.SendMessage(self.Hwnd, self.Msg.TB_ADDBITMAP, 0, byref(tbmp))
		if result < 0: raise "could not add bitmap"
		return result
		
	
	def SetBitmapSize(self, x, y):
		if not self.SendMessage(self.Hwnd, self.Msg.TB_SETBITMAPSIZE, 0, MAKELONG(x, y)):
			raise "could not set bitmap size"
	
"""


from wnd.controls.toolbar.methods import ToolbarMethods 
from wnd.controls.toolbar.header import (TBBUTTON,
																				sizeof,
																				byref,
																				InitCommonControlsEx, )
from wnd.controls.toolbar.header import (Msgs,
																			Styles)
from wnd.controls.toolbar.helpers import ReadSnapshot, Snapshot
from wnd.controls.base import control
from wnd.controls.base.methods import ControlMethods

#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
ICC_BAR_CLASSES        = 4
InitCommonControlsEx(ICC_BAR_CLASSES)

#*******************************************************************


class Toolbar(ToolbarMethods, control.BaseControl, ControlMethods):
		
	def __init__(self, parent, *styles):
		self.Style= Styles
		self.Msg= Msgs 
			
		styles += 'subclass',
		control.BaseControl.__init__(self, parent, "ToolbarWindow32", "", 0, 0, 0, 0, *styles)
		self.SendMessage(self.Hwnd, self.Msg.TB_BUTTONSTRUCTSIZE, sizeof(TBBUTTON), 0)
		
		self._client_snapshot= None
		self._client_textMax= 127
				


class ToolbarFromHandle(ToolbarMethods, control.ControlFromHandle, ControlMethods):
	
	def __init__(self, hwnd, *styles):
		self.Style= Styles
		self.Msg= Msgs 
				
		styles += 'subclass',
		control.ControlFromHandle.__init__(self, hwnd, *styles)
		self.SendMessage(self.Hwnd, self.Msg.TB_BUTTONSTRUCTSIZE, sizeof(TBBUTTON), 0)
		
		self._client_snapshot= None
		self._client_textMax= 127
		


class ToolbarFromSnapshot(Toolbar):
	def __init__(self, parent, snapshot, *styles):
		Toolbar.__init__(self, parent, *styles)
				
		try:
			arrBt, text, arrUser= ReadSnapshot(snapshot)
		except Exception, details: 
			raise ValueError(details)
		self._client_snapshot= Snapshot(arrBt, text, arrUser)
		iTitle=self.SendMessage(self.Hwnd, self.Msg.TB_ADDSTRING, 0, text)
		if iTitle < 0:
			raise ValueError("could not add strings")
		if not self.SendMessage(self.Hwnd, self.Msg.TB_ADDBUTTONS, len(arrBt), byref(arrBt)):
				raise ValueError( "could not add items")
		if arrUser:
			self.Clear()
			if not self.SendMessage(self.Hwnd, self.Msg.TB_ADDBUTTONS, len(arrUser), byref(arrUser)):
				raise ValueError( "could not add user items")
			
		self.SendMessage(self.Hwnd, self.Msg.TB_AUTOSIZE, 0, 0)

		
		
	