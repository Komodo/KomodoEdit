
import unittest, imp, os
from wnd.controls.radiobox import Radiobox, RadioboxFromHandle
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
		
	def test_SetText(self):
		self.ctrl.SetText('foo')
		self.failUnless(self.ctrl.GetText() == 'foo')
	
	
	def test_Click(self):
		self.ctrl.Uncheck()
					
		self.ctrl.Click()
		self.failUnless(self.ctrl.IsChecked())
		self.failUnless(self.GetMsg("checked"))
		
		self.ctrl1.Uncheck()

		
	def test_Check(self):
		self.ctrl.Uncheck()
		self.failIf(self.ctrl.IsChecked())

		self.ctrl.Check()
		self.failUnless(self.ctrl.IsChecked())

		self.ctrl.Uncheck()
		self.failIf(self.ctrl.IsChecked())


	def test_Group(self):
		
		# setup a radiogroup
		self.ctrl.Group(self.ctrl1)
		self.failUnless(self.ctrl.IsGrouped())
		self.failUnless(self.ctrl1.IsGrouped())
		self.failUnless(self.ctrl.GetGroup()==[self.ctrl.Hwnd, self.ctrl1.Hwnd])
		self.failUnless(self.ctrl.IsGroupAncestor())
		self.failIf(self.ctrl1.IsGroupAncestor())

		# test group clicking
		self.ctrl.Click()
		self.failUnless(self.ctrl.IsChecked())
		self.ctrl1.Click()
		self.failUnless(self.ctrl1.IsChecked())
		self.failIf(self.ctrl.IsChecked())

		self.ctrl.Click()
		self.failUnless(self.ctrl.IsChecked())
		self.failIf(self.ctrl1.IsChecked())

		# dismiss the group
		self.ctrl.Ungroup(self.ctrl1)
		self.failIf(self.ctrl.IsGrouped())
		self.failIf(self.ctrl1.IsGrouped())
		self.failIf(self.ctrl.IsGroupAncestor())
		self.assertRaises(RuntimeError, self.ctrl.GetGroup)
		
		
#****************************************************************
# test classes
#****************************************************************

##
class TestRadiobox(unittest.TestCase, Tests):
	def setUp(self):
		self.ctrl= Radiobox(PARENT , 'test', 0, 0, 40, 40, 'autoradiobutton')
		self.ctrl1= Radiobox(PARENT , 'test', 0, 0, 40, 40, 'autoradiobutton')
		self.ctrl1.onMSG= self.onMSG
		Tests.__init__(self)

	
	def tearDown(self):
		self.ctrl.Close()
		self.ctrl1.Close()

	
##
class TestRadioboxFromHandle(unittest.TestCase, Tests):
	def setUp(self):
		self.ctrl0= Radiobox(PARENT , 'test', 0, 0, 40, 40, 'autoradiobutton')
		self.ctrl= RadioboxFromHandle(self.ctrl0.Hwnd)
		self.ctrl00= Radiobox(PARENT , 'test', 0, 0, 40, 40, 'autoradiobutton')
		## redirect messages 'manually' to our cache here
		self.ctrl1= RadioboxFromHandle(self.ctrl00.Hwnd)
		self.ctrl1.onMSG= self.onMSG

		Tests.__init__(self)

	def tearDown(self):
		self.ctrl0.Close()
		self.ctrl.Close()
		self.ctrl00.Close()
		self.ctrl1.Close()


#****************************************************************
#***************************************************************
def suite():
	tests= ("test_SetText", "test_Click", "test_Check", 
				
				"test_Group"		## grouping tests start here
				)
	
	suite1 = unittest.TestSuite()
	suite2= unittest.TestSuite()
	for i in tests:	
		suite1.addTest(TestRadiobox(i))
		suite2.addTest(TestRadioboxFromHandle(i))
	return suite1, suite2


	

if __name__=='__main__':
	mod= imp.load_source('foo', PATH_STANDALONE)
	PARENT= mod.Main()
	PARENT.RunTest(suite)
	helpers.RemovePyc(PATH)
	