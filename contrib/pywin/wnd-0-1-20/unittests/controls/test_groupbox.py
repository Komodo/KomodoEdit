
import wnd
from wnd.controls.groupbox import Groupbox, GroupboxFromHandle

import unittest, imp, os
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

PARENT= None	
PATH=  os.path.split(__file__)[0]
DIRUP=  os.path.split(PATH)[0]

PATH_STANDALONE= os.path.join(DIRUP, 'teststandalone.py')
PATH_HELPERS= os.path.join(DIRUP, 'testhelpers.py')

helpers= imp.load_source('helpers',PATH_HELPERS)


#*****************************************************************
# default tests
#*****************************************************************

class Tests(helpers.Helpers):
	
	def __init__(self):
		helpers.Helpers.__init__(self)
	
	def test_SetText(self):
		self.ctrl.SetText('foo')
		self.failUnless(self.ctrl.GetText() == 'foo')
	
	

		
#*****************************************************************
# test classes
#*****************************************************************

##
class TestGroupbox(unittest.TestCase, Tests):
	def setUp(self):
		self.ctrl= Groupbox(PARENT , 'test', 0, 0, 40, 40)
		Tests.__init__(self)

	def tearDown(self):
		self.ctrl.Close()

##
class TestGroupboxFromHandle(unittest.TestCase, Tests):
	def setUp(self):
		self.ctrl0= Groupbox(PARENT , 'test', 0, 0, 40, 40)
		self.ctrl= GroupboxFromHandle(self.ctrl0.Hwnd)
		Tests.__init__(self)

	def tearDown(self):
		self.ctrl0.Close()
		self.ctrl.Close()

#****************************************************************
#***************************************************************
def suite():
	return (unittest.makeSuite(TestGroupbox),
					unittest.makeSuite(TestGroupboxFromHandle),
					)


						

if __name__=='__main__':
	mod= imp.load_source('foo', PATH_STANDALONE)
	PARENT= mod.Main()
	PARENT.RunTest(suite)
	helpers.RemovePyc(PATH)
	