
"""
TODO
	
	- currently only the following messages are tested: 
			"opendropdown", 
			"closedropdown" 
		
"""


import wnd
from wnd.controls.combobox import Combobox, ComboboxFromHandle

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
		self.TEXT= 'test'
		self.TEXT2= 'foo'
		self.LONG_TEXT= 'foo'*33


		
		
	def test_Item(self):
		self.ctrl.Item(self.TEXT)
		self.failUnless(len(self.ctrl)==1)
		self.ctrl.RemoveItem(0)
		self.failUnless(len(self.ctrl)==0)


	def test_InsertItem(self):
		self.ctrl.InsertItem(0, 'test')
		self.failUnless(len(self.ctrl)==1)
		self.ctrl.RemoveItem(0)
		self.failUnless(len(self.ctrl)==0)
	
	
	def test_SetItemText(self):
		self.ctrl.Item(self.TEXT)
		self.failUnless(len(self.ctrl)==1)

		self.ctrl.SetItemText(0, self.TEXT2)
		self.failUnless(self.ctrl.GetItemText(0)==self.TEXT2)
		self.failUnless(self.ctrl.GetItemTextLen(0)==3)
		
		self.ctrl.RemoveItem(0)
		self.failUnless(len(self.ctrl)==0)

	def test_SetItemLparam(self):
		self.ctrl.Item(self.TEXT, lp=888)
		self.failUnless(len(self.ctrl)==1)

		self.failUnless(self.ctrl.GetItemLparam(0)==888)
		self.ctrl.SetItemLparam(0, 999)
		self.failUnless(self.ctrl.GetItemLparam(0)==999)
				
		self.ctrl.RemoveItem(0)
		self.failUnless(len(self.ctrl)==0)
	
	
	
	def test_SetItemHeight(self):
		self.ctrl.Item(self.TEXT)
		self.failUnless(len(self.ctrl)==1)
		
		self.ctrl.SetItemHeight(99)
		self.failUnless(self.ctrl.GetItemHeight()==99)
		
		self.ctrl.RemoveItem(0)
		self.failUnless(len(self.ctrl)==0)
		
		
	def test_Select(self):
			
		self.ctrl.Item(self.TEXT)
		self.failUnless(len(self.ctrl)==1)
		
		self.ctrl.Select(0)
		self.failUnless(self.ctrl.GetText()==self.TEXT)
		
		self.ctrl.RemoveItem(0)
		self.failUnless(len(self.ctrl)==0)
		
	
	
	def test_SetEditSelection(self):
				
		self.ctrl.Item(self.TEXT)
		self.failUnless(len(self.ctrl)==1)
		
		self.ctrl.Select(0)
		self.failUnless(self.ctrl.GetText()==self.TEXT)

		
		self.ctrl.SetEditSelection(1, 3)
		self.failUnless(self.ctrl.GetEditSelection()==(1, 3))
				
		self.ctrl.RemoveItem(0)
		self.failUnless(len(self.ctrl)==0)
	
	
	
	def test_Find(self):
		self.ctrl.Item(self.TEXT)
		self.failUnless(len(self.ctrl)==1)
		
		self.failUnless(self.ctrl.Find(self.TEXT[:2])==0)
		self.failUnless(self.ctrl.FindExact(self.TEXT)==0)
		
		self.ctrl.RemoveItem(0)
		self.failUnless(len(self.ctrl)==0)


	def test_SetTopItem(self):
		for i in range(10):
			self.ctrl.Item(self.TEXT)
		self.failUnless(len(self.ctrl)==10)

		self.ctrl.SetTopItem(5)
		self.failUnless(self.ctrl.GetTopItem()==5)
		
		for i in range(10):
			self.ctrl.RemoveItem(0)
		self.failUnless(len(self.ctrl)==0)
	
	
	def test_GetEditBox(self):
		self.failIf(self.ctrl.GetEditControl('nosubclass')==None)
		
	
	def test_TextMax(self):
		self.ctrl.SetTextMax(10)
		self.failUnless(self.ctrl.GetTextMax()==10)

		self.ctrl.Item(self.LONG_TEXT)
		self.failUnless(len(self.ctrl)==1)
		
		self.failUnless(len(self.ctrl.GetItemText(0))==10)
		
		self.ctrl.RemoveItem(0)
		self.failUnless(len(self.ctrl)==0)


	def test_SetItemCount(self):
		self.ctrl.SetItemCount(1000, 10)
	
	
	def test_Clear(self):
		for i in range(10):
			self.ctrl.Item(self.TEXT)
		self.failUnless(len(self.ctrl)==10)

		self.ctrl.Clear()
		self.failUnless(len(self.ctrl)==0)
	
	
	def test_Iter(self):
		for i in range(10):
			self.ctrl.Item(self.TEXT)
		self.failUnless(len(self.ctrl)==10)

		for i in self.ctrl: pass

		self.failUnless(i==9)

		self.ctrl.Clear()
		self.failUnless(len(self.ctrl)==0)


#*****************************************************************
# test classes
#*****************************************************************
	
##
class TestCombobox(unittest.TestCase, Tests):
	def setUp(self):
		self.ctrl= Combobox(PARENT ,  0, 0, 40, 40)
		Tests.__init__(self)
		
	def tearDown(self):
		self.ctrl.Close()

##
class TestComboboxFromHandle(unittest.TestCase, Tests):
	def setUp(self):
		self.ctrl0= Combobox(PARENT , 0, 0, 40, 40)
		self.ctrl= ComboboxFromHandle(self.ctrl0.Hwnd)
		Tests.__init__(self)

	def tearDown(self):
		self.ctrl0.Close()
		self.ctrl.Close()
	
	
##
class TestDropdownCombobox(unittest.TestCase, helpers.Helpers):
	def setUp(self):
		self.ctrl= Combobox(PARENT ,  0, 0, 40, 40, 'dropdownlist', 'hscroll')
		helpers.Helpers.__init__(self)
		self.TEXT= 'test'
		
	def tearDown(self):
		self.ctrl.Close()
	
	def test_DropDown(self):
		self.ctrl.OpenDropdown()
		self.failUnless(self.PeekMsg("opendropdown"))
		self.failUnless(self.ctrl.IsDroppedDown())
		self.ctrl.CloseDropdown()
		self.failUnless(self.PeekMsg("closedropdown"))
		self.failIf(self.ctrl.IsDroppedDown())

	
	def test_ExtendedUI(self):
		self.ctrl.SetExtendedUI(True)
		self.failUnless(self.ctrl.HasExtendedUI())
		self.ctrl.SetExtendedUI(False)
		self.failIf(self.ctrl.HasExtendedUI())
		
	
	def test_ScrollWidth(self):
		self.ctrl.SetScrollWidth(300)
		self.failUnless(self.ctrl.GetScrollWidth()==300)
	

#****************************************************************
#***************************************************************
def suite():
	return (unittest.makeSuite(TestCombobox),
				unittest.makeSuite(TestComboboxFromHandle),
				unittest.makeSuite(TestDropdownCombobox),	
					)


	
						

if __name__=='__main__':
	mod= imp.load_source('foo', PATH_STANDALONE)
	PARENT= mod.Main()
	PARENT.RunTest(suite)
	helpers.RemovePyc(PATH)
	

	
