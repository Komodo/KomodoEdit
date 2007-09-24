

import os, ConfigParser
from wnd.api import winpath
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

INIPATH= os.path.join(os.path.split(__file__)[0], 'expl.ini')


class Ini(ConfigParser.RawConfigParser):
	
	def __init__(self, mainframe):
		self.ini_sections= {
		'mainwindow': ('size', ),
		'dircombo': ('n_mru_items', ),
		'mru_dircombo': None, 
		'panes': None,
		'pane1': ('dir', ), 
		'pane2': ('dir', ),
		}
				
		ConfigParser.RawConfigParser.__init__(self)
		
		
		self.Main= mainframe
		
		try: self.read((INIPATH, ))
		except: pass

				
		## remove the stupid defaults.
		## Sorry, but this is a nonsense feature...
		if hasattr(self, '_defaults'):
			self._defaults= {}
		
				

	
	def GetMRU(self, section):
		if self.has_section(section):
			items=  dict(self.items(section))
			out= []
			for i in range(len(items)):
				try:
					out.append(items[str(i)])
				except: pass
			return out
		self.add_section(section) 
		
	
	def SetMRU(self, section, values):
		if self.has_section(section):
			self.remove_section(section) 
		self.add_section(section) 
		for n, i in enumerate(values):
			self.set(section, str(n), i) 
			
	
		
	def GetValue(self, section, name, default=None):
		if self.has_section(section):
			if self.has_option(section, name):
				return self.get(section, name)
		else:
			self.add_section(section)
		return default
	
	
	def SetValue(self, section, name, value):
		if not self.has_section(section):
			self.add_section(section) 
		self.set(section, name, value)
	
	def GetInt(self, section, name, default=None):
		if not self.has_section(section):
			self.add_section(section) 
		try:
			return self.getint(section, name)
		except:
			return default
		
	
	def Save(self):
		
		## keep ini clean
		sections= self.sections()
		for section in sections:
			if section not in self.ini_sections:
				self.remove_section(section)
			else:
				names= self.ini_sections[section] 
				options= self.options(section)
				if names:
					for option in options:
						if option not in names:
							self.remove_option(section, option) 
				
	
		
		if 1:
			## store cwds of the DirLists
			path= self.Main.DirList1.GetCwd(path=True)
			if not path:
				path= self.Main.DirList1.GetCLSIDL()
				if path:
					path= path[1]
				else: path= 'desktop'
			self.SetValue('pane1', 'dir', path)

			path= self.Main.DirList2.GetCwd(path=True)
			if not path:
				path= self.Main.DirList2.GetCLSIDL()
				if path:
					path= path[1]
				else: path= 'desktop'
			self.SetValue('pane2', 'dir', path)

		
			
		fp= open(INIPATH, 'w')
		try:
			self.write(fp)
		finally:
			fp.close()


