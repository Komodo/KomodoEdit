
from wnd import fwtypes
from wnd.controls.base import control
from wnd.controls.base.methods import ControlMethods
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
	

class RadioboxMethods:
	#-----------------------------------------------------------------	
	# message handlers	
	
	def onMESSAGE(self, hwnd, msg, wp, lp):
		if msg==fwtypes.WND_WM_NOTIFY:
			if wp==fwtypes.WND_NM_MSGREFLECT:
				msgr= fwtypes.WND_MSGREFLECT.from_address(lp)
				msgr.fReturn= self._base_fMsgReflect
				if msgr.msg==self.Msg.WM_COMMAND:
					if self.IsGrouped():
						self.onMSG(hwnd, "checked", self.GetCheckedRadiobox(), 0)
					else:
						if self.IsChecked():
							self.onMSG(hwnd, "checked", self.Hwnd, 0)
			return 0
			
		elif msg==self.Msg.WM_SETFOCUS:
			if self.IsGrouped():
				if wp not in self.GetGroup():
					self.onMSG(hwnd, "setfocus", wp, lp)
			else:	
				self.onMSG(hwnd, "setfocus", wp, lp)
		elif msg==self.Msg.WM_KILLFOCUS:
			if self.IsGrouped():
				if wp not in self.GetGroup():
					self.onMSG(hwnd, "killfocus", wp, lp)
			else:	
				self.onMSG(hwnd, "killfocus", wp, lp)
		
		elif msg==self.Msg.WM_DESTROY:
			self.onMSG(hwnd, "destroy", 0, 0)
			
				
	#-------------------------------------------------------------------------
	# methods
		
	def IsGrouped(self):
		return bool(self._client_group or self._client_OldMSGHandler) 
	def IsGroupAncestor(self): return bool(self._client_group) 		
	
	def GetGroup(self):
		if not self._client_group:
			raise RuntimeError("radiobox is not grouped")
		if self._client_OldMSGHandler:
			raise RuntimeError("sub radioboxes do not supply group information")
		return self._client_group
	
	def Group(self, *radioboxes):
		if not radioboxes:
			raise RuntimeError("no radioboxes specified")
		if self in radioboxes:
			raise RuntimeError("a radiobox can not group itsself")
		if self.IsGrouped(): 
			raise RuntimeError("radiobox is alreaddy grouped: %s" % self.Hwnd)
		self._client_group=[self.Hwnd, ]
		for i in radioboxes:
			if i.IsGrouped(): 
				raise RuntimeError("radiobox is alreaddy grouped: %s" % i.Hwnd)
			self._client_group.append(i.Hwnd)
			i.SetStyle('-group')
			i._client_OldMSGHandler=i.onMESSAGE
			i.onMESSAGE=self.onMESSAGE
		
	def Ungroup(self, *radioboxes):
			if not self.IsGroupAncestor(): 
				raise RuntimeError("radiobox is no groupe ancestor")
			self._client_group.remove(self.Hwnd)
			for i in radioboxes:
				if i.Hwnd != self.Hwnd:
					try: 
						self._client_group.remove(i.Hwnd)
						i.onMESSAGE=i._client_OldMSGHandler
						i._client_OldMSGHandler=None
						i.SetStyle('group')
					except:
						raise RuntimeError("radiobox is not grouped: (%s)" % i.Hwnd)
			if self._client_group:
				raise RuntimeError("Not all radioboxes found for ungrouping : (%s missing)" % len(self._client_group)) 
			
	def CheckRadiobox(self, Radiobox):
		if not self.IsGroupAncestor(): 
				raise RuntimeError("radiobox is no group ancestor")
		BST_UNCHECKED     = 0
		BST_CHECKED       = 1
		if not Radiobox: 
			for i in self._client_group:
				self.SendMessage(i, self.Msg.BM_SETCHECK,
											BST_UNCHECKED, 0)
				if self.SendMessage(i, 	self.Msg.BM_GETSTATE,
									0, 0) & BST_CHECKED:
					raise RuntimeError("could not uncheck radiobox: hwnd (%s)" % i)
		else:
			flag=False
			for i in self._client_group:
				if Radiobox.Hwnd==i:
					flag=True
					self.SendMessage(i, 
						self.Msg.BM_SETCHECK, BST_CHECKED, 0)
					if not self.SendMessage(i,  self.Msg.BM_GETSTATE, 0, 0) & BST_CHECKED:
						raise RuntimeError("could not check radiobox: hwnd (%s)" % i)
				else:
					self.SendMessage(i, self.Msg.BM_SETCHECK,
											BST_UNCHECKED, 0)
					if self.SendMessage(i, 	self.Msg.BM_GETSTATE,
									0, 0) & BST_CHECKED:
						raise RuntimeError("could not uncheck radiobox: hwnd (%s)" % i)
			if not flag:
				raise RuntimeError("no matching radiobox found in group")

 	
	def GetCheckedRadiobox(self):
		if not self.IsGroupAncestor(): 
				raise RuntimeError("radiobox is no groupe ancestor")
		BST_CHECKED       = 1
		hwnd= None 
		for i in self._client_group:
				if self.SendMessage(i, self.Msg.BM_GETSTATE,
								0, 0) & BST_CHECKED:
					hwnd= i
					break
		return hwnd
					
	def IsChecked(self):
		# BST_CHECKED       = 1
		return bool(self.SendMessage(self.Hwnd, self.Msg.BM_GETSTATE, 0, 0) & 1)
		
		
	def Check(self):
		BST_CHECKED       = 1
		self.SendMessage(self.Hwnd, self.Msg.BM_SETCHECK, BST_CHECKED, 0)
		if not self.IsChecked():
			raise RuntimeError("could not check radiobox")
	
	def Uncheck(self):
		BST_UNCHECKED     = 0
		self.SendMessage(self.Hwnd, self.Msg.BM_SETCHECK, BST_UNCHECKED, 0)
		if self.IsChecked():
			raise RuntimeError("could not uncheck radiobox")
	
	def Click(self):
		self.SendMessage(self.Hwnd, self.Msg.BM_CLICK, 0, 0)
	
	#------------------------------------------------------------------
	# overwritten methods
	# GetStyle/SetStyle needs some additional handling
	#
	def SetStyle(self, *styles):
		"""Sets the style for the checkbox.
		Same as the SetStyle method for other controls, except  
		The styles 'radiobutton', 'autoradiobutton'
		are mutually exclusive. You can not use the flags '-' and
		'~' on them.
		"""
		out = []
		st=('radiobutton', 'autoradiobutton')
		for i in styles:
			if i in st:
				if i=='radiobutton': style = 4
				elif i=='autoradiobutton': style = 9
				self.SendMessage(self.Hwnd, self.Msg.BM_SETSTYLE, style, 1)
			else:
				out.append(i)
			if out:
				ControlMethods.SetStyle(self, *out)


#**********************************************************************

class Styles:
	
	BS_RADIOBUTTON     = 4
	BS_AUTORADIOBUTTON = 9	
	BS_PUSHLIKE        = 4096	 # currently not working
		
	#BS_TEXT            = 0
	BS_ICON            = 64
	BS_BITMAP          = 128
	BS_LEFT            = 256
	BS_RIGHT           = 512
	BS_CENTER          = 768
	BS_TOP             = 1024
	BS_BOTTOM          = 2048
	BS_VCENTER         = 3072
	BS_MULTILINE       = 8192
	BS_NOTIFY          = 16384
	#BS_FLAT            = 32768		# ??

Styles.__dict__.update(control.control_styles.__dict__)
Styles.prefix += ['BS_', ]
	

class Msgs: 
	BST_UNCHECKED     = 0
	BST_CHECKED       = 1
	BST_FOCUS = 8
		
	BM_SETCHECK = 241
	BM_GETSTATE = 242
	BM_SETSTATE = 243
	BM_SETSTYLE = 244
	BM_CLICK    = 245
	BM_GETIMAGE = 246
	BM_SETIMAGE = 247
	
Msgs.__dict__.update(control.control_msgs.__dict__)


class Radiobox(RadioboxMethods, control.BaseControl, ControlMethods):
		
	def __init__(self, parent, title, x, y, w, h, *styles):
		self.Style= Styles
		self.Msg= Msgs 
		
		
		# make shure one of the BS_* styles is set
		flag = False
		if 'radiobutton' in styles: flag=True
		elif 'autoradiobutton' in styles: flag=True
		if flag: styles += 'subclass', 'group'
		else: styles += 'autoradiobutton', 'subclass', 'group'
		
		control.BaseControl.__init__(self, parent, "Button", title, x, y, w, h, *styles)
		
		self._client_OldMSGHandler=None
		self._client_group=[]
				
		
class RadioboxFromHandle(RadioboxMethods, control.ControlFromHandle, ControlMethods):
		
	def __init__(self, hwnd, *styles):
		self.Style= Styles
		self.Msg= Msgs 
		
		
		styles += 'subclass',
		control.ControlFromHandle.__init__(self, hwnd, *styles)
			
		self._client_OldMSGHandler=None
		self._client_group=[]
		



#***********************************************
