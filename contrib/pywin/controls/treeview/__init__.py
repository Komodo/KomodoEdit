
"""

NOT IMPLEMENTED
	
	TVM_CREATEDRAGIMAGE
	TVM_ENDEDITLABELNOW
	TVM_GETISEARCHSTRING
	TVM_GETNEXTITEM (TVGN_LASTVISIBLE)
	TVM_GETSCROLLTIME
	TVM_GETTOOLTIPS
	TVM_GETUNICODEFORMAT
	TVM_GETVISIBLECOUNT
	TVM_SETINSERTMARK
	TVM_SETSCROLLTIME
	TVM_SETTOOLTIPS
	TVM_SETUNICODEFORMAT

	NM_SETCURSOR
	TVN_DELETEITEM
	TVN_GETINFOTIP
	TVN_ITEMEXPANDED
	TVN_SELCHANGED
	TVN_SINGLEEXPAND


TODO
	
	- setting intgral height seems to mess up focus handling 
		items get selected but focus highlight is not set correctly
		for items following the item at lower level
	- GetCutHilighted method seems not to be available
	- SetBold --or whatever-- to draw an item bold not seems to work
	- what the heck does 'expandpartial' do ??
	- CollapseReset does not work correctly. The items are removed but
		the + sign is still there and HasChildren returns True 

	- implement navigating the Treeview by index 
		(0, 3) should return the third sub-item of the first root-item and so on
	- the path thing needs backslash escaping 

	- test 'getdispinfo'
	- test HasChildren with 'getdispinfo'
	- test new method SetChildInfo

"""




from wnd.controls.treeview.methods import TreeviewMethods 
from wnd.controls.treeview.header import (TVCOMPAREFUNC,
																				create_string_buffer,
																				InitCommonControlsEx, 
																				ControlMethods)
from wnd.controls.treeview.header import Msgs, Styles
from wnd.controls.treeview.helpers import ITERPATH
from wnd.controls.base import control

#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
ICC_TREEVIEW_CLASSES   = 2
InitCommonControlsEx(ICC_TREEVIEW_CLASSES)


#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::


class Treeview(TreeviewMethods, control.BaseControl, ControlMethods):
	
	def __init__(self, parent, x, y, w, h, *styles):
		self.Style= Styles
		self.Msg= Msgs 
		
		
		styles += 'subclass',
		control.BaseControl.__init__(self, parent, "SysTreeView32", "", x, y, w, h, *styles)	
		self._client_buffer = create_string_buffer(512)
		self._client_IterPath=ITERPATH()

		self._client_p_SortFunc = TVCOMPAREFUNC(self._client_SortFunc)
		self._client_CompFunc = None
		

class TreeviewFromHandle(TreeviewMethods, control.ControlFromHandle, ControlMethods):
	
	
	def __init__(self, hwnd, *styles):
		self.Style= Styles
		self.Msg= Msgs 
		
		
		styles += 'subclass',
		control.ControlFromHandle.__init__(self, hwnd, *styles)
		self._client_buffer = create_string_buffer(512)
		self._client_IterPath=ITERPATH()

		self._client_p_SortFunc = TVCOMPAREFUNC(self._client_SortFunc)
		self._client_CompFunc = None
		