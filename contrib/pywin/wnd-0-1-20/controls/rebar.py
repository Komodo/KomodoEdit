"""

TODO:
	pretty old code here.
	Test all method calls

 NOT implemented

 NM_CUSTOMDRAW
 RBM_SETUNICODEFORMAT
 RBM_GETUNICODEFORMAT
 RBN_AUTOSIZE
 RBN_CHILDSIZE
 RBN_DELETEDBAND
 RBN_DELETINGBAND
 RBN_ENDDRAG
 RBN_GETOBJECT
 RBN_HEIGHTCHANGE
 RBN_LAYOUTCHANGED

 
 RB_BEGINDRAG
 RB_DRAGMOVE
 RB_ENDDRAG
 RB_GETDROPTARGET
 RB_GETCOLORSCHEME
 RB_SETCOLORSCHEME
 RB_GETPALETTE
 RB_SETPALETTE

"""

from wnd.wintypes import (comctl32,
													InitCommonControlsEx,
													create_string_buffer,
													UINT_MAX,
													NM_FIRST,
													Structure,
													sizeof,
													byref,
													addressof,
													NMHDR,
													BOOL,
													RECT,
													DWORD,
													UINT,
													LPARAM,
													POINT,
													INT,
													COLORREF,
													LPSTR,
													HANDLE,
													)
from wnd import fwtypes as fw
from wnd.wintypes import DRAWITEMSTRUCT
from wnd.controls.base.methods import ControlMethods
from wnd.controls.base import control

#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
ICC_COOL_CLASSES       = 1024 
InitCommonControlsEx(ICC_COOL_CLASSES)


		
class RebarMethods: 
		
	#-----------------------------------------------------------------	
	# message handler	
	
	def onMESSAGE(self, hwnd, msg, wp, lp):
		
		if msg==fw.WND_WM_NOTIFY:
			if wp==fw.WND_NM_MSGREFLECT:
				msgr= fw.WND_MSGREFLECT.from_address(lp)
				msgr.fReturn= self._base_fMsgReflect
				
				if msgr.msg ==self.Msg.NM_RELEASEDCAPTURE:
					self.onMSG(hwnd, "releasedcapture", 0, 0)
					return 0
				
				elif msgr.msg ==self.Msg.RBN_BEGINDRAG:
					nmrb=NMREBAR.from_address(msgr.lParam)
					result= self.onMSG(hwnd, "begindrag", (nmrb.wID, nmrb.uBand), 0)
					if result==False: return 1
					return 0
				
				return 0
		elif msg==self.Msg.WM_DESTROY:
			self.onMSG(hwnd, "destroy", 0, 0)
			
			
	#---------------------------------------------------------------------------------
	# helper methods

	def SetTextMax(self, n):
		self._client_buffer = create_string_buffer(n) +1
	
	def GetTextMax(self):
		return sizeof(self._client_buffer) -1
	
	def _client_TruncText(self, text):
		"""Truncates text to _client_buffer. Return value is
		the address of the buffer."""
		n = len(text)
		szeof = sizeof(self._client_buffer) -1
		if n > szeof: text = '%s...\x00' % text[:szeof-3]
		else: text = '%s\x00' % text
		self._client_buffer.raw = text
		return addressof(self._client_buffer)			
		

	
	#-------------------------------------------------------------------------
	# methods
			
	def Band(self, ID, title, Control,  w, h, *style, **kwargs):
		return self. InsertBand(-1, ID, title, Control,  w, h, *style, **kwargs)
	
	
	
	def InsertBand(self, i, ID, title, Control,  w, h, *style, **kwargs):
		## style does not work
		## if you set the mask bit or a style except from
		# RBBS_VARIABLEHEIGHT, RB_INSERTBAND will fail
		
		bi=REBARBANDINFO()
		bi.fMask = RBBIM_ID | RBBIM_CHILD| RBBIM_CHILDSIZE		
		#|RBBIM_STYLE
		bi.fStyle = RBBS_VARIABLEHEIGHT
		
		bi.wID = ID
		bi.lpText = title
		bi.hwndChild= Control.Hwnd
		bi.cxMinChild, bi.cyMinChild= w, h
		## ?? looks useless. Dono what it does
		# bi.cyChild, bi.cyMaxChild= childSize
		##bi.cyIntegral= 20 ??
		
		if title:
			bi.fMask |=  RBBIM_TEXT
			bi.lpText = title
		
		## dono ehat this does, is supposed to set the band width
		#if width:
			#bi.fMask |= RBBIM_SIZE
			#bi.cx= width
		
		if style:
			#bi.fMask |= RBBIM_STYLE
			st={'break':1,'fixedsize':2,'childedge':4,'hidden':8,'novert':16,
				'fixedbmp':32,'variableheight':64,'gripperalways':128,
				'nogripper':256,'usechevron':512,'hidetitle':1024,'topalign':2048}
			for i in style:
				try:
					bi.fStyle |= st[i]
				except: raise ValueError, "invalid style: %s" % i

		#if idealSize:
		#	bi.fMask |= RBBIM_IDEALSIZE
		#	bi.cxIdeal=  idealSize
		
		iImage= kwargs.get('iImage')
		if iImage !=None:
			bi.fMask |= RBBIM_IMAGE
			bi.lParam= iImage
				
		lp= kwargs.get('lp')
		if lp != None:
			bi.fMask |= RBBIM_LPARAM
			bi.iImage= lp
		
		colors= kwargs.get('colors')
		if colors:
			bi.fMask |= RBBIM_COLORS
			bi.clrFore, bi.clrBack= colors
		
		sizeHeader= kwargs.get('sizeHeader')
		if sizeHeader != None:
			bi.fMask |= RBBIM_HEADERSIZE
			bi.cxHeader= sizeHeader

		bitmap= kwargs.get('bitmap')
		if bitmap != None:
			bi.fMask |= RBBIM_BACKGROUND
			bi.hbmBack= bitmap.handle

		if not self.SendMessage(self.Hwnd, self.Msg.RB_INSERTBAND,
															i, byref(bi)):
			raise "could insert band"
	
				
	def IDToIndex(self, i):
		result= self.SendMessage(self.Hwnd, self.Msg.RB_IDToIndex, i, 0)
		if result <0: raise "no such band"
		return result
	
	
	def IndexToID(self, i):
		bi=REBARBANDINFO()
		bi.fMask = RBBIM_ID 
		if not self.SendMessage(self.Hwnd, self.Msg.RB_GETBANDINFO,
															i, byref(bi)):
			raise "could retrieve band ID"
		return bi.wID
		
	
	def RemoveBand(self, ID):
		if not self.SendMessage(self.Hwnd, self.Msg.RB_DELETEBAND, 0, self.IDToIndex(ID)):
			raise "could not remove band"

	def __iter__(self):
		for i in range(self.__len__()): yield i
	
	def __len__(self):
		return self.SendMessage(self.Hwnd, self.Msg.RB_GETBANDCOUNT, 0, 0)
	
	
	def GetTextColor(self):
		return self.SendMessage(self.Hwnd, self.Msg.RB_GETTEXTCOLOR, 0, 0)
	
	def SetTextColor(self, colorref):
		return self.SendMessage(self.Hwnd, self.Msg.RB_SETTEXTCOLOR, 0, colorref)
	
	def SetBkColor(self, colorref):
		return self.SendMessage(self.Hwnd, self.Msg.RB_SETBKCOLOR, 0, colorref)
	
	
	def GetBandTitle(self, ID):
		bi=REBARBANDINFO()
		bi.fMask = RBBIM_TEXT
		bi.lpText = addressof(self._client_buffer)
		bi.cch = sizeof(self._client_buffer) - 1
		if not self.SendMessage(self.Hwnd, self.Msg.RB_GETBANDINFO,
															self.IDToIndex(ID), byref(bi)):
			raise "could retrieve band title"
		return self._client_buffer.value
		
	def SetBandTitle(self, ID, title):
		bi=REBARBANDINFO()
		bi.fMask = RBBIM_TEXT
		bi.lpText = self._client_TruncText(title)
		if not self.SendMessage(self.Hwnd, self.Msg.RB_SETBANDINFO,
															self.IDToIndex(ID), byref(bi)):
			raise "could set band title"		
	
	
	def GetBandColors(self, ID):
		bi=REBARBANDINFO()
		bi.fMask = RBBIM_COLORS
		if not self.SendMessage(self.Hwnd, self.Msg.RB_GETBANDINFO,
															self.IDToIndex(ID), byref(bi)):
			raise "could retrieve band colors"
		return bi.clrFore, bi.clrBack
		
	def SetBandColors(self, ID, colorrefText, colorrefBk):
		bi=REBARBANDINFO()
		bi.fMask = RBBIM_COLORS
		bi.clrFore=colorrefText
		bi.clrBack=colorrefBk
		if not self.SendMessage(self.Hwnd, self.Msg.RB_SETBANDINFO,
															self.IDToIndex(ID), byref(bi)):
			raise "could set band colors"
		
	
	def SetBandBackgroundImage(self, ID, Bitmap):
		bi=REBARBANDINFO()
		bi.fMask = RBBIM_BACKGROUND
		bi.hbmBack=Bitmap.handle
		if not self.SendMessage(self.Hwnd, self.Msg.RB_SETBANDINFO,
															self.IDToIndex(ID), byref(bi)):
			raise "could set band background image"
					
	def GetBandBackgroundImage(self, ID):
		bi=REBARBANDINFO()
		bi.fMask |= RBBIM_BACKGROUND
		if not self.SendMessage(self.Hwnd, self.Msg.RB_GETBANDINFO,
															self.IDToIndex(ID), byref(bi)):
			raise "could retrieve band background image"
		if bi.hbmBack:	return bi.hbmBack
	
	
	def GetBandImage(self, ID):
		bi=REBARBANDINFO()
		bi.fMask = RBBIM_IMAGE
		
		if not self.SendMessage(self.Hwnd, self.Msg.RB_GETBANDINFO,
															self.IDToIndex(ID), byref(bi)):
			raise "could retrieve band image"
		return bi.iImage
		
	def SetBandImage(self, ID, i):
		bi=REBARBANDINFO()
		bi.fMask = RBBIM_IMAGE
		bi.iImage=i
		if not self.SendMessage(self.Hwnd, self.Msg.RB_SETBANDINFO,
															self.IDToIndex(ID), byref(bi)):
			raise "could set band image"
					
	
	def GetBandControlSize(self, ID):
		bi=REBARBANDINFO()
		bi.fMask = RBBIM_CHILDSIZE
		if not self.SendMessage(self.Hwnd, self.Msg.RB_GETBANDINFO,
															self.IDToIndex(ID), byref(bi)):
			raise "could retrieve band control size"
		return bi.cxMinChild, bi.cyMinChild
	
	def SetBandControlSize(self, ID, w, h):
		bi=REBARBANDINFO()
		bi.fMask |= RBBIM_CHILDSIZE
		bi.cxMinChild = w or 0
		bi.cyMinChild = h or 0
		if not self.SendMessage(self.Hwnd, self.Msg.RB_SETBANDINFO,
															self.IDToIndex(ID), byref(bi)):
			raise "could set band control size"

	
	def GetBandMaximizedWidth(self, ID):
		bi=REBARBANDINFO()
		bi.fMask |= RBBIM_IDEALSIZE 
		if not self.SendMessage(self.Hwnd, self.Msg.RB_GETBANDINFO,
															self.IDToIndex(ID), byref(bi)):
			raise "could retrieve band maximized size"
		return bi.cxIdeal
	
	def SetBandMaximizedWidth(self, ID, n):
		bi=REBARBANDINFO()
		bi.cxIdeal = n 
		bi.fMask |= RBBIM_IDEALSIZE 
		if not self.SendMessage(self.Hwnd, self.Msg.RB_SETBANDINFO,
															self.IDToIndex(ID), byref(bi)):
			raise "could set band maximized size"
		
	
	def GetBandHeaderSize(self, ID):
		bi=REBARBANDINFO()
		bi.fMask |= RBBIM_HEADERSIZE
		if not self.SendMessage(self.Hwnd, self.Msg.RB_GETBANDINFO,
															self.IDToIndex(ID), byref(bi)):
			raise "could retrieve band header size"
		return bi.cxHeader 
	
	def SetBandHeaderSize(self, ID, n):
		bi=REBARBANDINFO()
		bi.cxHeader = n
		bi.fMask |= RBBIM_HEADERSIZE
		if not self.SendMessage(self.Hwnd, self.Msg.RB_SETBANDINFO,
															self.IDToIndex(ID), byref(bi)):
			raise "could set band header size"
		
	
	def GetBandChild(self, ID):
		bi=REBARBANDINFO()
		bi.fMask = RBBIM_CHILD
		if not self.SendMessage(self.Hwnd, self.Msg.RB_GETBANDINFO,
															self.IDToIndex(ID), byref(bi)):
			raise "could retrieve band child"
		if bi.hwndChild: return bi.hwndChild
	def SetBandChild(self, ID, Control):
		bi=REBARBANDINFO()
		bi.fMask = RBBIM_CHILD
		bi.hwndChild=Control.Hwnd
		if not self.SendMessage(self.Hwnd, self.Msg.RB_SETBANDINFO,
															self.IDToIndex(ID), byref(bi)):
			raise "could set band child"
		
	
	def GetBandWidth(self, ID):
		bi=REBARBANDINFO()
		bi.fMask =  RBBIM_SIZE
		
		if not self.SendMessage(self.Hwnd, self.Msg.RB_GETBANDINFO,
															self.IDToIndex(ID), byref(bi)):
			raise "could retrieve band width"
		return bi.cx
	
	def SetBandWidth(self, ID, n):
		bi=REBARBANDINFO()
		bi.fMask =  RBBIM_SIZE
		bi.cx = n
		if not self.SendMessage(self.Hwnd, self.Msg.RB_SETBANDINFO,
															self.IDToIndex(ID), byref(bi)):
			raise "could set band width"
		
	
	def GetBandLparam(self, ID):
		bi=REBARBANDINFO()
		
		bi.fMask = RBBIM_LPARAM
		if not self.SendMessage(self.Hwnd, self.Msg.RB_GETBANDINFO,
															self.IDToIndex(ID), byref(bi)):
			raise "could retrieve band lParam"
		return bi.lParam
	
	def SetBandLparam(self, ID, lp):
		bi=REBARBANDINFO()
		bi.lParam = lp
		bi.fMask = RBBIM_LPARAM
		if not self.SendMessage(self.Hwnd, self.Msg.RB_SETBANDINFO,
															self.IDToIndex(ID), byref(bi)):
			raise "could set band lParam"
	
	def MoveBand(self, iFrom, iTo):
		if not self.SendMessage(self.Hwnd, self.Msg.RB_MOVEBAND, iFrom, iTo):
			raise "could not move band"
		
	
	def GetBandBorders(self, ID):
		rc=RECT()
		self.SendMessage(self.Hwnd, self.Msg.RB_GETBANDBORDERS, self.IDToIndex(ID), byref(rc))
		return rc
	
	
	def GetHeight(self):
		return self.SendMessage(self.Hwnd, self.Msg.RB_GETBARHEIGHT, 0, 0)

	def GetBandRect(self, ID):
		rc=RECT()
		if not self.SendMessage(self.Hwnd, self.Msg.RB_GETBANDRECT, self.IDToIndex(ID), byref(rc)):
			raise "could not retrieve band rect"
		return rc
		
	def GetRowCount(self):
		return self.SendMessage(self.Hwnd, self.Msg.RB_GETROWCOUNT, 0, 0)

	def GetRowHeight(self, i):
		return self.SendMessage(self.Hwnd, self.Msg.RB_GETROWHEIGHT, i, 0)


	def GetTooltips(self):
		result=  self.SendMessage(self.Hwnd, self.Msg.RB_GETTOOLTIPS, 0, 0)
		if result: return result
		
	def ItemHittest(self, x, y):
		ht=RBHITTESTINFO()
		ht.pt.x, ht.pt.y = x, y
		result= self.SendMessage(self.Hwnd, self.Msg.RB_HITTEST, 0, byref(ht))
		if result >-1:
			out=[ht.iBand, None]
			if h.fFlags==RBHT_CAPTION: out[1]=="caption"
			elif h.fFlags==RBHT_CLIENT: out[1]=="client"
			elif h.fFlags==RBHT_GRABBER: out[1]=="grbber"
			elif h.fFlags==RBHT_NOWHERE: out[1]=="unknown"
			return out
		
					
	def MaximizeBand(self, ID, maxsize=True):
		if maxsize: maxsize=1
		else: maxsize=0
		self.SendMessage(self.Hwnd, self.Msg.RB_MAXIMIZEBAND, self.IDToIndex(ID), maxsize)

	def MinimizeBand(self, ID):
		self.SendMessage(self.Hwnd, self.Msg.RB_MINIMIZEBAND, self.IDToIndex(ID), 0)

			
	def ShowBand(self, ID):
		if not self.SendMessage(self.Hwnd, self.Msg.RB_SHOWBAND, self.IDToIndex(ID), 1):
			raise "could not show band"

	def HideBand(self, ID):
			if not self.SendMessage(self.Hwnd, self.Msg.RB_SHOWBAND, self.IDToIndex(ID), 0):
				raise "could not hide band"

	def SetTooltips(self, Tooltips):
		self.SendMessage(self.Hwnd, self.Msg.RB_SETTOOLTIPS, Tooltips.Hwnd, 0)

	def ArrangeBands(self, Rect):
		if self.SendMessage(self.Hwnd, self.Msg.RB_SIZETORECT, 0, byref(Rect)):
			return True
		return False

	def SetImagelist(self, Imagelist):
		if Imagelist== None:
			handle= 0
		else:
			handle= Imagelist.handle
		
		rbi=REBARINFO(sizeof(REBARINFO), RBIM_IMAGELIST, handle)
		if not self.SendMessage(self.Hwnd, self.Msg.RB_SETBARINFO, 0, byref(rbi)):
				raise "could not set imagelist"


	def GetImagelist(self):
		rbi=REBARINFO(sizeof(REBARINFO), RBIM_IMAGELIST, 0)
		if not self.SendMessage(self.Hwnd, self.Msg.RB_GETBARINFO, 0, byref(rbi)):
				raise "could not retrieve imagelist"
		if rbi.himl: return rbi.himl






#***********************************************************************
#***********************************************************************
class Rebar(RebarMethods, control.BaseControl, ControlMethods):
		
	def __init__(self, parent,*styles):
		self.Style= Styles
		self.Msg= Msgs 
			
		
		styles += 'subclass',
		control.BaseControl.__init__(self, parent, "ReBarWindow32", "", 0, 0, 0, 0, *styles)
		
		self._client_buffer = create_string_buffer(128)
		

class RebarFromHandle(RebarMethods, control.ControlFromHandle, ControlMethods):
		
	def __init__(self, hwnd, *styles):
		self.Style= Styles
		self.Msg= Msgs 
		
		
		styles += 'subclass',
		control.ControlFromHandle.__init__(self, hwnd,*styles)	
		
		self._client_buffer = create_string_buffer(128)



#***********************************************
WM_USER   = 1024
RBN_FIRST               = UINT_MAX-831
CCM_FIRST              = 8192


CCM_SETCOLORSCHEME     = CCM_FIRST + 2 # lParam is color scheme
CCM_GETCOLORSCHEME     = CCM_FIRST + 3 
CCM_GETDROPTARGET      = CCM_FIRST + 4
#***********************************************

class Styles:
	CCS_TOP           = 1
	CCS_NOMOVEY       = 2
	CCS_BOTTOM        = 3
	CCS_NORESIZE      = 4
	CCS_NOPARENTALIGN = 8
	CCS_ADJUSTABLE    = 32
	CCS_NODIVIDER     = 64
	CCS_VERT          = 128
	CCS_LEFT          = CCS_VERT | CCS_TOP
	CCS_RIGHT         = CCS_VERT | CCS_BOTTOM
	CCS_NOMOVEX       = CCS_VERT | CCS_NOMOVEY
	
	
	RBS_TOOLTIPS        = 256
	RBS_VARHEIGHT       = 512
	RBS_BANDBORDERS     = 1024
	RBS_FIXEDORDER      = 2048
	RBS_REGISTERDROP    = 4096
	RBS_AUTOSIZE        = 8192
	RBS_VERTICALGRIPPER = 16384  # this always has the vertical gripper (default for horizontal mode)
	RBS_DBLCLKTOGGLE    = 32768

Styles.__dict__.update(control.control_styles.__dict__)
Styles.prefix += ['RBS_', 'CCS_']


class Msgs: 
	RB_INSERTBAND   = WM_USER + 1
	RB_DELETEBAND   = WM_USER + 2
	RB_GETBARINFO   = WM_USER + 3
	RB_SETBARINFO   = WM_USER + 4
	#RB_GETBANDINFO  = (WM_USER + 5)    # for _WIN32_IE < 1024
	RB_SETBANDINFO  = WM_USER + 6
	RB_SETPARENT    = WM_USER + 7
	RB_HITTEST      = WM_USER + 8
	RB_GETRECT      = WM_USER + 9
	RB_INSERTBANDW  = WM_USER + 10
	RB_SETBANDINFOW = WM_USER + 11
	RB_GETBANDCOUNT = WM_USER + 12
	RB_GETROWCOUNT  = WM_USER + 13
	RB_GETROWHEIGHT = WM_USER + 14
	RB_IDToIndex    = WM_USER + 16 # wParam == id
	RB_GETTOOLTIPS  = WM_USER + 17
	RB_SETTOOLTIPS  = WM_USER + 18
	RB_SETBKCOLOR   = WM_USER + 19 # sets the default BK color
	RB_GETBKCOLOR   = WM_USER + 20 # defaults to CLR_NONE
	RB_SETTEXTCOLOR = WM_USER + 21
	RB_GETTEXTCOLOR = WM_USER + 22 # defaults to 0
	RBSTR_CHANGERECT = 1 # flags for RB_SIZETORECT
	RB_SIZETORECT   = WM_USER + 23 # resize the rebar/break bands and such to this rect (lparam)
	RB_SETCOLORSCHEME  = CCM_SETCOLORSCHEME  # lParam is color scheme
	RB_GETCOLORSCHEME  = CCM_GETCOLORSCHEME  # fills in COLORSCHEME pointed to by lParam
	RB_BEGINDRAG    = WM_USER + 24
	RB_ENDDRAG      = WM_USER + 25
	RB_DRAGMOVE     = WM_USER + 26
	RB_GETBARHEIGHT = WM_USER + 27
	RB_GETBANDINFOW = WM_USER + 28
	RB_GETBANDINFO  = WM_USER + 29
	RB_MINIMIZEBAND = WM_USER + 30
	RB_MAXIMIZEBAND = WM_USER + 31
	RB_GETDROPTARGET =CCM_GETDROPTARGET
	RB_GETBANDBORDERS = WM_USER + 34  # returns in lparam = lprc the amount of edges added to band wparam
	RB_SHOWBAND     = WM_USER + 35      # show/hide band
	RB_SETPALETTE   = WM_USER + 37
	RB_GETPALETTE   = WM_USER + 38
	RB_MOVEBAND     = WM_USER + 39
	#RB_SETUNICODEFORMAT = CCM_SETUNICODEFORMAT
	#RB_GETUNICODEFORMAT = CCM_GETUNICODEFORMAT
	RB_PUSHCHEVRON  = WM_USER + 43
	
		
	RBN_HEIGHTCHANGE    = RBN_FIRST - 0
	RBN_GETOBJECT       = RBN_FIRST - 1
	RBN_LAYOUTCHANGED   = RBN_FIRST - 2
	RBN_AUTOSIZE        = RBN_FIRST - 3
	RBN_BEGINDRAG       = RBN_FIRST - 4
	RBN_ENDDRAG         = RBN_FIRST - 5
	RBN_DELETINGBAND    = RBN_FIRST - 6     # Uses NMREBAR
	RBN_DELETEDBAND     = RBN_FIRST - 7     # Uses NMREBAR
	RBN_CHILDSIZE       = RBN_FIRST - 8
	RBN_CHEVRONPUSHED   = RBN_FIRST - 10
	RBN_MINMAX          = RBN_FIRST - 21
	RBN_AUTOBREAK       = RBN_FIRST - 22
	
	
	NM_RELEASEDCAPTURE = NM_FIRST - 16
	#NM_CUSTOMDRAW      = NM_FIRST - 12

Msgs.__dict__.update(control.control_msgs.__dict__)

#******************************************************************************************

RBIM_IMAGELIST  = 1

RBBS_BREAK          = 1  # break to new line
RBBS_FIXEDSIZE      = 2  # band can't be sized
RBBS_CHILDEDGE      = 4  # edge around top & bottom of child window
RBBS_HIDDEN         = 8  # don#t show
RBBS_NOVERT         = 16  # don#t show when vertical
RBBS_FIXEDBMP       = 32  # bitmap doesn#t move during band resize
RBBS_VARIABLEHEIGHT = 64  # allow autosizing of this child vertically
RBBS_GRIPPERALWAYS  = 128  # always show the gripper
RBBS_NOGRIPPER      = 256  # never show the gripper
RBBS_USECHEVRON     = 512  # display drop-down button for this band if it#s sized smaller than ideal width
RBBS_HIDETITLE      = 1024  # keep band title hidden
RBBS_TOPALIGN       = 2048  # keep band title hidden


RBBIM_STYLE         = 1
RBBIM_COLORS        = 2
RBBIM_TEXT          = 4
RBBIM_IMAGE         = 8
RBBIM_CHILD         = 16
RBBIM_CHILDSIZE     = 32
RBBIM_SIZE          = 64
RBBIM_BACKGROUND    = 128
RBBIM_ID            = 256
RBBIM_IDEALSIZE     = 512
RBBIM_LPARAM        = 1024
RBBIM_HEADERSIZE    = 2048  # control the size of the header


class NMRBAUTOSIZE(Structure):
	_fields_ = [("hdr", NMHDR),
					("fChanged", BOOL),
					("rcTarget", RECT),
					("rcActual", RECT)]

class NMREBAR(Structure):
	_fields_ = [("hdr", NMHDR),
					("dwMask", DWORD),
					("uBand", UINT),
					("fStyle", UINT),
					("wID", UINT),
					("lParam", LPARAM)]

class NMREBARCHILDSIZE(Structure):
	_fields_ = [("hdr", NMHDR),
					("uBand", UINT),
					("wID", UINT),
					("rcChild", RECT),
					("rcBand", RECT)]

class RBHITTESTINFO(Structure):
	_fields_ = [("pt", POINT),
					("flags", UINT),
					("iBand", INT)]

class REBARBANDINFO(Structure):
	_fields_ = [("cbSize", UINT),
					("fMask", UINT),
					("fStyle", UINT),
					("clrFore", COLORREF),
					("clrBack", COLORREF),
					("lpText", LPSTR),
					("cch", UINT),
					("iImage", INT),
					("hwndChild", HANDLE),
					("cxMinChild", UINT),
					("cyMinChild", UINT),	 
					("cx", UINT),
					("hbmBack", HANDLE),
					("wID", UINT),
					# #if (_WIN32_IE >= 0x0400)"
					("cyChild", UINT),
					("cyMaxChild", UINT),
					("cyIntegral", UINT),
					("cxIdeal", UINT),
					("lParam", LPARAM),
					("cxHeader", UINT)
					]
	def __init__(self): self.cbSize=sizeof(self)
					
class REBARINFO(Structure):
	_fields_ = [("cbSize", UINT),
					("fMask", UINT),
					("himl", HANDLE)]






