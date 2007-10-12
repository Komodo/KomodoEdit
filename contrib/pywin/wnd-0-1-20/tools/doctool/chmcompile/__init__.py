


# project imports
## damn, hope relative imports come before 3.0, this is weird and nonsense !! 
from wnd.tools.doctool.chmcompile.header import *
from wnd.tools.doctool.chmcompile.index import Index
from wnd.tools.doctool.chmcompile.contents import Contents
from wnd.tools.doctool.chmcompile.project import Project
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

def GetHelpWorkshopPath():
	hive=reg.HKEY_LOCAL_MACHINE
	subkey = 'Software\Microsoft\Windows\CurrentVersion\App Paths\hhw.exe'
	try:
		hKey = reg.OpenKey(hive, subkey)
		name, data, type = reg.EnumValue(hKey, 1)
		reg.CloseKey(hKey)
		path=os_join(str(data), 'hhc.exe')
		if not os_isfile(path):
			raise IOError, 'MS Help Workshop compiler not found (hhc.exe)'
		return path
	except: raise IOError, 'MS Help Workshop not installed (required)'	
	



def WalkSorted(top, topdown=True, onerror=None):
	try:
        # Note that listdir and error are globals in this module due
        # to earlier import-*.
		names = os.listdir(top)
	except error, err:
		if onerror is not None:
			onerror(err)
		return

	dirs, nondirs = [], []
	for name in names:
		if os_isdir(os_join(top, name)):
			dirs.append(name)
		else:
			nondirs.append(name)

	dirs.sort()
	nondirs.sort()
	if topdown:
		yield top, dirs, nondirs
	for name in dirs:
		path = os_join(top, name)
		if not os_islink(path):
			for x in WalkSorted(path, topdown, onerror):
				yield x
		if not topdown:
			yield top, dirs, nondirs
	

#*********************************************************************
#********************************************************************
   
class ChmCompiler(object, Index, Contents, Project):
	def __init__(self):
		"""Compile a CHM help file. Requires MS Help Workshop
		to be installed.
		Sample use:
			c=ChmCompiler()
			path='path-to-folder-containing-my-html-files'
			c.InitProject(path)
			c.Compile()
				
		Note:
		MS Help Workshop clutters windows\temp with tempfiles. 
		"""
		self._hhwpath=GetHelpWorkshopPath()
		self._formats = ('.html', '.htm')
		self._defaulttitle= ' - Help'
		self.Reset()
			

	def Reset(self):
		"""Resets the compiler to default state."""
		self._defaulttitle= ' - Help'
		self._root=None
		self._projpath= None
		self._projdata=None
		self._data=None
		self._cmpfunc=None
		self._fKeepfiles=True
		self._errorlog=None
		self._fProjectStarted=False
		self._defaultFolderPage=None
		self._debug=False
		
	
	def _SetDefaultPage(self, root, files):
		tmpFiles = [i.lower() for i in files]
		dirname= os_split(root)[1].lower()
		n1=None
		n2=None
		for i in self._formats:
			try: n1= tmpFiles.index('%s%s' % (dirname, i))
			except: pass
			try: n2= tmpFiles.index('%s%s' % (self._defaultFolderPage, i))
			except: pass
	
		if self._defaultFolderPage=='foldername':
			if n2 != None: files.insert(0, files.pop(n2))
			else:
				if n1 != None: files.insert(0, files.pop(n1))
		elif self._defaultFolderPage != None:
			if n2 != None: files.insert(0, files.pop(n2))
			else:
				if n1 != None: files.insert(0, files.pop(n1))
		else: 
			if n1 != None: files.insert(0, files.pop(n1))
		
				
	
	def _SetupData(self, path, filelist=None):
		# TODO: check if all files are rooted at rootpath ??
		#		- os_normpath the paths
		if self._fProjectStarted:
			self._data=tempfile.TemporaryFile()
		
		if filelist:
			for i in filelist:
				try:
					i=i.strip()
					if not i: continue
					i=os_normpath(i)
					#and os_isfile(i)							\
					#and self._ISROOTED(i)
					if os_splitext(i)[1] in self._formats	\
					:
						self._data.write('%s\n' % i)
					else:
						# catch errors
						if self._errorlog2:
							msg=None
							if  not os_isfile(i):
								msg=='Invalid file %s' % i
							if os_splitext(i)[1] not in self._formats:
								msg='Invalid type %s' % i
							if  not self._ISROOTED(i):
								msg='Invalid root %s' % i
							if msg:
								print >> self._errorlog, msg
				except: pass
		else: 
			for root, dirs, files in WalkSorted(path):
				self._SetDefaultPage(root, files)
				for i in files:
					if os_splitext(i)[1] in self._formats:					
						#self._data.write('%s\n' % os_join(root, i).lower())
						self._data.write('%s\n' % os_join(root, i))
	
	
	
	def _PrintError(self, msg):
		if self._errorlog:	print >> self._errorlog, msg
	
	def _WriteErrorLog(self):
		if self._errorlog:
			fp=open(self._projdata['Error log file'], 'a')
			try:
				self._errorlog.seek(0)
				fp.write('\n <-- End Microsoft HTML Help Compiler log')
				fp.write('\n----------------------------------------\n')
				fp.write('\nPython %s script errors:\n\n' % self.__class__.__name__)
				for i in self._errorlog: fp.write(i)
			finally: fp.close()
		
	def _ISROOTED(self, path):
		if path[:len(self._root)]==self._root:
			return True
		return False
	
	#----------------------------------------------------------------------
	
	def InitProject(self, path, filelist=None, title=None, defaultfolderpage=None):
		#if not os_isdir(str(path)): raise 'invalid root dir: %s' % path
		self._fProjectStarted=True
		if defaultfolderpage:
			self._defaultFolderPage=defaultfolderpage.lower()
		
		self._root=os_normpath(path.lower().strip())
		name=os_split(path)[1]
		self._projpath= os_join(self._root, '%s.hhp' % name)
		
		self._windowdata=[]	## not used
		self._projdata={
			'Auto Index':'Yes',							# ??
			'Binary TOC':'Yes',
			'Enhanced decompilation':'Yes',		# ??
			'Compatibility':'1.1 or later',
			'Display compile progress':'Yes',
			'Full-text search':'Yes',
			'Default Window':'main',
			'Default Font':'Arial,8,0',
			'Compiled file': '%s.chm' % os_split(self._root)[1] or 'Untitled.chm',
			'Contents file': os_join(self._root, '%s.hhc' % name),
			'Index file': os_join(self._root, '%s.hhk' % name),
			'Default topic': None,
			'Title': title or '%s %s' % (os_split(self._root)[1], self._defaulttitle)  or 'Untitled',
			'Error log file': os_join(self._root, 'ErrorLog.log')
			}
		
		self._data=tempfile.TemporaryFile()
		self._errorlog=tempfile.TemporaryFile()
				
		#self._data=open('%s\\test.tmp' % path, 'w+')
		self._SetupData(path, filelist)
		self._data.seek(0)
		self._projdata['Default topic']=self._RELPATH(
												self._data.readline().strip())
		self._data.seek(0)
		

	def GetRoot(self): return self._root
	
	def GetFormats(self): return self._formats
	
	def GetProjectData(self): return self._projdata
	
	def GetDefaultTitle(self): return self._defaulttitle
	
	def SetTitle(self, title): self._projdata['Title']=Title
		

	def SetDefaultTopic(self, path):
		if '%s\n' % path not in self._data:
			raise 'no such file in project: %s' % path
		self._projdata['Default topic']=self._RELPATH(path)
		
				
	def SetFont(self, facename, size, charset=0):
		self._projdata['Default Font']='%s,%s,%s' % (facename, size, charset)
	
	def SetErrorLog(self, Bool):
		if Bool: pass
		else:
			self._projdata['Error log file']=None
			del self._errorlog
			self._errorlog=None
	
			
	def SetOutputFile(self, filepath):
		if not os_splitext(filepath)[1].lower()=='.chm':
			raise '*.chm file required'
		self._projdata['Compiled file']=filepath
	
	def SetKeepProjectFiles(self, Bool): self._fKeepfiles=Bool
	
	def SetCompFunc(self, func): self._cmpfunc=func
	
	def Compile(self):
		if not self._fProjectStarted: raise 'no project started'
		try:
			self.WriteContents()
			self.WriteIndex()
			self.WriteProject()
			path = QUOTE(self._hhwpath)
			projectfile = QUOTE(self._projpath)
			commandline = '%s %s' % (path, projectfile)
			sub= subprocess.Popen(args=commandline)
			sub.wait()
		finally:
			pass
			#self._data.close()
		
		if not self._fKeepfiles:
			# TODO log errors
			try:
				os.remove(self._projdata['Contents file'])
				os.remove(self._projdata['Index file'])
				os.remove(self._projpath)
			except: pass
		
		if self._errorlog: 
			self._WriteErrorLog()
		else:
			try:
				os.remove(os_join(self._root, 'ErrorLog.log'))
			except: pass
				
	def SetDebug(self):
		"""Does nothing else then to keep the tempfile used
		to create the contents.hhc. You find it as
		projectname/contents.hhc.tmp in the project folder.
		The file has the following format:
		0 0 0 item
		nFoldersToClose, boolOpenFolder, boolUseFolderIcon, relpath-of-item."""
		self._debug=True
	
#***************************************************
def COMP(f, l, n):
	
	if n=='COLORREF':
		return False
	return True

def test():
	path=r'c:\aaa'
	log=r'D:\_scr_\py\scripts\name\guis\chmcompile\log.log'
	path=r'D:\_scr_\py\scripts\name\guis\chmcompile\testdir'

	c = ChmCompiler()
	c.SetDebug()
	fp=open(log)
	try:
		c.InitProject(path, filelist=None)
		c.SetFont('Tahoma', 10)
	finally: fp.close()
	c.Compile()


#test()


		