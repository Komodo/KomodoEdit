"""compiles a chm from the sample *.dtpl in the smple folder.
If HtmlWorkshop is not installed only the html pages are created"""

import os, sys
from wnd.tools import doctool
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

def test():
	path=r'%s\\_test_chm' % os.getcwd()
	
	d = doctool.Doc()
	d.Wipe(path)
	d.DocTree(path)
	try:
		d.CompileCHM()
	except: print >> sys.stderr, "sorry help workshop not found"
	#d.Wipe(path)


if __name__=='__main__':	
	test()	