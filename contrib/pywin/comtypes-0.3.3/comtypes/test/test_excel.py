# -*- coding: latin-1 -*-
import unittest

import comtypes.test
comtypes.test.requires("ui")

import datetime

from comtypes.client import CreateObject

class Test(unittest.TestCase):
    def setUp(self):
        self.xl = CreateObject("Excel.Application")

    def test_excel(self):
        xl = self.xl
        xl.Visible = 0
        self.failUnlessEqual(xl.Visible, False)
        xl.Visible = 1
        self.failUnlessEqual(xl.Visible, True)

        wb = xl.Workbooks.Add()

        xl.Range("A1", "C1").Value = (1,"2",3.14)
        xl.Range("A2:C2").Value = ('x','y','z')
        xl.Range("A3:C3").Value = ('3','2','1')

        self.failUnlessEqual(xl.Range("A1:C3").Value,
                             ((1.0, 2.0, 3.14),
                              ("x", "y", "z"),
                              (3.0, 2.0, 1.0)))

        self.failUnlessEqual(xl.Range("A1", "C3").Value,
                             ((1.0, 2.0, 3.14),
                              ("x", "y", "z"),
                              (3.0, 2.0, 1.0)))

        for i in xrange(20):
            xl.Cells(i+1,i+1).Value = "Hi %d" % i

        # test dates out with Excel
        xl.Range("A5").Value = "Excel time"
        xl.Range("B5").Formula = "=Now()"
        self.failUnlessEqual(xl.Cells(5,2).Formula, "=NOW()")

        xl.Range("A6").Calculate()
        excel_time = xl.Range("B5").Value
        self.failUnlessEqual(type(excel_time), datetime.datetime)
        python_time = datetime.datetime.now()

        self.failUnless(python_time >= excel_time)
        self.failUnless(python_time - excel_time < datetime.timedelta(seconds=1))

        # How does "xl.Cells.Item(1, 2)" work?
        # xl.Cells is a POINTER(Range) instance.
        # Callign this is the same as calling it's .Item value:
        self.failUnlessEqual(xl.Cells.Item(1, 2).Value,
                             xl.Cells(1, 2).Value)

        # some random code, grabbed from c.l.p
        sh = wb.Worksheets(1)

        sh.Cells(1,1).Value = "Hello World!"
        sh.Cells(3,3).Value = "Hello World!"
        sh.Range(sh.Cells(1,1),sh.Cells(3,3)).Copy(sh.Cells(4,1))
        sh.Range(sh.Cells(4,1),sh.Cells(6,3)).Select()

        import time
        time.sleep(2)
    
    def tearDown(self):
        # Close all open workbooks without saving, then quit excel.
        for wb in self.xl.Workbooks:
            wb.Close(0)
        self.xl.Quit()

if __name__ == "__main__":
    unittest.main()
