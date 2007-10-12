
"""
TODO
	Not complete
"""

import wnd
from wnd.controls.rebar import Rebar, RebarFromHandle
from wnd.controls.button import Button
from wnd.controls.imagelist import Imagelist
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
		
	
	def XXXtestMoveBand(self):
		## IDToIndex fails after MoveBand
		
		self.failUnless(len(self.ctrl)==0)
		
		self.ctrl.Band(100, 'foo', self.child1, 0, 100)
		self.ctrl.Band(101, 'bar', self.child2, 0, 100)
		
		self.failUnless(len(self.ctrl)==2)

		self.ctrl.MoveBand(1, 0)
				
		##self.ctrl.MoveBand(0, 1)
		print self.ctrl.IDToIndex(101)
		
		self.ctrl.RemoveBand(100)
		self.ctrl.RemoveBand(101)

		self.failUnless(len(self.ctrl)==0)
	
	
	
	def testBand(self):
		
		self.failUnless(len(self.ctrl)==0)
		
		self.ctrl.Band(100, 'foo', self.child1, 0, 100)
		self.ctrl.Band(101, 'bar', self.child2, 0, 100)
		
		self.failUnless(len(self.ctrl)==2)

		self.ctrl.RemoveBand(100)
		self.ctrl.RemoveBand(101)

		self.failUnless(len(self.ctrl)==0)

	
	
	def testIDToIndex(self):
		self.failUnless(len(self.ctrl)==0)
		
		self.ctrl.Band(100, 'foo', self.child1, 0, 100)
		self.failUnless(len(self.ctrl)==1)
		
		self.failUnless(self.ctrl.IDToIndex(100)==0)
		self.failUnless(self.ctrl.IndexToID(0)==100)
		
		self.ctrl.RemoveBand(100)
		self.failUnless(len(self.ctrl)==0)

		
	def testBandText(self):
		self.failUnless(len(self.ctrl)==0)
		
		self.ctrl.Band(100, 'foo', self.child1, 0, 100)
		self.failUnless(len(self.ctrl)==1)

		
		self.failUnless(self.ctrl.GetBandTitle(100)=='foo')
		self.ctrl.SetBandTitle(100, 'bar')
		self.failUnless(self.ctrl.GetBandTitle(100)=='bar')
						
		self.ctrl.RemoveBand(100)
		self.failUnless(len(self.ctrl)==0)		
	
	
	def testBandColors(self):
		self.failUnless(len(self.ctrl)==0)
		
		self.ctrl.Band(100, 'foo', self.child1, 0, 100)
		self.failUnless(len(self.ctrl)==1)
		
		clrFg, clrBk= self.ctrl.GetBandColors(100)
		self.ctrl.SetBandColors(100, clrBk, clrFg)
		self.failUnless(self.ctrl.GetBandColors(100)==(clrBk, clrFg))
								
		self.ctrl.RemoveBand(100)
		self.failUnless(len(self.ctrl)==0)		

	
	def testBandBitmap(self):
		self.failUnless(len(self.ctrl)==0)
		
		self.ctrl.Band(100, 'foo', self.child1, 0, 100)
		self.failUnless(len(self.ctrl)==1)
		
		bm= gdi.SystemBitmap('size')

		self.ctrl.SetBandBackgroundImage(100,  bm)
		self.failUnless(self.ctrl.GetBandBackgroundImage(100)==bm.handle)
		
		bm.Close()
								
		self.ctrl.RemoveBand(100)
		self.failUnless(len(self.ctrl)==0)		


	def testImagelist(self):
		self.failUnless(len(self.ctrl)==0)
		
		self.ctrl.Band(100, 'foo', self.child1, 0, 100)
		self.failUnless(len(self.ctrl)==1)
		
		imgl= Imagelist(10, 10, 1, 0)
		self.ctrl.SetImagelist(imgl)
		self.failUnless(self.ctrl.GetImagelist()==imgl.handle)

		self.ctrl.SetBandImage(100, 4)
		self.failUnless(self.ctrl.GetBandImage(100)==4)
		
		self.ctrl.SetImagelist(None)
		self.failUnless(self.ctrl.GetImagelist()==None)
		imgl.Close()

		self.ctrl.RemoveBand(100)
		self.failUnless(len(self.ctrl)==0)		

	
	def testBandControlSize(self):
		self.failUnless(len(self.ctrl)==0)
		
		self.ctrl.Band(100, 'foo', self.child1, 0, 100)
		self.failUnless(len(self.ctrl)==1)
		
		self.ctrl.SetBandControlSize(100, 20, 200)
		self.failUnless(self.ctrl.GetBandControlSize(100)==(20, 200))
		
		self.ctrl.RemoveBand(100)
		self.failUnless(len(self.ctrl)==0)		


	def testBandMaximizedWidth(self):
		self.failUnless(len(self.ctrl)==0)
		
		self.ctrl.Band(100, 'foo', self.child1, 0, 100)
		self.failUnless(len(self.ctrl)==1)
		
		self.ctrl.SetBandMaximizedWidth(100, 500)
		self.failUnless(self.ctrl.GetBandMaximizedWidth(100)==500)
		
		self.ctrl.RemoveBand(100)
		self.failUnless(len(self.ctrl)==0)		

	
	def testBandWidth(self):
		self.failUnless(len(self.ctrl)==0)
		
		self.ctrl.Band(100, 'foo', self.child1, 0, 100)
		self.failUnless(len(self.ctrl)==1)
		
		self.ctrl.SetBandWidth(100, 500)
		self.failUnless(self.ctrl.GetBandWidth(100)==500)
		
		self.ctrl.RemoveBand(100)
		self.failUnless(len(self.ctrl)==0)		
	
	
	
	def testBandHeaderSize(self):
		self.failUnless(len(self.ctrl)==0)
		
		self.ctrl.Band(100, 'foo', self.child1, 0, 100)
		self.failUnless(len(self.ctrl)==1)
		
		self.ctrl.SetBandHeaderSize(100, 500)
		self.failUnless(self.ctrl.GetBandHeaderSize(100)==500)
		
		self.ctrl.RemoveBand(100)
		self.failUnless(len(self.ctrl)==0)		

	
	def testBandChild(self):
		self.failUnless(len(self.ctrl)==0)
		
		self.ctrl.Band(100, 'foo', self.child1, 0, 100)
		self.failUnless(len(self.ctrl)==1)
		
		self.ctrl.SetBandHeaderSize(100, 500)
		self.failUnless(self.ctrl.GetBandChild(100)==self.child1.Hwnd)
		
		self.ctrl.RemoveBand(100)
		self.failUnless(len(self.ctrl)==0)		


	def testBandLparam(self):
		self.failUnless(len(self.ctrl)==0)
		
		self.ctrl.Band(100, 'foo', self.child1, 0, 100)
		self.failUnless(len(self.ctrl)==1)
		
		self.ctrl.SetBandLparam(100, 500)
		self.failUnless(self.ctrl.GetBandLparam(100)==500)
		
		self.ctrl.RemoveBand(100)
		self.failUnless(len(self.ctrl)==0)		

#*****************************************************************
# test classes
#*****************************************************************
	
##
class TestRebar(unittest.TestCase, Tests):
	def setUp(self):
		self.ctrl= Rebar(PARENT)
		
		self.child1= Button(PARENT, '', 0, 0, 100, 100)
		self.child2= Button(PARENT, '', 0, 0, 100, 100)
		
		Tests.__init__(self)
	
	def tearDown(self):
		self.ctrl.Close()
		self.child1.Close()
		self.child2.Close()
	

##
class TestRebarFromHandle(unittest.TestCase, Tests):
	def setUp(self):
		self.ctrl0= Rebar(PARENT)
		self.ctrl= RebarFromHandle(self.ctrl0.Hwnd)
		
		self.child1= Button(PARENT, '', 0, 0, 100, 100)
		self.child2= Button(PARENT, '', 0, 0, 100, 100)
		
		Tests.__init__(self)

	def tearDown(self):
		self.ctrl0.Close()
		self.ctrl.Close()
		self.child1.Close()
		self.child2.Close()

	

	
#****************************************************************
#***************************************************************
def suite():
	return (unittest.makeSuite(TestRebar),
					unittest.makeSuite(TestRebarFromHandle),
					)


	
						

if __name__=='__main__':
	mod= imp.load_source('foo', PATH_STANDALONE)
	PARENT= mod.Main()
	PARENT.RunTest(suite)
	helpers.RemovePyc(PATH)
	

	
