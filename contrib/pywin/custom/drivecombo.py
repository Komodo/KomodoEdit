"""

TODO
			- winos.GetDriveList fails sometimes
			- limit dropdown height if style 'adjusth' is used. (dono if 26 drives listed 
				cause trouble. Anyone here for testing ??)
			- implement flags to exclude drive types ??
										

NOTES			
			- comboboxes do not send any reliable notification when being enabled or
				disabled, so no special drawing is done here
			- SetFont/GetFont not implemented; 
				If the user sets a non-default font this control will mess up. 
			- item offets are calculated as follows:
				icon -> text =   font.GetAverageCharWidth
				item -> nextItem =   font.GetAverageCharWidth/2

"""

from wnd import gdi
from wnd.api import shell
from wnd.api import winos
from wnd.controls.imagelist import Imagelist
from wnd.controls.helpers import ParseStylesSZ 
from wnd.custom.odcombobox import ODCombobox
from wnd.wintypes import user32

#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

SZ_MSG_SHELLNOTIFY= "wnd_DriveCombo_notify"

STYLES= ('adjusth',
					'largeicon',
					'monitorchanges',
					'showdetails',
					'smallicon',
					)

#**********************************************************************************
#**********************************************************************************

class Data(object):
	__slots__= ('Combobox', 'Imagelist', 'Shell', 'ShellNotify', 'msgNotify', 'styles', 'isNotifyRegistered')
	def __init__(self):
		self.Combobox= None
		self.Imagelist= None
		self.Shell= None
		self.ShellNotify= None
		
		self.msgNotify= None
		self.isNotifyRegistered= False
		self.styles= []


	def Close(self):
		try: self.Shell.Close()
		except: pass
		try: self.ShellNotify.Close()
		except: pass
		try: self.Imagelist.Close()
		except: pass

	
	def SHN_StartMonitor(self):
		if not self.isNotifyRegistered:
			self.Shell.OpenSpecialFolder(shell.CLSIDL_DRIVES)
			pIdl= self.Shell.GetCwd()
			self.ShellNotify.Register(pIdl, 'mediainserted', 'mediaremoved', 'driveremoved', 'driveadd')
			shell.PidlFree(pIdl)
			self.Shell.SetCwd(None)
			self.isNotifyRegistered= True
	
	def SHN_StopMonitor(self):
		if self.isNotifyRegistered:
			self.ShellNotify.Close()
			self.isNotifyRegistered= False
		
	
	
	def _printPidls(self, msg, wp, lp):
		## helper for 'shellnotify' message
		if lp==None: return
		out= []
		if isinstance(lp, tuple):
			if lp[0]: out.append(self.Shell.GetParseName(lp[0]))
			else: out.append(None)
			if lp[1]: out.append(self.Shell.GetParseName(lp[1]))
			else: out.append(None)
		else:
			if lp: out.append(self.Shell.GetParseName(lp))
			else: out.append(None)
		print msg, wp, out
		
#**********************************************************************************
#**********************************************************************************

class DriveCombo(object):

	def __init__(self, parent, x, y, w, h, *styles):
		
		
		self._custom_Data= Data()
				
		for i in styles:
			if i not in STYLES:
				raise ValueError, "invalid style: %s" % i
		self._custom_Data.styles= styles
								
		self.Hwnd= 0
		
		self._custom_Data.Combobox=ODCombobox(parent)
		self._custom_Data.Combobox.onMSG= self.onMESSAGECombobox
		self._custom_Data.Combobox.InitCombobox(x, y, w, h, 'ownerdrawvariable', 'hasstrings', 'dropdownlist')
		self.Hwnd= self._custom_Data.Combobox.GetContainer().Hwnd
		
		self._custom_Data.Shell= shell.ShellNamespace()
		self._custom_Data.msgNotify= user32.RegisterWindowMessageA(SZ_MSG_SHELLNOTIFY)
		self._custom_Data.ShellNotify= shell.ShellNotify(
													self._custom_Data.Combobox, 
													self._custom_Data.msgNotify, 
													self.onMESSAGECombobox)
		self._custom_Data.Combobox.HandleMessage(self._custom_Data.msgNotify)
		
		
		if 'monitorchanges' in self._custom_Data.styles:
			self._custom_Data.SHN_StartMonitor()
		
		self.Refresh()
		

		
	#--------------------------------------------------------------------------------------------
	# message handler
	
	def onMESSAGECombobox(self, hwnd, msg, wp, lp):
		
		if msg=="measureitem":
			#if lp.itemID==0xFFFFFFFF: return
			if 'largeicon' in self._custom_Data.styles: 
				icoH=gdi.GetSystemMetric('cyicon')
			else: 
				icoH=gdi.GetSystemMetric('cysmicon')
			dc=gdi.ClientDC(self._custom_Data.Combobox.Hwnd)
			font= dc.GetFont()
			lp.itemHeight = max(icoH, font.GetMaxHeight(dc))+	\
											(font.GetAverageCharWidth(dc)/2)
			font.Close()
			dc.Close()
		
		
		elif msg=="drawitem":
			
			# do not process combobox selection field
			if lp.itemID==0xFFFFFFFF: return
			dc=gdi.DCFromHandle(lp.hDC)
			font= dc.GetFont()
			
			if  lp.itemAction == lp.FOCUSCHANGE:
				if not lp.itemState & lp.FOCUS:
					dc.DrawFocusRect(lp.rcItem)
			elif lp.itemAction == lp.SELECTCHANGE or lp.itemAction == lp.DRAWENTIRE:
				if lp.itemState & lp.SELECTED:
					dc.SetTextColor(gdi.GetSysColor('highlighttext'))
					dc.SetBkColor(gdi.GetSysColor('highlight'))
				else:
					dc.SetTextColor(gdi.GetSysColor('windowtext'))
					dc.SetBkColor(gdi.GetSysColor('window'))
				#
				# draw text
				text= self._custom_Data.Combobox.GetItemText(lp.itemID)
				w, h= font.GetTextExtend(dc, text)
				icoW, icoH = self._custom_Data.Imagelist.GetIconSize()
				y= lp.rcItem.top + ((lp.rcItem.bottom-lp.rcItem.top- (h))/2)
				font.TextOutEx(dc, text, lp.rcItem.left+icoW+(font.GetAverageCharWidth(dc)),
									y, 'opaque', rect=lp.rcItem)
				#
				# draw icon
				y= lp.rcItem.top + ((lp.rcItem.bottom-lp.rcItem.top- (icoH))/2)
				self._custom_Data.Imagelist.Draw(dc, lp.itemID, lp.rcItem.left, y)
				#
				# draw focus rect
				if lp.itemState & lp.FOCUS:
					dc.DrawFocusRect(lp.rcItem)
			dc.Close()
			font.Close()
	
		
		elif msg==self._custom_Data.msgNotify:
			self._custom_Data.ShellNotify.HandleMessage(hwnd, msg, wp, lp)
			return 0
		
		elif msg=="shellnotify":
			#self._custom_Data._printPidls(msg, wp, lp)
			
			if wp=="mediainserted":
				self.Refresh()
				if lp:
					self.onMSG(hwnd, "shellnotify", "mediainserted", self._custom_Data.Shell.GetParseName(lp))
		
			elif wp=="mediaremoved":
				self.Refresh()
				if lp:
					self.onMSG(hwnd, "shellnotify", "mediaremoved", self._custom_Data.Shell.GetParseName(lp))
				
			elif wp=="driveadd":
				self.Refresh()
				if lp:
					self.onMSG(hwnd, "shellnotify", "driveadd", self._custom_Data.Shell.GetParseName(lp))
		
			elif wp=="driveremoved":
				self.Refresh()
				if lp:
					self.onMSG(hwnd, "shellnotify", "driveremoved", self._custom_Data.Shell.GetParseName(lp))
				
		
		
		elif msg=="select":
				data= self._custom_Data.Combobox.GetText()
				self.onMSG(hwnd, "driveselected", 0, data[:data.find(':')+1])
				
		else:
			if msg=="destroy":
				self._custom_Data.Close()
			
			## default
			self.onMSG(hwnd, msg, wp, lp)
				
							
	def onMSG(self,  hwnd, msg, wp, lp):	
		# overwrite
		pass
		
					
	#------------------------------------------------------------------------------------------
	# DriveCombo methods
	
	def Refresh(self):
		
		if self._custom_Data.Imagelist: self._custom_Data.Imagelist.Close()
		self._custom_Data.Combobox.Clear()
		drives= winos.GetDriveList()		##
		if drives:
			if "largeicon" in self._custom_Data.styles: 
				iconSize= 'largeicon'
			else: 
				iconSize= 'smallicon'
			ico=gdi.FileIcon(drives[0], iconSize)
			icoW, icoH=ico.GetSize()
			self._custom_Data.Imagelist= Imagelist(icoW, icoH, len(drives), 0, 'color16', 'mask')
			self._custom_Data.Imagelist.AddIcons(ico)
			for i in drives[1:]:
				self._custom_Data.Imagelist.AddIcons(gdi.FileIcon(i, iconSize))
			
		if "showdetails" in self._custom_Data.styles:
			for i in drives: 
				if i == 'a:\\' or i== 'b:\\':
					self._custom_Data.Combobox.Item('%s   [3\xBD floppy]' % i.rstrip('\\'))
				else:
					try:
						name= winos.GetVolumeInfo(i)[0]
						self._custom_Data.Combobox.Item('%s   [%s -%s-]' % (i.rstrip('\\'),name,  winos.GetDriveInfo(i).lower()))
					except: 				
						self._custom_Data.Combobox.Item('%s   [%s]' % (i.rstrip('\\'), winos.GetDriveInfo(i).lower()))
		else: 
			for i in drives: self._custom_Data.Combobox.Item(i.rstrip('\\'))
		#
		# adjust selection field height of the hosted combobox
		# ...set some limit here ??
		dc= gdi.ClientDC(self._custom_Data.Combobox.Hwnd)
		font= dc.GetFont()
		baseOffset= font.GetAverageCharWidth(dc) / 2
		self._custom_Data.Combobox.SetItemHeight(icoH + baseOffset, -1)
		
		if "adjusth" in self._custom_Data.styles:
			n= len(self._custom_Data.Combobox)
			if n:
				rc=self._custom_Data.Combobox.GetWindowRect()
				h= n* self._custom_Data.Combobox.GetItemHeight(1) + (rc.bottom-rc.top)
				self._custom_Data.Combobox.SetWindowSize(rc.right-rc.left, h)
				
		dc.Close()
		font.Close()
		# finally: make shure there is a selection
		try: self._custom_Data.Combobox.Select(0)	
		except: pass
	
	
	def GetDrive(self):
		drv= self._custom_Data.Combobox.GetText()
		if drv:
			try: return drv[:drv.find(':')+1]
			except: pass

	def SelectDrive(self, drive):
		if isinstance(drive, (str, unicode)):
			return self._custom_Data.Combobox.SelectItemText(drive, -1)
		elif isinstance(drive, (int, long)): return self._custom_Data.Combobox.Select(drive)

		
	def SetSelectionFieldHeight(self, h):
		self._custom_Data.Combobox.SetItemHeight(h, -1)
		rc= self._custom_Data.Combobox.GetWindowRect()
		self._custom_Data.Combobox.SetWindowSize(rc.right-rc.left, h)
	
	def GetSelectionFieldHeight(self): 
		return self._custom_Data.Combobox.GetItemHeight(-1)
	
	
	def GetMinSelectionFieldSize(self):
		dc=gdi.ClientDC(self._custom_Data.Combobox.Hwnd)
		font= dc.GetFont()
		maxW= 0
		
		for i in self._custom_Data.Combobox:
			w, h= font.GetTextExtend(dc, self._custom_Data.Combobox.GetItemText(i))
			maxW = max(maxW, w)
		font.Close()
		dc.Close()
		icoW, icoH = self._custom_Data.Imagelist.GetIconSize()
		maxH = max(icoH, h)
		return maxW + icoW + (icoW/2) +					\
					gdi.GetSystemMetric('cyhscroll') +	\
					(gdi.GetSystemMetric('cyedge') * 2) +1, maxH

	#-----------------------------------------------------------------------------------	
	
	def GetStyle(self): return self._custom_Data.styles
	
	
	def SetStyle(self, *styles):
		self._custom_Data.styles= ParseStylesSZ(STYLES,	self._custom_Data.styles, styles)
		
		if 'largeicon' in self._custom_Data.styles:
			if (gdi.GetSystemMetric('cxicon'), gdi.GetSystemMetric('cyicon')) != \
				self._custom_Data.Imagelist.GetIconSize():
				self._custom_Data.Imagelist= SystemImagelist('large')
				refresh= True
		else:
			if (gdi.GetSystemMetric('cxsmicon'), gdi.GetSystemMetric('cysmicon')) != \
				self._custom_Data.Imagelist.GetIconSize():
				self._custom_Data.Imagelist= SystemImagelist('small')
				refresh= True
					
		if 'monitorchanges' in self._custom_Data.styles:
			self._custom_Data.SHN_StartMonitor()
		else:
			self._custom_Data.SHN_StopMonitor()
				
		if refresh:
			self.Refresh()

	
	def SetWindowPosAndSize(self, x, y, w, h):
		rc= self._custom_Data.Combobox.GetWindowRect()
		self._custom_Data.Combobox.SetWindowSize(rc.right-rc.left, h)
		rc= self._custom_Data.Combobox.GetContainer().GetWindowRect()
		self._custom_Data.Combobox.GetContainer().SetWindowPosAndSize(x, y, w, rc.bottom-rc.top)
	
	def SetWindowSize(self, w, h):
		rc= self._custom_Data.Combobox.GetWindowRect()
		self._custom_Data.Combobox.SetWindowSize(rc.right-rc.left, h)
		rc= self._custom_Data.Combobox.GetContainer().GetWindowRect()
		self._custom_Data.Combobox.GetContainer().SetWindowSize(w, rc.bottom-rc.top)
	
	def OffsetWindowSize(self, offsW, offsH):
		self._custom_Data.Combobox.OffsetWindowSize(0, offsH)
		self._custom_Data.Combobox.GetContainer().OffsetWindowSize(offsW, 0)
	
	
	def OffsetWindowPos(self, offsX, offsY):
		return self._custom_Data.Combobox.GetContainer().OffsetWindowPos(offsX, offsY)
	def SetWindowPos(self, x, y):
		return self._custom_Data.Combobox.GetContainer().OffsetWindowPos(x, y)
	
	def GetItemHeight(self, i): return self._custom_Data.Combobox.GetItemHeight()
	
	def GetDropdownRect(self): 
		return self._custom_Data.Combobox.GetDropdownRect()	
	
	def GetWindowRect(self): 
		return self._custom_Data.Combobox.GetContainer().GetWindowRect()	
	
	def GetClientRect(self): 
		return self._custom_Data.Combobox.GetContainer().GetClientRect()
	
	
	def GetCombobox(self):
		return self._custom_Data.Combobox
	
	def GetContainer(self):
		return self._custom_Data.Combobox.GetContainer()
			
	def Enable(self): return self._custom_Data.Combobox.Enable()
	def Disable(self): return self._custom_Data.Combobox.Disable()
	def IsEnabled(self): return self._custom_Data.Combobox.IsEnabled()
	
	def Show(self): return self._custom_Data.Combobox.GetContainer().Show()
	def Hide(self): return self._custom_Data.Combobox.GetContainer().Hide()
	def IsVisible(self): return self._custom_Data.Combobox.GetContainer().IsVisible()
	
	def HasExtendedUI(self): return self._custom_Data.Combobox.HasExtendedUI()
	def SetExtendedUI(self, Bool): 
		return self._custom_Data.Combobox.SetExtendedUI(Bool)

	
	
	
	


	