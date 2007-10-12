
"""
TODO
	- messages tested so far

		'beginlabeledit'
		'endlabeledit'
		'itemchanged'

"""


import wnd
from wnd.controls.listview import Listview, ListviewFromHandle
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
# column tests
#*****************************************************************
class ColumnTests:
	
	def test_Column(self):
		self.failUnless(self.ctrl.GetColumnCount()==0)
		self.ctrl.Column('test')
		self.failUnless(self.ctrl.GetColumnCount()==1)
		self.ctrl.RemoveColumn(0)
		self.failUnless(self.ctrl.GetColumnCount()==0)

	def test_InsertColumn(self):
		self.failUnless(self.ctrl.GetColumnCount()==0)
		self.ctrl.InsertColumn(0, 'test')
		self.failUnless(self.ctrl.GetColumnCount()==1)
		self.ctrl.RemoveColumn(0)
		self.failUnless(self.ctrl.GetColumnCount()==0)


	def test_IterColumns(self):
		self.failUnless(self.ctrl.GetColumnCount()==0)
		for i in range(10):
			self.ctrl.Column('test')
		self.failUnless(self.ctrl.GetColumnCount()==10)

		for i in self.ctrl.IterColumns(): pass
		self.failUnless(i==9)
		
		for i in range(10):
			self.ctrl.RemoveColumn(0)
		self.failUnless(self.ctrl.GetColumnCount()==0)

	
	def test_ColumnText(self):
		self.failUnless(self.ctrl.GetColumnCount()==0)
		self.ctrl.Column('test')
		self.failUnless(self.ctrl.GetColumnCount()==1)
		
		self.failUnless(self.ctrl.GetColumnText(0)=='test')
		self.ctrl.SetColumnText(0, 'foo')
		self.failUnless(self.ctrl.GetColumnText(0)=='foo')
		
		self.ctrl.RemoveColumn(0)
		self.failUnless(self.ctrl.GetColumnCount()==0)
	

	def test_ColumnWidth(self):
		self.failUnless(self.ctrl.GetColumnCount()==0)
		self.ctrl.Column('test', width=100)
		self.failUnless(self.ctrl.GetColumnCount()==1)
		
		self.failUnless(self.ctrl.GetColumnWidth(0)==100)
		self.ctrl.SetColumnWidth(0, 10)
		self.failUnless(self.ctrl.GetColumnWidth(0)==10)
		
		self.ctrl.RemoveColumn(0)
		self.failUnless(self.ctrl.GetColumnCount()==0)
	
	
	def test_ColumnImage(self):
		self.failUnless(self.ctrl.GetColumnCount()==0)
		self.ctrl.Column('test', iImage=3)
		self.failUnless(self.ctrl.GetColumnCount()==1)
		
		self.failUnless(self.ctrl.GetColumnImage(0)==3)
		self.ctrl.SetColumnImage(0, 10)
		self.failUnless(self.ctrl.GetColumnImage(0)==10)
		
		self.ctrl.RemoveColumn(0)
		self.failUnless(self.ctrl.GetColumnCount()==0)
	

	def test_ColumnOrder(self):
		self.failUnless(self.ctrl.GetColumnCount()==0)
		for i in range(10):
			self.ctrl.Column('test')
		self.failUnless(self.ctrl.GetColumnCount()==10)

		rng= range(10)[::-1]
		self.ctrl.SetColumnOrder(*rng)
		self.failUnless(self.ctrl.GetColumnOrder()==rng)
		
		self.failUnless(self.ctrl.ColumnIndexToOrder(1)==8)
		## OrderToIndex is missing
				
		for i in range(10):
			self.ctrl.RemoveColumn(0)
		self.failUnless(self.ctrl.GetColumnCount()==0)

	
	def test_ClearColumns(self):
		self.failUnless(self.ctrl.GetColumnCount()==0)
		for i in range(10):
			self.ctrl.Column('test')
		self.failUnless(self.ctrl.GetColumnCount()==10)

		self.ctrl.ClearColumns()
		self.failUnless(self.ctrl.GetColumnCount()==0)


#*****************************************************************
# item tests
#*****************************************************************
class ItemTests:
	def test_Item(self):
		self.failUnless(self.ctrl.GetColumnCount()==0)
		self.ctrl.Column('test', iImage=3)
		self.failUnless(self.ctrl.GetColumnCount()==1)

		self.failUnless(len(self.ctrl)==0)
		self.ctrl.Item('test')
		self.failUnless(len(self.ctrl)==1)
		self.ctrl.RemoveItem(0)
		self.failUnless(len(self.ctrl)==0)
		
		self.ctrl.RemoveColumn(0)
		self.failUnless(self.ctrl.GetColumnCount()==0)

	
	def test_ItemText(self):
		self.failUnless(self.ctrl.GetColumnCount()==0)
		self.ctrl.Column('test')
		self.failUnless(self.ctrl.GetColumnCount()==1)

		self.failUnless(len(self.ctrl)==0)
		self.ctrl.Item('test')
		self.failUnless(len(self.ctrl)==1)
		
		self.failUnless(self.ctrl.GetItemText(0, 0)=='test')
		self.ctrl.SetItemText(0, 0, 'foo')
		self.failUnless(self.ctrl.GetItemText(0, 0)=='foo')

		self.ctrl.RemoveItem(0)
		self.failUnless(len(self.ctrl)==0)
		
		self.ctrl.RemoveColumn(0)
		self.failUnless(self.ctrl.GetColumnCount()==0)


	def test_SubItemText(self):
		self.failUnless(self.ctrl.GetColumnCount()==0)
		self.ctrl.Column('test')
		self.ctrl.Column('foo')
		self.failUnless(self.ctrl.GetColumnCount()==2)

		self.failUnless(len(self.ctrl)==0)
		self.ctrl.Item('test')
		self.failUnless(len(self.ctrl)==1)
		
		self.ctrl.SetItemText(0, 1, 'test')
		self.failUnless(self.ctrl.GetItemText(0, 1)=='test')
		self.ctrl.SetItemText(0, 1, 'foo')
		self.failUnless(self.ctrl.GetItemText(0, 1)=='foo')

		self.ctrl.RemoveItem(0)
		self.failUnless(len(self.ctrl)==0)
		
		self.ctrl.RemoveColumn(0)
		self.ctrl.RemoveColumn(0)
		self.failUnless(self.ctrl.GetColumnCount()==0)


	def test_ItemLparam(self):
		self.failUnless(self.ctrl.GetColumnCount()==0)
		self.ctrl.Column('test')
		self.failUnless(self.ctrl.GetColumnCount()==1)

		self.failUnless(len(self.ctrl)==0)
		self.ctrl.Item('test', lp=333)
		self.failUnless(len(self.ctrl)==1)
		
		self.failUnless(self.ctrl.GetItemLparam(0)==333)
		self.ctrl.SetItemLparam(0, 999)
		self.failUnless(self.ctrl.GetItemLparam(0)==999)

		self.ctrl.RemoveItem(0)
		self.failUnless(len(self.ctrl)==0)
		
		self.ctrl.RemoveColumn(0)
		self.failUnless(self.ctrl.GetColumnCount()==0)


	def test_ItemImage(self):
		self.failUnless(self.ctrl.GetColumnCount()==0)
		self.ctrl.Column('test')
		self.failUnless(self.ctrl.GetColumnCount()==1)

		self.failUnless(len(self.ctrl)==0)
		self.ctrl.Item('test', iImage=333)
		self.failUnless(len(self.ctrl)==1)
		
		self.failUnless(self.ctrl.GetItemImage(0, 0)==333)
		self.ctrl.SetItemImage(0, 0, 999)
		self.failUnless(self.ctrl.GetItemImage(0, 0)==999)

		self.ctrl.RemoveItem(0)
		self.failUnless(len(self.ctrl)==0)
		
		self.ctrl.RemoveColumn(0)
		self.failUnless(self.ctrl.GetColumnCount()==0)


	####
	#### Fails (tested on 'life' Listview passes the test)
	def XXXtest_SubItemImage(self):
		self.failUnless(self.ctrl.GetColumnCount()==0)
		self.ctrl.Column('test')
		self.ctrl.Column('foo')
		self.failUnless(self.ctrl.GetColumnCount()==2)

		self.failUnless(len(self.ctrl)==0)
		self.ctrl.Item('test')
		self.failUnless(len(self.ctrl)==1)
		
		self.ctrl.SetItemImage(0, 1, 1)
		self.failUnless(self.ctrl.GetItemImage(0, 1)==1)
		self.ctrl.SetItemImage(0, 1, 2)
		self.failUnless(self.ctrl.GetItemImage(0, 1)==2)

		self.ctrl.RemoveItem(0)
		self.failUnless(len(self.ctrl)==0)
		
		self.ctrl.RemoveColumn(0)
		self.ctrl.RemoveColumn(0)
		self.failUnless(self.ctrl.GetColumnCount()==0)

		
	def test_ItemStateImage(self):
		self.failUnless(self.ctrl.GetColumnCount()==0)
		self.ctrl.Column('test')
		self.failUnless(self.ctrl.GetColumnCount()==1)

		self.failUnless(len(self.ctrl)==0)
		self.ctrl.Item('test', iStateImage=3)
		self.failUnless(len(self.ctrl)==1)
		
		self.failUnless(self.ctrl.GetItemStateImage(0)==3)
		self.ctrl.SetItemStateImage(0,9)
		self.failUnless(self.ctrl.GetItemStateImage(0)==9)

		self.ctrl.RemoveItem(0)
		self.failUnless(len(self.ctrl)==0)
		
		self.ctrl.RemoveColumn(0)
		self.failUnless(self.ctrl.GetColumnCount()==0)


	def test_ItemMisc(self):
		self.failUnless(self.ctrl.GetColumnCount()==0)
		self.ctrl.Column('test')
		self.failUnless(self.ctrl.GetColumnCount()==1)

		self.failUnless(len(self.ctrl)==0)
		self.ctrl.Item('test')
		self.failUnless(len(self.ctrl)==1)
		
		pt= self.ctrl.GetItemPos(0)
		rc= self.ctrl.GetItemRect(0, 0)
		rc= self.ctrl.GetItemIconRect(0, 0)
		rc= self.ctrl.GetItemLabelRect(0, 0)
		rc= self.ctrl.GetItemSelectedRect(0)

		self.ctrl.RemoveItem(0)
		self.failUnless(len(self.ctrl)==0)
		self.ctrl.RemoveColumn(0)
		self.failUnless(self.ctrl.GetColumnCount()==0)
		

#*****************************************************************
# item state tests
#*****************************************************************
class ItemStateTests:
	
	def test_ItemFocus(self):
		self.failUnless(self.ctrl.GetColumnCount()==0)
		self.ctrl.Column('test')
		self.failUnless(self.ctrl.GetColumnCount()==1)

		self.failUnless(len(self.ctrl)==0)
		self.ctrl.Item('test')
		self.failUnless(len(self.ctrl)==1)

		self.ClearMsgCache()
				
		self.ctrl.SetFocus()
		self.ctrl.SetFocusItem(0)
		self.failUnless(self.ctrl.ItemHasFocus(0))
			
		msg= self.GetMsg("itemchanged")
		self.failUnless(msg, "no message: itemchanged")
		self.failIf('focused' in self.ctrl.StateToString(msg[3][0]))
		self.failUnless('focused' in self.ctrl.StateToString(msg[3][1]))
			
		self.failUnless(self.ctrl.GetFocusItem()==None)		## Fails
		self.ctrl.RemoveItemFocus(0)
		self.failIf(self.ctrl.ItemHasFocus(0))
		self.failUnless(self.ctrl.GetFocusItem()==None)
		
		msg= self.GetMsg("itemchanged")
		self.failUnless(msg, "no message: itemchanged")
		
		self.failUnless('focused' in self.ctrl.StateToString(msg[3][0]))
		self.failIf('focused' in self.ctrl.StateToString(msg[3][1]))
		


		self.ctrl.RemoveItem(0)
		self.failUnless(len(self.ctrl)==0)
		self.ctrl.RemoveColumn(0)
		self.failUnless(self.ctrl.GetColumnCount()==0)
	
	
	def test_ItemSelect(self):
		self.failUnless(self.ctrl.GetColumnCount()==0)
		self.ctrl.Column('test')
		self.failUnless(self.ctrl.GetColumnCount()==1)

		self.failUnless(len(self.ctrl)==0)
		self.ctrl.Item('test')
		self.failUnless(len(self.ctrl)==1)

		self.ClearMsgCache()
		
		self.ctrl.SelectItem(0)
		self.failUnless(self.ctrl.GetSelectedItem()==0)
		self.failUnless(self.ctrl.GetSelectedCount()==1)
		
		msg= self.GetMsg("itemchanged")
		self.failUnless(msg, "no message: itemchanged")
		self.failIf('selected' in self.ctrl.StateToString(msg[3][0]))
		self.failUnless('selected' in self.ctrl.StateToString(msg[3][1]))
		
		i= None
		for i in self.ctrl.IterSelected(): pass
		self.failIf(i==None)
		self.ctrl.DeselectItem(0)
		self.failUnless(self.ctrl.GetSelectedItem()==None)

		msg= self.GetMsg("itemchanged")
		self.failUnless(msg, "no message: itemchanged")
		self.failUnless('selected' in self.ctrl.StateToString(msg[3][0]))
		self.failIf('selected' in self.ctrl.StateToString(msg[3][1]))
								
		self.ctrl.RemoveItem(0)
		self.failUnless(len(self.ctrl)==0)
		self.ctrl.RemoveColumn(0)
		self.failUnless(self.ctrl.GetColumnCount()==0)


	def test_ItemCutHilight(self):
		self.failUnless(self.ctrl.GetColumnCount()==0)
		self.ctrl.Column('test')
		self.failUnless(self.ctrl.GetColumnCount()==1)

		self.failUnless(len(self.ctrl)==0)
		self.ctrl.Item('test')
		self.failUnless(len(self.ctrl)==1)

		self.ClearMsgCache()
		
		self.ctrl.CutSelectItem(0)
		self.failUnless(self.ctrl.IsItemCutSelected(0))
		msg= self.GetMsg("itemchanged")
		self.failUnless(msg, "no message: itemchanged")
		self.failIf('cuthilighted' in self.ctrl.StateToString(msg[3][0]))
		self.failUnless('cuthilighted' in self.ctrl.StateToString(msg[3][1]))
		
		self.ctrl.RemoveItemCutSelect(0)
		self.failIf(self.ctrl.IsItemCutSelected(0))
		msg= self.GetMsg("itemchanged")
		self.failUnless(msg, "no message: itemchanged")
		self.failUnless('cuthilighted' in self.ctrl.StateToString(msg[3][0]))
		self.failIf('cuthilighted' in self.ctrl.StateToString(msg[3][1]))
		
		self.ctrl.RemoveItem(0)
		self.failUnless(len(self.ctrl)==0)
		self.ctrl.RemoveColumn(0)
		self.failUnless(self.ctrl.GetColumnCount()==0)	

	
	def test_ItemDropHilight(self):
		self.failUnless(self.ctrl.GetColumnCount()==0)
		self.ctrl.Column('test')
		self.failUnless(self.ctrl.GetColumnCount()==1)

		self.failUnless(len(self.ctrl)==0)
		self.ctrl.Item('test')
		self.failUnless(len(self.ctrl)==1)

		self.ClearMsgCache()
		
		self.ctrl.DropHilightItem(0)
		self.failUnless(self.ctrl.IsItemDropHilighted(0))
		msg= self.GetMsg("itemchanged")
		self.failUnless(msg, "no message: itemchanged")
		self.failIf('drophilighted' in self.ctrl.StateToString(msg[3][0]))
		self.failUnless('drophilighted' in self.ctrl.StateToString(msg[3][1]))
				
		self.ctrl.RemoveItemDropHilight(0)
		self.failIf(self.ctrl.IsItemCutSelected(0))
		msg= self.GetMsg("itemchanged")
		self.failUnless(msg, "no message: itemchanged")
		self.failUnless('drophilighted' in self.ctrl.StateToString(msg[3][0]))
		self.failIf('drophilighted' in self.ctrl.StateToString(msg[3][1]))

		self.ctrl.RemoveItem(0)
		self.failUnless(len(self.ctrl)==0)
		self.ctrl.RemoveColumn(0)
		self.failUnless(self.ctrl.GetColumnCount()==0)		


#*****************************************************************
# default tests
#*****************************************************************

class Tests(helpers.Helpers, ColumnTests, ItemTests, ItemStateTests):
	
	def __init__(self):
		helpers.Helpers.__init__(self)
		
			
	def test_Find(self):
		self.failUnless(self.ctrl.GetColumnCount()==0)
		self.ctrl.Column('test')
		self.failUnless(self.ctrl.GetColumnCount()==1)

		self.failUnless(len(self.ctrl)==0)
		self.ctrl.Item('hard to find',lp=999)
		self.failUnless(len(self.ctrl)==1)

		self.failUnless(self.ctrl.Find('hard')==0)
		self.failUnless(self.ctrl.FindExact('hard to find')==0)
		self.failUnless(self.ctrl.FindExact('easy to miss')==None)
		self.failUnless(self.ctrl.FindLparam(999)==0)
		self.failUnless(self.ctrl.FindLparam(111)==None)
		self.failUnless(self.ctrl.FindXY(-1000, -1000)==None)

		self.ctrl.RemoveItem(0)
		self.failUnless(len(self.ctrl)==0)
		self.ctrl.RemoveColumn(0)
		self.failUnless(self.ctrl.GetColumnCount()==0)

	
	def test_Imagelist(self):
		imgl= Imagelist(10, 10, 1, 0)

		self.ctrl.SetImagelistNormal(imgl)
		self.failUnless(self.ctrl.GetImagelistNormal()==imgl.handle)
		self.ctrl.SetImagelistNormal(None)
		self.failUnless(self.ctrl.GetImagelistNormal()==None)

		self.ctrl.SetImagelistSmall(imgl)
		self.failUnless(self.ctrl.GetImagelistSmall()==imgl.handle)
		self.ctrl.SetImagelistSmall(None)
		self.failUnless(self.ctrl.GetImagelistSmall()==None)
		
		self.ctrl.SetImagelistState(imgl)
		self.failUnless(self.ctrl.GetImagelistState()==imgl.handle)
		self.ctrl.SetImagelistState(None)
		self.failUnless(self.ctrl.GetImagelistState()==None)
				
		imgl.Close()
	
	
	def test_Colors(self):
		color= 123
		self.ctrl.SetBkColor(color)
		self.failUnless(self.ctrl.GetBkColor()==color)
		color= 234
		self.ctrl.SetTextColor(color)
		self.failUnless(self.ctrl.GetTextColor()==color)
		color= 345
		self.ctrl.SetTextBkColor(color)
		self.failUnless(self.ctrl.GetTextBkColor()==color)

	
	
	def test_ChildControls(self):
		self.failIf(self.ctrl.GetHeaderControl()==None)
		self.assertRaises(RuntimeError, self.ctrl.GetEditControl)
	
	
	def test_editlabel(self):
		self.failUnless(self.ctrl.GetColumnCount()==0)
		self.ctrl.Column('test')
		self.failUnless(self.ctrl.GetColumnCount()==1)

		self.failUnless(len(self.ctrl)==0)
		self.ctrl.Item('test')
		self.failUnless(len(self.ctrl)==1)
		
		## fails if listview does not have keyboard focus
		self.ctrl.SetFocus()
		self.ctrl.EditLabel(0)
		msg= self.GetMsg("beginlabeledit")
		self.failUnless(msg)
		self.failUnless(msg[2]=='test')	## label text
				
		ed= self.ctrl.GetEditControl()
		self.failUnless(ed)
		ed.SetText('foo')
		self.failUnless(ed.GetText()=='foo')
		ed.SendMessage(ed.Hwnd, ed.Msg.WM_KEYDOWN, 13, 0)
		ed.SendMessage(ed.Hwnd, ed.Msg.WM_KEYUP, 13, 0)
		## could not get this to work from  here
		## labeledit is ended, but text not returned
		msg= self.GetMsg("endlabeledit")
		self.failUnless(msg)
		
		self.ctrl.RemoveItem(0)
		self.failUnless(len(self.ctrl)==0)
		self.ctrl.RemoveColumn(0)
		self.failUnless(self.ctrl.GetColumnCount()==0)

			
	def test_Misc(self):
		self.failIf(self.ctrl.GetStringWidth('long') >= self.ctrl.GetStringWidth('longer'))
		self.failIf(self.ctrl.ItemHittest(-1000, -1000))
		self.ctrl.SetItemCount(1000)
		h= self.ctrl.GetPageCount()
		w, h= self.ctrl.ApproximateViewRect(-1)

		

#*****************************************************************
# test Listview classes
#*****************************************************************
	
##
class TestListview(unittest.TestCase, Tests):
	def setUp(self):
		self.ctrl= Listview(PARENT ,  0, 0, 40, 40, 'report', 'editlabels')
		Tests.__init__(self)

	def tearDown(self):
		self.ctrl.Close()
		

##
class TestListviewFromHandle(unittest.TestCase, Tests):
	def setUp(self):
		self.ctrl0= Listview(PARENT , 0, 0, 40, 40, 'report', 'editlabels')
		self.ctrl= ListviewFromHandle(self.ctrl0.Hwnd)
		Tests.__init__(self)

	def tearDown(self):
		self.ctrl0.Close()
		self.ctrl.Close()
	
	
#****************************************************************
#***************************************************************
def suite():
	return (unittest.makeSuite(TestListview),
				unittest.makeSuite(TestListviewFromHandle),
					)


	
						

if __name__=='__main__':
	mod= imp.load_source('foo', PATH_STANDALONE)
	PARENT= mod.Main()
	PARENT.RunTest(suite)
	helpers.RemovePyc(PATH)
	

	
