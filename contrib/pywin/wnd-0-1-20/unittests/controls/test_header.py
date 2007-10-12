
"""
TODO
	- no messages tested so far

"""


import wnd
from wnd.controls.header import Header, HeaderFromHandle
from wnd.controls.imagelist import Imagelist

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
		
	
	def test_Item(self):
		self.failUnless(len(self.ctrl)==0)
		self.ctrl.Item('test')
		self.failUnless(len(self.ctrl)==1)
		self.ctrl.RemoveItem(0)
		self.failUnless(len(self.ctrl)==0)

	
	def test_InsertItem(self):
		self.failUnless(len(self.ctrl)==0)
		self.ctrl.InsertItem(0, 'test')
		self.failUnless(len(self.ctrl)==1)
		self.ctrl.RemoveItem(0)
		self.failUnless(len(self.ctrl)==0)

	
	def test_ItemText(self):
		self.failUnless(len(self.ctrl)==0)
		self.ctrl.Item('test')
		self.failUnless(len(self.ctrl)==1)
		
		self.failUnless(self.ctrl.GetItemText(0)=='test')
		self.ctrl.SetItemText(0, 'foo')
		self.failUnless(self.ctrl.GetItemText(0)=='foo')
				
		self.ctrl.RemoveItem(0)
		self.failUnless(len(self.ctrl)==0)
	
	def test_ItemLparam(self):
		self.failUnless(len(self.ctrl)==0)
		self.ctrl.Item('test', lp=333)
		self.failUnless(len(self.ctrl)==1)
		
		self.failUnless(self.ctrl.GetItemLparam(0)==333)
		self.ctrl.SetItemLparam(0, 999)
		self.failUnless(self.ctrl.GetItemLparam(0)==999)
				
		self.ctrl.RemoveItem(0)
		self.failUnless(len(self.ctrl)==0)
	
	
	def test_ItemImage(self):
		self.failUnless(len(self.ctrl)==0)
		self.ctrl.Item('test', iImage=3)
		self.failUnless(len(self.ctrl)==1)
		
		self.failUnless(self.ctrl.GetItemImage(0)==3)
		self.ctrl.SetItemImage(0, 9)
		self.failUnless(self.ctrl.GetItemImage(0)==9)
				
		self.ctrl.RemoveItem(0)
		self.failUnless(len(self.ctrl)==0)
	
	
	def test_ItemWidth(self):
		self.failUnless(len(self.ctrl)==0)
		self.ctrl.Item('test', width= 100)
		self.failUnless(len(self.ctrl)==1)
		
		self.failUnless(self.ctrl.GetItemWidth(0)==100)
		self.ctrl.SetItemWidth(0, 10)
		self.failUnless(self.ctrl.GetItemWidth(0)==10)
				
		self.ctrl.RemoveItem(0)
		self.failUnless(len(self.ctrl)==0)
	
	
	def test_ItemOrder(self):
		for i in range(10):
			self.ctrl.Item('test')
		self.failUnless(len(self.ctrl)==10)

		rng= (range(len(self.ctrl)))[::-1]
		self.ctrl.SetItemOrder(*rng)
		self.failUnless(self.ctrl.GetItemOrder()==rng)
		self.failUnless(self.ctrl.IndexToOrder(self.ctrl.OrderToIndex(0))==0)
		
		for i in range(10):
			self.ctrl.RemoveItem(0)
		self.failUnless(len(self.ctrl)==0)
	

	def test_Imagelist(self):
		imgl= Imagelist(10, 10, 1, 0)
		self.ctrl.SetImagelist(imgl)
		self.failUnless(self.ctrl.GetImagelist()==imgl.handle)
		imgl.Close()
	
	
	def test_Clear(self):
		for i in range(10):
			self.ctrl.Item('test')
		self.failUnless(len(self.ctrl)==10)

		self.ctrl.Clear()
		self.failUnless(len(self.ctrl)==0)

	
	
	def test_Misc(self):
		self.failUnless(len(self.ctrl)==0)
		self.ctrl.Item('test', iImage=3)
		self.failUnless(len(self.ctrl)==1)
		
		self.ctrl.GetItemRect(0)
		r= self.ctrl.ItemHittest(0, 10)

		rc= self.ctrl.GetClientRect()
		r= self.ctrl.GetLayout(rc)

		self.ctrl.RemoveItem(0)
		self.failUnless(len(self.ctrl)==0)
	

#*****************************************************************
# test classes
#*****************************************************************
	
##
class TestHeader(unittest.TestCase, Tests):
	def setUp(self):
		self.ctrl= Header(PARENT ,  0, 0, 40, 40)
		Tests.__init__(self)

	def tearDown(self):
		self.ctrl.Close()
		

##
class TestHeaderFromHandle(unittest.TestCase, Tests):
	def setUp(self):
		self.ctrl0= Header(PARENT , 0, 0, 40, 40)
		self.ctrl= HeaderFromHandle(self.ctrl0.Hwnd)
		Tests.__init__(self)

	def tearDown(self):
		self.ctrl0.Close()
		self.ctrl.Close()
	
	
#****************************************************************
#***************************************************************
def suite():
	return (unittest.makeSuite(TestHeader),
				unittest.makeSuite(TestHeaderFromHandle),
					)


	
						

if __name__=='__main__':
	mod= imp.load_source('foo', PATH_STANDALONE)
	PARENT= mod.Main()
	PARENT.RunTest(suite)
	helpers.RemovePyc(PATH)
	

	
