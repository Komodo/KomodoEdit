
from wnd.tools.doctool.chmcompile.header import *
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::



class Index:
	# stuff required for parsing an index file
	
	def _INDEX_OBJECT(self, name, local):
		obj=['\t<LI><OBJECT type="text/sitemap">',
				'\t\t<param name="Name" value="%s">' % name,
				'\t\t<param name="Local" value="%s">\n' % local,
				'\t\t</OBJECT></LI>\n'] 
		return '\n'.join(obj) 	
		
		
	def _MAKEPOSTFIX(self, name, relpath):
			postfix=os_splitext(relpath)[0]
			return '%s (%s)' % (name, postfix.replace('\\', ' '))
			
	
	def _STRIPTAGS(self, name):
		name = rxStripTags.sub('', name)
		return rxCleanString.sub('', name)
	
	def WriteIndex(self):
		"""Writes the index file (*.hhc). """
		if not self._fProjectStarted: raise 'no project started yet.'
		
		tmp=tempfile.NamedTemporaryFile()
		path=tmp.name
		tmp.close()
		db = bsddb.btopen(path, 'n')
		try:
			self._data.seek(0)
			error=''
			for i in self._data:
				fp=None
				try:
					fp=open(i.strip())
					matches = rxGetNamesPat.findall(fp.read())
				except: pass
				if fp:fp.close()
				if matches:
					for linkname, name in matches:
						
						name=self._STRIPTAGS(name)
						if self._cmpfunc:
							# call user provided compfunc
							result = self._cmpfunc(i.strip(), linkname, name)
							if not result: continue
						
						if not (linkname or name): continue
						relpath=self._RELPATH(i).strip()
						
						# gather multiple target names if needed
						if name in db:
							db[name]= '%s*%s' % (db[name], relpath)	
						else: db[name]=relpath
						

			# write all the data from db to index file
			fp=open(self._projdata['Index file'], 'w+')
			fp.write(INDEX_HEADER)
			fp.write(UL(0))
			try:
				for name, relpath in db.items(): 
					if not relpath: continue
					if '*' in relpath:
						for i in relpath.split('*'):
							o=self._INDEX_OBJECT(
									self._MAKEPOSTFIX(name, i), i)
							fp.write(o)
					else:		
						o=self._INDEX_OBJECT(name, '%s' % relpath)
						fp.write(o)
				fp.write(END_UL(0))
				fp.write(FOOTER)
			finally: fp.close()
		finally:			
			db.close()
			os.remove(path)

		

		
	