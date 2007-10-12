"""
TODO
	
	::compiler-logfile:: is no longer used

"""

from wnd.tools.doctool.header import *
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

class DocParser(object):
	def __init__(self, path, globaldata):
		
		self.globaldata=globaldata.copy()
		fp=open(path, 'r')
		try: self.data=fp.read().replace('\r', '').split('\n')
		finally: fp.close()
		self.isroot=False
		self.projectfile=path
		self.path=os_dirname(path)
		self.sites={}
		self.sitelog=[]
		self.RxDefsPat =None
		
		self.options={KW_DEFPAGE: 'contents', 
							KW_TABWIDTH: self.globaldata['tabwidth']}
		self.contents={
			'name': os_basename(self.path),
			'path': os_join(self.path, 'contents.html'),
			'sites':[],
			'folders':[],
			}
		self.cmp_options={
			KW_CMP_FONT: '', 
			KW_CMP_DEFTOPIC: '',
			KW_CMP_OUTFILE:'%s\\%s.chm' % (self.path, os_basename(self.path)),
			KW_CMP_KEEPPROJ:True,
			KW_CMP_LOG:True,
			KW_CMP_ERRLOG:True,
			}
		
		# setup keywords
		self.kw={
			KW_ROOT:  "../"*self.path[len(self.globaldata['root']):
												].count(os.sep),
			KW_ROOTSITE: self.globaldata['rootsite']							\
									or '%s.html' % self.GetDefaultPage(),
			KW_ROOTSITENAME: self.globaldata['rootsitename']		\
											or self.GetName(),
			
			KW_UPDIR: self.globaldata['updirsite']									\
								and '../%s.html' % self.globaldata['updirsite']	\
								or None,
			KW_UPDIRNAME: self.globaldata['updirname']					\
										and self.globaldata['updirname']					\
										or None,
			KW_CWDIRNAME:os_basename(self.path),
			KW_NEXTSITE:None,
			KW_NEXTSITENAME:None,
			KW_PREVSITE:None,
			KW_PREVSITENAME:None,
			}
		
		self._Tokenize()
		self._GetOptions()
		self._GetDefs()
		defpage=self.GetDefaultPage()
		self.kw[KW_CWDIR]='%s.html' % defpage
		if not self.kw[KW_UPDIR]:
			self.isroot=True
			self.kw[KW_UPDIR]='../%s' % self.kw[KW_CWDIR]
			self.kw[KW_UPDIRNAME]=defpage

		self._GetSites()
		self._GetContentsData()
		self._WriteSiteLog()	
		self._ParseSubdirs()	 # before writing contents
		self._WriteSites()	 #->	self._WriteContents()
		self._WriteFolders()
		
		if self.isroot:
			self._WriteCss(self.path)
						
			
	def _GetToken(self, line):
		"""Splits a line in token, token name-and returns it if a
		token was found."""
		test = line.strip()
		test=test.split(None, 1)
		if test:
			if test[0] in TOKENS:
				if len(test)==2: return test
				else: return test[0], ''
		return False
	
	def _GetComment(self, line):
		"""Checks if a line is a comment. Resturn value is True if it
		is one, the otherwise the line with comments escaped is
		returned."""
		if '#' in line:
			test=line.lstrip()
			if test.startswith('#'):
				return True
			line=RxCommentsPat.subn(self.RxCommentsProc, line)[0]
		return line
			
			
	def _IsLegalName(self, name):
		"""Checks if <::item::> name contains any illegal chars."""
		flag=True
		for i in ILLEGALCHARS:
			if i in name:
				flag=False
				break
		return flag
		
	
	def _Tokenize(self):
		tmpData, currentToken = [], []
		tokenData = ''
		lineno=0
		for i in self.data:
			lineno += 1
			if i:
				i = self._GetComment(i)
				if i==True: continue
				token = self._GetToken(i)
				if token:
					token, name = token
					name = name.strip()
					if currentToken: 
						currentToken[3] = tokenData.lstrip()
						tmpData.append(currentToken)
						currentToken=[]
						tokenData = ''
					currentToken += lineno, token, name, None
				else: 
					tokenData = '%s\n%s' % (tokenData, i)
			else:
				# consereve linefeeds (<pre></pre>)
				if currentToken:
					tokenData = '%s\n' % tokenData
		
		# finalize
		if currentToken: 
			currentToken[3] = tokenData.lstrip()
			tmpData.append(currentToken)
		self.data = tmpData
		
		return ERR_OK
	
	
	def _GetDefs(self):
		"""gather and re sub defs"""
		defs={}
		for lineno, token, name, data in self.data:
			if token==KW_DEF:
				defs[name]=data
			elif token==KW_HEADER:
				defs[token]=data
			elif token==KW_FOOTER:
				defs[token]=data
		if defs:
			self.globaldata['defs']=defs
		if self.globaldata['defs']:
			pat=[]
			for i in self.globaldata['defs'].keys():
				pat.append(sre.escape(i))
			self.RxDefsPat=sre.compile(
				r'(\\?)(%s)' % '|'.join(pat), sre.M)
						
	
	def error(self, value, lineno='?'):
		print >> sys.stderr, '''error:
		in: %s
		line: %s
			%s
		''' % (self.projectfile, lineno, value)
	
	
	def _GetSites(self):	
		"""Gathers all sites defined"""
		self.sites={None:[('contents', None), ]}	# contents header here	
		self.folders= {}
		
		lastfolder=None
		counter1=0
		counter2=0
		for lineno, token, name, data in self.data:
			if token==KW_SITE:
				lastfolder=None
				if not name:
					counter1 += 1
					name='untitled-%s' % counter1
				
				if not self._IsLegalName(name):
					self.error("illegal char in sitename: '%s'" % name, lineno)
				elif len(os_join(self.path, name)) > MAX_PATH:
					self.error("max path exceeded: '%s'" % name, lineno)
				else:
					self.sites[lastfolder].append([name,  data])
					
			elif token==KW_FOLDER:
				if not name:
					counter1 += 1
					name='untitled-%s' % counter1
				
				if not self._IsLegalName(name):
					self.error("illegal char in foldername: '%s'" % name, lineno)
				elif len(os_join(self.path, name)) > MAX_PATH:
					self.error("max path exceeded: '%s'" % name, lineno)
					lastfolder=-1	# error
				else:	
					lastfolder=name
					self.folders[lastfolder]=[['contents', data]]
			
			elif token==KW_ITEM:
				if not name:
					counter2 += 1
					name='untitled-%s' % counter2
				if not self._IsLegalName(name):
					self.error("illegal char in folder item: '%s'" % name, lineno)
				elif lastfolder and lastfolder != -1:
					if len(os_join(self.path, name)) > MAX_PATH:
						self.error("max path exceeded: '%s'" % name, lineno)
					else:
						self.folders[lastfolder].append([name, data])
				elif not lastfolder:
					self.error("item without folder: %s" % name, lineno)
					 # error: item without folder
					
		for i in self.folders.values():
			i.sort(self.sortfolders)
		
		for i in self.sites.values():
			i.sort(self.sortsites)
		
		self.sites.update(self.folders)
				
	#----------------------------------------------------------------
	def sortfolders(self, x1, x2):
		if x1[0].lower()=='contents':
			return -1
		elif x2[0].lower()=='contents':
			return 1
		return cmp(x1[0].lower(), x2[0].lower())	
		
	
	def sortsites(self, x1, x2):
		if x1[0].lower()==self.GetDefaultPage().lower():
			return -1
		elif x2[0].lower()==self.GetDefaultPage().lower():
			return 1
		return cmp(x1[0].lower(), x2[0].lower())	
		
	#------------------------------------------------------------------

	def _GetOptions(self):
		"""Gathers data for ...options"""
		for lineno, token, value, data in self.data:
			if token in COMPILEROPTIONS:
				self.cmp_options[token]=MakeValue(token, value)
			elif token in OPTIONS:
				self.options[token]=MakeValue(token, value)
	
	def _GetContentsData(self):
		"""Gathers data for contents page and sitelog"""
		for folder, sitelist in self.sites.items():
			if folder:
				self.contents['folders'].append(( '%s/contents.html' % folder, folder))
				for i in sitelist:
					self.sitelog.append(os_join(self.path, folder, '%s.html' % i[0]))
			else:	
				for i in sitelist:
					sitename= '%s.html' % i[0]
					if i[0] !='contents':
						self.contents['sites'].append((sitename, i[0]))
					self.sitelog.append(os_join(self.path, sitename))
			
			
	
	def _ParseSubdirs(self):	
		"""recurse into subdirs"""
		dirlist=[os_join(self.path, i) for i in os.listdir(self.path) 
					if os_isdir(os_join(self.path, i))]
		dirlist.sort()
		for i in dirlist:
			tpl=[os_join(i, x) for x in os.listdir(i) 
					if os_isfile(os_join(i, x)) 
					and os_splitext(x)[1].lower() == '.dtpl']
			if tpl:
				tpl.sort()
				if len(tpl) > 1:
					self.error("multiple templates found in directory: %s" % i)
					
				# create a new parser for subsequent templates
				self.globaldata['updirsite']=self.GetDefaultPage()
				self.globaldata['updirname']=self.GetName()
				self.globaldata['tabwidth']=self.GetTabWidth()
				
				p=DocParser(tpl[0], self.globaldata)
				name=p.GetName()
				self.contents['folders'].append(
					('%s/%s.html' % (name, p.GetDefaultPage()), 
					name))
				
	#----------------------------------------------------------------------
	# regex stuff
	
	def RxCommentsProc(self, RxMatches):
		comment=RxMatches.groups()[1]
		if RxMatches.groups()[0]:
			return comment
		return comment
		
	def RxDefsProc(self, RxMatches):
		token=RxMatches.groups()[1]
		if RxMatches.groups()[0]:
			return token
		if token in self.globaldata['defs']:
			# replace keywords in def
			return RxTokensPat.subn(
						self.RxTokensProc,
						self.globaldata['defs'][token])[0] or ''
		return token
			
	def RxTokensProc(self, RxMatches):
		token=RxMatches.groups()[1]
		if RxMatches.groups()[0]:
			return token
		if token in self.kw:
			return self.kw[token] or ''
		return token
		
	def RxData(self, data):
		if data:
			# bugfix here, 
			# 1. substitute defs
			# 2. substitute escapes
			# was vice versa
			if self.globaldata['defs']:
				data= self.RxDefsPat.subn(self.RxDefsProc, data)[0]
			data=data.replace('\t', ' '*self.GetTabWidth())
			data= RxTokensPat.subn(self.RxTokensProc, data)[0]
			if self.globaldata['callback']:
				try: data=self.globaldata['callback'](data)
				except:
					self.error("callback error")
					self.globaldata['callback']=None

					# error: invalid translator
					pass
		return data
		
	#----------------------------------------------------------------------
	def _WriteCss(self, path):
		"""Writes default.css"""
		path = '%s\\default.css' % path
		fp=open(path, 'w')
		try: fp.write(CSS)
		finally: fp.close()
	
	
	def _WriteContents(self):
		"""writes a contents page"""
		# get contents headers
		hd1=None
		hd2=None
		for lineno, token, name, data in self.data:
			if token==KW_CTS_HDR1: hd1=name, data
			elif token==KW_CTS_HDR2: hd2=name, data
					
		fp=open(self.contents['path'], 'w+')
		try:
			
			fp.write(HEADER(self.contents['name'], self.kw[KW_ROOT]))
			if KW_HEADER in self.globaldata['defs']:
				fp.write(self.RxData(
							self.globaldata['defs'][KW_HEADER]))
			
			if hd1:
				if hd1[0]: 
					data=self.RxData(hd1[0])
					fp.write(H2 % (data, data))
				if hd1[1]: fp.write(self.RxData(hd1[1]))
			else:
				title='%s contents' % self.contents['name']
				fp.write(H2 % (title, title))
			fp.write(P)
			for site, name in self.contents['sites']:
				fp.write(HREF % (site, name))
			if hd2:
				if hd2[0]: 
					data=self.RxData(hd2[0])
					fp.write(H2 % (data, data))
				if hd2[1]: fp.write(self.RxData(hd2[1]))
			else:
				title='%s modules' % self.contents['name']
				fp.write(H2 % (title, title))
			fp.write(P)
			for site, name in self.contents['folders']:
				fp.write(HREF % (site, name))
			
			if KW_FOOTER in self.globaldata['defs']:
				fp.write(self.RxData(
							self.globaldata['defs'][KW_FOOTER]))
			fp.write(FOOTER)
		finally: fp.close()
	

	
	def _WriteSite(self, path, name, data):
		"""helper method: writes a site"""
		
		fp=open(path, 'w+')
		try: 
			fp.write(HEADER(name, self.kw[KW_ROOT]))
			if KW_HEADER in self.globaldata['defs']:
				fp.write(self.RxData(
							self.globaldata['defs'][KW_HEADER]))
			fp.write(H2 % (name, name))
			
			if 	data:
				fp.write(	self.RxData(data))
			if KW_FOOTER in self.globaldata['defs']:
				fp.write(self.RxData(
							self.globaldata['defs'][KW_FOOTER]))
			fp.write(FOOTER)
		finally: fp.close()
		
	
	def _WriteSites(self):
		"""writes all sites found"""
		sites = self.sites.pop(None)
		oldupdirsite=self.kw[KW_UPDIR]
		oldupdirname=self.kw[KW_UPDIRNAME]
		if self.isroot:
			self.kw[KW_UPDIR]=None
			self.kw[KW_UPDIRNAME]=None
		for n, i in enumerate(sites):
			name, data= i
			if n == 1:
				# updir is defaultpage for all subsequent siles
				self.kw[KW_UPDIR]=self.kw[KW_CWDIR]
				self.kw[KW_UPDIRNAME]=self.kw[KW_CWDIRNAME]

				self.kw[KW_PREVSITE]= '%s.html' % sites[n-1][0]
				self.kw[KW_PREVSITENAME]=sites[n-1][0]
			try: 
				self.kw[KW_NEXTSITE]= '%s.html' % sites[n+1][0]
				self.kw[KW_NEXTSITENAME]=sites[n+1][0]
			except: 
				self.kw[KW_NEXTSITE]= '%s.html' % sites[0][0]
				self.kw[KW_NEXTSITENAME]=sites[0][0]
			
			if name=='contents': self._WriteContents()
			else:
				self._WriteSite(os_join(self.path, '%s.html' % name),
								name, 
								data)
		self.kw[KW_UPDIR]=oldupdirsite
		self.kw[KW_UPDIRNAME]=oldupdirname
		
			
	
	def _WriteFolders(self):
		"""writes all folders found"""
		while self.sites:
			folder, sites=self.sites.popitem()
			try: os.mkdir(os_join(self.path, folder))
			except: pass
			#self._WriteCss(os_join(self.path, folder))
						
			oldroot=self.kw[KW_ROOT]
			oldcwdir=self.kw[KW_CWDIR]
			oldcwdirname=self.kw[KW_CWDIRNAME]
			olddupdir=self.kw[KW_UPDIR]
			oldupdirname=self.kw[KW_UPDIRNAME]
			
			self.kw[KW_ROOT]='../%s' % self.kw[KW_ROOT]
			self.kw[KW_CWDIR]='../%s' % self.kw[KW_CWDIR]
			self.kw[KW_CWDIRNAME]=folder
			self.kw[KW_UPDIR]='contents.html'
			self.kw[KW_UPDIRNAME]=folder			
			
			# pop contents page
			flag=False
			for n, i in enumerate(sites):
				if i[0]=="contents":
					flag=True
					break
			if flag:
				contents=sites.pop(n)
			else:
				# fallback here --no contents page found
				# ?? error ??
				contents=sites.pop(0)
			
			contentslist=[]
			for n, i in enumerate(sites):
				name, data=i
				contentslist.append(('%s.html' % name, name))
				if n-1 > 0:
					self.kw[KW_PREVSITE]= '%s.html' % sites[n-1][0]
					self.kw[KW_PREVSITENAME]=sites[n-1][0]
				else:	
					self.kw[KW_PREVSITE]= 'contents.html'
					self.kw[KW_PREVSITENAME]=folder
				try: 
					self.kw[KW_NEXTSITE]= '%s.html' % sites[n+1][0]
					self.kw[KW_NEXTSITENAME]=sites[n+1][0]
				except: 
					self.kw[KW_NEXTSITE]='contents.html'
					self.kw[KW_NEXTSITENAME]=folder
				
				self._WriteSite(
						os_join(self.path, folder, '%s.html' % name),
						name, 
						data)
			
			self.kw[KW_ROOT]=oldroot
			self.kw[KW_CWDIR]=oldcwdir
			self.kw[KW_CWDIRNAME]=oldcwdirname
			self.kw[KW_UPDIR]=olddupdir
			self.kw[KW_UPDIRNAME]=self.kw[KW_CWDIRNAME]
				
			# write sites defined in folder
			if sites:
				self.kw[KW_PREVSITE]= '%s.html' % sites[-1][0]
				self.kw[KW_PREVSITENAME]=sites[-1][0]
				self.kw[KW_NEXTSITE]= '%s.html' %  sites[0][0]
				self.kw[KW_NEXTSITENAME]= sites[0][0]
			out=[]
			
			# root is now one level lower #
			oldroot = self.kw[KW_ROOT]
			self.kw[KW_ROOT]='../%s' % self.kw[KW_ROOT]
			for i in contentslist:
				if i[1] !="contents":
					out.append(HREF % i)
			self._WriteSite(os_join(self.path, folder, 'contents.html'),
								folder, 
								'%s\n%s%s%s' % (
															contents[1], 
															BLQ,
															''.join(out),
															ENDBLQ))
			self.kw[KW_UPDIRNAME]=oldupdirname	
			self.kw[KW_ROOT] = oldroot

	
	
	def _WriteSiteLog(self):
		"""dump all sites to log"""
		fp=open(self.globaldata['logpath'], 'a+')
		try:
			for i in self.sitelog: fp.write('%s\n' % i)
		finally: fp.close()
	
	
	#--------------------------------------------------------------------------------
	# public methods
	
	def GetName(self):
		return os_basename(self.path)
		
	def GetDefaultPage(self):
		return self.options[KW_DEFPAGE]
	
	def GetTabWidth(self):
		return self.options[KW_TABWIDTH]
	
	def GetCompilerOptions(self):
		return self.cmp_options

	def GetSiteLog(self):
		return self.sitelog


						
#**********************************************************************************
# front end for the parser
#***********************************************************************************
					
			
class Doc(object):
	def __init__(self):
		self.path=None
		
		
	def DocTree(self, path, callback=None):
		if not os_isdir(path):
			raise IOError, 'invalid dir: %s' % path
		self.path=path
				
		tpl=[os_join(path, x) for x in os.listdir(path) 
					if os_isfile(os_join(path, x)) 
					and os_splitext(x)[1].lower() == '.dtpl']
		if len(tpl) > 1:
			print >> sys.stderr, "multiple templates in directory: %s " % path
			
		
		self.logpath=os_join(path, 'sitelog.log')
		if os_isfile(self.logpath):
			os.remove(self.logpath)
		globaldata={
			'logpath': self.logpath,
			'root': self.path,
			'rootsite':None,
			'rootsitename': None,
			'updirsite': None,
			'updirname':None,
			'callback':callback,
			'tabwidth': 6,
			'errorlog':False,
			'defs': {},
			}
		
		
		self.project=DocParser(tpl[0], globaldata)
				
	
	def Wipe(self, path, emptyfolders=True):
		for root, dirs, files in os.walk(path):
			for x in files:
				filePath = os_join(root, x)
				if os_splitext(filePath)[1].lower()=='.html':
					os.remove(filePath)
		if emptyfolders:
			delete = []
			flag=False
			for root, dirs, files in os.walk(path, False):
				if flag:
					if not files: delete.append(root)
				flag=True
			for i in delete:
				try: os.rmdir(i)
				except: pass

	def CompileCHM(self, outfile, compfunc=None):
		opt=self.project.GetCompilerOptions()
		fp=open(self.logpath, 'r')
		try:
			c=ChmCompiler()
			c.InitProject(self.path,
				title=opt.get(KW_CMP_TITLE, None),
				filelist=fp)
		finally: fp.close()
		c.SetOutputFile(outfile)
		if KW_CMP_FONT in opt:
			if opt[KW_CMP_FONT]:
				c.SetFont(*opt[KW_CMP_FONT].split(','))
		if KW_CMP_KEEPPROJ in opt:
			c.SetKeepProjectFiles(opt[KW_CMP_KEEPPROJ])
		if KW_CMP_DEFTOPIC in opt:
			if opt[KW_CMP_DEFTOPIC]:
				c.SetDefaultTopic(os_join(self.path, '%s.html' % opt[KW_CMP_DEFTOPIC]))
		if KW_CMP_ERRLOG in opt:
			if opt[KW_CMP_ERRLOG]==False:
				c.SetErrorLog(False)
			else: c.SetErrorLog(True)
		
		if compfunc:
			c.SetCompFunc(compfunc)
		c.Compile()

		if KW_CMP_KEEPSITELOG in opt:
			if not opt[KW_CMP_KEEPSITELOG]:
				try:
					os.remove(self.logpath)
				except: pass
		



#**********************************************************************************
#***********************************************************************************
def test():
	path=r'D:\_scr_\py\scr\wnd\doc\wnd'
	d=Doc()
	d.Wipe(path)
	d.DocTree(path)
	d.CompileCHM()
#p=DocParser(path, None)

#p.Tokenize()
#for token, name, data in p:



