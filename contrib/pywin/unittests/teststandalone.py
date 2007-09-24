
"""helper for developing unittests.
When run from commandline a unittest will be atatched to this window.

Default is to run unittests from the main GUI.
This enshures most framework independend processing possible

"""

import unittest, wnd
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

VERBOSITY= 2


class Main:
	def __init__(self):
		self.mainframe= wnd.Window('unittest-standalone', 'test', 10, 10, 400, 300, 'sysmenu')
		self.Hwnd= self.mainframe.Hwnd
		
	def RunTest(self, suite):	
		suite=unittest.TestSuite(suite())
		unittest.TextTestRunner(verbosity=VERBOSITY).run(suite)
						