

import unittest, imp, os
from wnd.controls.checkbox import Checkbox, CheckboxFromHandle
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

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
		
	def test_Click(self):
		
		self.failUnless(not self.ctrl.IsChecked())
		self.ctrl.Click()
		self.failUnless( self.ctrl.IsChecked())
		self.failUnless(self.PeekMsg("checked"))
		
		self.ctrl.Click()
		self.failUnless( self.ctrl.IsGraychecked())
		self.failUnless(self.PeekMsg("graychecked"))
		
		self.ctrl.Click()
		self.failUnless( self.ctrl.IsUnchecked())
		self.failUnless(self.PeekMsg("unchecked"))


	def test_Check(self):
		self.failUnless(not self.ctrl.IsChecked())
		self.ctrl.Check()
		self.failUnless( self.ctrl.IsChecked())
		self.ctrl.Graycheck()
		self.failUnless( self.ctrl.IsGraychecked())
		self.ctrl.Uncheck()
		self.failUnless( self.ctrl.IsUnchecked())
		
	def test_SetText(self):
		self.ctrl.SetText('foo')
		self.failUnless(self.ctrl.GetText() == 'foo')
	
	
#****************************************************************
# test classes
#****************************************************************

##
class TestCheckbox(unittest.TestCase, Tests):
	def setUp(self):
		self.ctrl= Checkbox(PARENT , 'test', 0, 0, 40, 40, 'auto3state')
		Tests.__init__(self)

	def tearDown(self):
		self.ctrl.Close()

	
##
class TestCheckboxFromHandle(unittest.TestCase, Tests):
	def setUp(self):
		self.ctrl0= Checkbox(PARENT , 'test', 0, 0, 40, 40, 'auto3state')
		self.ctrl= CheckboxFromHandle(self.ctrl0.Hwnd)
		Tests.__init__(self)

	def tearDown(self):
		self.ctrl0.Close()
		self.ctrl.Close()


#****************************************************************
#***************************************************************
def suite():
	return (unittest.makeSuite(TestCheckbox),
					unittest.makeSuite(TestCheckboxFromHandle),
					)


	
						
PARENT= None			

if __name__=='__main__':
	mod= imp.load_source('foo', PATH_STANDALONE)
	PARENT= mod.Main()
	PARENT.RunTest(suite)
	helpers.RemovePyc(PATH)
	