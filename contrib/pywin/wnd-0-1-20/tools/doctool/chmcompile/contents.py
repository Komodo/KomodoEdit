
from wnd.tools.doctool.chmcompile.header import *
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

class Contents:
	# stuff required for parsing contents file
	
	def _RELPATH(self, path):
		return path[len(self._root)+1:]
	
	
	def _ISSAMEFOLDER(self, path1, path2):
		if os_split(path1)[0] == os_split(path2)[0]:
			return True
		return False
	

	def _COMP(self, path1, path2):
		"""Compares two paths by their relative level.
		Returns -1 if first is on a higher level, 1 if second.
		0 if both compare equal."""
		return cmp(path1.count(os.sep), path2.count(os.sep))

	def _CONTENTS_OBJECT(self, relpath, level, isfolder=False):
		
		flag=True
		if isfolder:
			if self._defaultFolderPage:
				if self._defaultFolderPage !='foldername':
					name =os_split(os_split(relpath)[0])[1]
					flag=False
			else:
				if os_splitext(os_basename(relpath))[0].lower()== 'contents':
					# get the folders name
					name=os_basename(os_dirname(relpath))
					if not name:
						name = os_basename(self._root)
					flag=False
						
		if flag:
			name = os_splitext(os_split(relpath)[1])[0]
		tab='\t'*level
		obj=[
		'%s<LI><OBJECT type="text/sitemap">' % tab,
		'%s<param name="Name" value="%s">' % (tab, name),
		'%s<param name="Local" value="%s">' % (tab, relpath),
		'%s</OBJECT></LI>\n' % tab]
		if isfolder:
			obj.insert(-1, '%s<param name="ImageNumber" value="1">' % tab)
		return '\n'.join(obj)
		
		
	
	def WriteContents(self):
		"""Writes the contents file (*.hhk). For special purposes only.
		'"""
		if not self._fProjectStarted: raise 'no project started yet'
	
		fp=None		# our contents file
		
		if self._debug:
			fpTmp=open('%s.tmp' % self._projdata['Contents file'], 'w+')
		else:
			fpTmp=tempfile.TemporaryFile()
				
		try:
			# process data from self._data file to temp file
			self._data.seek(0)
			n=0
			useFolderIcon=0
			nextIsFolder=0
			closemap={}
			prevline=''
			while True:
				line=self._data.readline()
				if line==EOF: break
				pos=self._data.tell()
				next=self._data.readline()
				self._data.seek(pos)
				isfileprev=self._ISSAMEFOLDER(prevline, line)
				isfilenext=self._ISSAMEFOLDER(line, next)
				levelprev=self._COMP(prevline, line)
				levelnext=self._COMP(next, line)
				
				# check if the item starts a folder
				useFolderIcon=0
				if next:
					if not isfileprev and isfilenext:
						useFolderIcon=1
					if (levelprev != 0 and isfilenext):
						useFolderIcon=1
					if (levelprev < 0 and levelnext > 0):
						useFolderIcon=1
					
				# compare the current line to the following
				# lines to check when to close the folder
				if not isfileprev:	# if its a folder in this case
					j=n
					while True:
						tmpLine=self._data.readline()
						if tmpLine==EOF: break
						if not self._ISSAMEFOLDER(line, tmpLine):
							if self._COMP(tmpLine, line) <= 0:
								#+1=next item closes this folder
								if j+1 in closemap: closemap[j+1] +=1 
								else: closemap[j+1] =1
								break
						j +=1
					self._data.seek(pos)
				
				# each item checks for the number of folders 
				# it should close
				if n in closemap:	nClose = closemap[n]
				else: nClose=0
																
				# write the data to tempfile
				# nItems-to-close|starts-folder|use-folder-icon|item
				fpTmp.write('%s %s %s %s' % (nClose, nextIsFolder, useFolderIcon, self._RELPATH(line)))
				nextIsFolder=useFolderIcon
				prevline=line
				n += 1
						
			#write the index file from tempdata
			fp=open(self._projdata['Contents file'], 'w+')	
			fpTmp.seek(0)	
			
			fp.write(CONTENTS_HEADER)
			fp.write(UL(0))
			level=0
			for i in fpTmp:
				close, start, icon, item = i.split(' ', 3)
				close, start, icon = int(close),int(start),int(icon)
				
				if close:
					for i in range(close):
						level -= 1
						fp.write(END_UL(level+1))
				
				if start:
					level += 1
					fp.write(UL(level))
								
				# write the object
				tablevel= '\t'*(level +1)	
				#fp.write('%s%s' % (tablevel, self.RELPATH(item)))
				o=self._CONTENTS_OBJECT(item.strip().replace('\\', '/'), level+1, icon)
				fp.write(o)
				
			
			# finalize this thingy
			for i in range(level +1):
				level -= 1
				tablevel= '\t'*(level	+1)
				fp.write('%s</UL>\n' % tablevel)
			fp.write(FOOTER)
		finally: 
			if fp:	fp.close()
			fpTmp.close()

			
	