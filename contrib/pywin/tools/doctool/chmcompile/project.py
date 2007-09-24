
from wnd.tools.doctool.chmcompile.header import *
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

class Project:
	
	def WriteProject(self):
		"""Writes the project file (*.hhp).
		For special purposes only. The 'Compile' method calls this
		by default.'"""
		if not self._fProjectStarted: raise 'no project started'
		fp=open(self._projpath, 'w+')
		try: 
			fp.write("[OPTIONS]\n")
			for name, value in self._projdata.items():
				if value:	fp.write('%s=%s\n' % (name, value))
	
			fp.write("\n[FILES]\n")
			self._data.seek(0)
			for i in self._data:	fp.write(self._RELPATH(i))
		finally: fp.close()
		
	