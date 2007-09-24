
import wnd
from wnd.controls.button import Button, ButtonFromHandle
from wnd import gdi

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
		
		
	def test_Click(self):
		self.ctrl.Click()
		self.failUnless(self.PeekMsg("command"))
		
	def test_Push(self):
		self.failUnless(not self.ctrl.IsPushed())
		self.ctrl.Push()
		self.failUnless(self.ctrl.IsPushed())
		self.ctrl.Release()
		self.failUnless(not self.ctrl.IsPushed())

	def test_SetText(self):
		self.ctrl.SetText('foo')
		self.failUnless(self.ctrl.GetText() == 'foo')

	
#*****************************************************************
# test classes
#*****************************************************************
	
##
class TestButton(unittest.TestCase, Tests):
	def setUp(self):
		self.ctrl= Button(PARENT , 'test', 0, 0, 40, 40)
		Tests.__init__(self)
	
	def tearDown(self):
		self.ctrl.Close()
	

##
class TestButtonFromHandle(unittest.TestCase, Tests):
	def setUp(self):
		self.ctrl0= Button(PARENT , 'test', 0, 0, 40, 40)
		self.ctrl= ButtonFromHandle(self.ctrl0.Hwnd)
		Tests.__init__(self)

	def tearDown(self):
		self.ctrl0.Close()
		self.ctrl.Close()
	
##
## no full tests here
class TestIconButton(unittest.TestCase):
	def setUp(self):
		self.ctrl= Button(PARENT , 'test', 0, 0, 40, 40, 'icon')
	
	def tearDown(self):
		self.ctrl.Close()
	
	def test_Icon(self):
		ico= gdi.SystemIcon('hand')
		self.ctrl.SetIcon(ico)
		self.failUnless(self.ctrl.GetIcon() == ico.handle)
		ico.Close()
	
	
##
## no full tests here
class TestBitmapButton(unittest.TestCase):
	def setUp(self):
		self.ctrl= Button(PARENT , 'test', 0, 0, 40, 40, 'bitmap')

	def tearDown(self):
		self.ctrl.Close()
	
	def test_Bitmap(self):
		bm= gdi.SystemBitmap('checkboxes')
		self.ctrl.SetBitmap(bm)
		self.failUnless(self.ctrl.GetBitmap() == bm.handle)
		bm.Close()


#****************************************************************
#***************************************************************
def suite():
	return (unittest.makeSuite(TestButton),
					unittest.makeSuite(TestButtonFromHandle),
					unittest.makeSuite(TestIconButton),
					unittest.makeSuite(TestBitmapButton),
					)


	
						

if __name__=='__main__':
	mod= imp.load_source('foo', PATH_STANDALONE)
	PARENT= mod.Main()
	PARENT.RunTest(suite)
	helpers.RemovePyc(PATH)
	

	
