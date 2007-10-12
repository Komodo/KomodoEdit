

from wnd.api import winpath
from wnd.controls.combobox import Combobox
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::


class ExplDircombo(Combobox):
	
	def __init__(self, mainframe):
		
		self.Main= mainframe
		self.n_mru_items= self.Main.Ini.GetInt('dircombo', 'n_mru_items', default=10)
		self.maxW= 0
						
				
		## TODO
		## calculate combobox height for nItems
		Combobox.__init__(self, mainframe, 0, 0, 0, 150, 'dropdown', 'vscroll', 'hscroll')

		self.SetExtendedUI(True)

		## restore MRU list
		mru= self.Main.Ini.GetMRU('mru_dircombo')
		if mru:
			for n, i in enumerate(mru):
				if n >= self.n_mru_items: 
					break
								
				if winpath.Exists(i):
					self.maxW= max(self.GetTextExtend(i)[0], self.maxW)
					self.Item(i)
			
			self.maxW += self.GetTextExtend('W')[0]	## arbitrary
			Combobox.SetScrollWidth(self, self.maxW)
			#self.SetScrollWidth()
		
		
		self.ed= self.GetEditControl()
		self.ed.onMSG= self.onMSG


	
	def onMSG(self, hwnd, msg, wp, lp):
				
		if msg=='getdlgcode':
			lp.append('wantallkeys')
			return lp
		
		elif msg=='return':
			
			refresh= False
			path= self.GetText()
			spec= winpath.GetFileName(path)
			
			if self.IsDroppedDown():
				self.CloseDropdown()
			
			if spec:
				if spec.startswith('*'):
					path= winpath.RemoveFileSpec(path)
					self.Main.activePane.SetFilespec(spec)
					if len(path)==2 and path[1]==':':
						path= '%s\\' % path
			else:
				## path may be spec
				if path.startswith('*'):
					self.Main.activePane.SetFilespec(path)
					refresh= True
				
			if refresh:	
				self.Main.activePane.Refresh()
			else:
				if self.Main.activePane.ListDir(path):
					self.SetText(path, self.Main.activePane.GetFilespec()[0])
				else:	
					self.Beep('asterisk')
			
			
	
	def SetScrollWidth(self):
			self.maxW= 0
			for i in self:
				text= self.GetItemText(i)
				self.maxW= max(self.GetTextExtend(text)[0], self.maxW)
			self.maxW += self.GetTextExtend('W')[0]	## arbitrary
			Combobox.SetScrollWidth(self, self.maxW)	
		
	
	
	def Expl_SaveState(self):
		
		self.Main.Ini.SetValue('dircombo', 'n_mru_items', self.n_mru_items)
		out= []
		for i in self:
			out.append(self.GetItemText(i))
		self.Main.Ini.SetMRU('mru_dircombo', out)
		

	
	def SetText(self, path, filespec):
			# manages MRU items and sets scrollable width
			if path:
				
				out= []
				for i in self:
					if self.GetItemText(i).lower()== path.lower():
						out.append(i)
				
				if out:
					for i in reversed(out):
						self.RemoveItem(i)
								
				if path.endswith('\\'):
					Combobox.SetText(self, '%s%s' % (path, filespec))
				else:
					Combobox.SetText(self, '%s\\%s' % (path, filespec))
				
				self.InsertItem(0, path)
				
				
				if len(self) > self.n_mru_items:
					self.RemoveItem(self.n_mru_items)
			
			else:
				Combobox.SetText(self, filespec)
			
			self.SetScrollWidth()
			
			