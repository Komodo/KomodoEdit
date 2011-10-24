import logging
import unittest
from koTreeView import *

class View(object):
    def __init__(self, log):
        self.log = log
        self.rowCount = 0
    @property
    def _tree(self):
        return self
    def invalidateRange(self, start, end):
        log.debug("invalidate range: %r -> %r", start, end)
    def rowCountChanged(self, index, delta):
        log.debug("row count changed: %r -> %r", index, delta)

""" Helper to keep the view's rowCount in sync with expected values """
def rowCountChanged(invalidater, index, delta):
    invalidater.view.rowCount += delta
    invalidater.rowCountChanged(index, delta)

class InvalidationRangeTestCase(unittest.TestCase):
    def setUp(self):
        self.log = logging.getLogger("InvalidationRange")
        log.setLevel(logging.DEBUG)
        self.view = View(self.log)

    def test_rowcount_basic(self):
        invalidater = InvalidationRange(self.view, log=self.log)
        with invalidater:
            # a, b, c
            rowCountChanged(invalidater, 0, 3)
            self.assertEquals(invalidater.ranges,
                              [[0, 0, 3]])
            # a,    c
            rowCountChanged(invalidater, 1, -1)
            self.assertEquals(invalidater.ranges,
                              [[0, 0, 2]])
            # a,    c,    d
            rowCountChanged(invalidater, 2, 1)
            self.assertEquals(invalidater.ranges,
                              [[0, 0, 3]])
            # a,    c, e, d
            rowCountChanged(invalidater, 2, 1)
            self.assertEquals(invalidater.ranges,
                              [[0, 0, 4]])
            # a,    c,    d
            rowCountChanged(invalidater, 2, -1)
            self.assertEquals(invalidater.ranges,
                              [[0, 0, 3]])

    def test_rowcount_removal(self):
        invalidater = InvalidationRange(self.view, log=self.log)
            # a, b, c, d, e, f
        with invalidater:
            #    b, c, d, e, f
            rowCountChanged(invalidater, 0, -1)
            self.assertEquals(invalidater.ranges,
                              [[0, 0, -1]])
            #    b,       e, f
            rowCountChanged(invalidater, 1, -2)
            self.assertEquals(invalidater.ranges,
                              [[0, 0, -1], [2, 2, -2]])
            #             e, f
            rowCountChanged(invalidater, 0, -1)
            self.assertEquals(invalidater.ranges,
                              [[0, 0, -4]])
            #             e, f, g
            rowCountChanged(invalidater, 2, 1)
            self.assertEquals(invalidater.ranges,
                              [[0, 0, -4], [6, 6, 1]])
            #             e, g
            rowCountChanged(invalidater, 1, -1)
            self.assertEquals(invalidater.ranges,
                              [[0, 0, -4], [5, 5, 0]])
            # h,          e, g
            rowCountChanged(invalidater, 0, 1)
            self.assertEquals(invalidater.ranges,
                              [[0, 0, -3], [5, 5, 0]])

    def test_invalidate(self):
        # this one is from actually running komodo
        invalidater = InvalidationRange(self.view, log=self.log)
            # a, b,       c, d, e, f
        with invalidater:
            # a, B,       C, d, e, f
            invalidater.invalidate(1, 2)
            self.assertEquals(invalidater.ranges,
                              [[1, 3, 0]])
            # a, B, G, H, C, d, e, f
            rowCountChanged(invalidater, 2, 2)
            self.assertEquals(invalidater.ranges,
                              [[1, 3, 2]])
            # a, B, G, H, C, D, e, f
            invalidater.invalidate(4, 5)
            self.assertEquals(invalidater.ranges,
                              [[1, 4, 2]])
            # a, B, G, H, C, D, E, f
            invalidater.invalidate(5, 6)
            self.assertEquals(invalidater.ranges,
                              [[1, 5, 2]])
            # a, B, G, H, C, D, I, E, f
            rowCountChanged(invalidater, 6, 1)
            self.assertEquals(invalidater.ranges,
                              [[1, 5, 3]])
            # a, B, G, H, C, J, K, D, I, E, f
            rowCountChanged(invalidater, 5, 2)
            self.assertEquals(invalidater.ranges,
                              [[1, 5, 5]])
            # a, B, G, H, L, M, N, C, J, K, D, I, E, f
            rowCountChanged(invalidater, 4, 3)
            self.assertEquals(invalidater.ranges,
                              [[1, 5, 8]])
            # a, B, G, H, L, M, N, C, J, K, D, I, E, f
            invalidater.invalidate(7, 9)
            self.assertEquals(invalidater.ranges,
                              [[1, 5, 8]])

    def test_invalidate_2(self):
        """Test invalidations with various corner cases"""
        # for the comments, the old range is marked as [ ]-->
        # where [ is start, ] is end, and --> (or <--) is the delta
        # the new range is marked as {  }
        invalidater = InvalidationRange(self.view, log=self.log)

        with invalidater:
            # {  }  [  ]
            invalidater.invalidate(10, 20)
            invalidater.invalidate(1, 2)
            self.assertEquals(invalidater.ranges,
                              [[1, 3, 0], [10, 21, 0]])
        with invalidater:
            # {  }  [  ]-->
            invalidater.invalidate(10, 20)
            rowCountChanged(invalidater, 10, 10)
            invalidater.invalidate(1, 2)
            self.assertEquals(invalidater.ranges,
                              [[1, 3, 0], [10, 21, 10]])
        with invalidater:
            # {  }  [  ]<--
            invalidater.invalidate(10, 20)
            rowCountChanged(invalidater, 10, -10)
            invalidater.invalidate(1, 2)
            self.assertEquals(invalidater.ranges,
                              [[1, 3, 0], [10, 21, -10]])
        with invalidater:
            # {  [  }  ]
            invalidater.invalidate(10, 20)
            invalidater.invalidate(5, 15)
            self.assertEquals(invalidater.ranges,
                              [[5, 21, 0]])
        with invalidater:
            # {  [  }  ]-->
            invalidater.invalidate(10, 20)
            rowCountChanged(invalidater, 10, 10)
            invalidater.invalidate(5, 15)
            self.assertEquals(invalidater.ranges,
                              [[5, 21, 10]])
        with invalidater:
            # {  [  }  ]<--
            invalidater.invalidate(10, 20)
            rowCountChanged(invalidater, 10, -10)
            invalidater.invalidate(5, 15)
            self.assertEquals(invalidater.ranges,
                              [[5, 21, -10]])
        with invalidater:
            # {  [  ]  }
            invalidater.invalidate(10, 20)
            invalidater.invalidate(5, 25)
            self.assertEquals(invalidater.ranges,
                              [[5, 26, 0]])
        with invalidater:
            # {  [  ]--}-->
            invalidater.invalidate(10, 20)
            rowCountChanged(invalidater, 10, 10)
            invalidater.invalidate(5, 25)
            self.assertEquals(invalidater.ranges,
                              [[5, 26, 10]])
        with invalidater:
            # {  [  ]<--}--
            invalidater.invalidate(10, 20)
            rowCountChanged(invalidater, 10, -10)
            invalidater.invalidate(5, 25)
            self.assertEquals(invalidater.ranges,
                              [[5, 26, -10]])
        with invalidater:
            # [  {  ]  }
            invalidater.invalidate(10, 20)
            invalidater.invalidate(15, 25)
            self.assertEquals(invalidater.ranges,
                              [[10, 26, 0]])
        with invalidater:
            # [  {  ]--}-->
            invalidater.invalidate(10, 20)
            rowCountChanged(invalidater, 10, 10)
            invalidater.invalidate(15, 25)
            self.assertEquals(invalidater.ranges,
                              [[10, 26, 10]])
        with invalidater:
            # [  {  ]<--}--
            invalidater.invalidate(10, 20)
            rowCountChanged(invalidater, 10, -10)
            invalidater.invalidate(15, 25)
            self.assertEquals(invalidater.ranges,
                              [[10, 26, -10]])
        with invalidater:
            # [  ]  {  }
            invalidater.invalidate(10, 20)
            invalidater.invalidate(30, 40)
            self.assertEquals(invalidater.ranges,
                              [[10, 21, 0], [30, 41, 0]])
        with invalidater:
            # [  ]-->  {  }
            invalidater.invalidate(10, 20)
            rowCountChanged(invalidater, 10, 10)
            invalidater.invalidate(50, 60)
            self.assertEquals(invalidater.ranges,
                              [[10, 21, 10], [40, 51, 0]])
        with invalidater:
            # [  ]<--  {  }
            invalidater.invalidate(10, 20)
            rowCountChanged(invalidater, 10, -10)
            invalidater.invalidate(50, 60)
            self.assertEquals(invalidater.ranges,
                              [[10, 21, -10], [60, 71, 0]])
        with invalidater:
            # [  ]--{-->  }
            invalidater.invalidate(10, 20)
            rowCountChanged(invalidater, 10, 10)
            invalidater.invalidate(25, 35)
            self.assertEquals(invalidater.ranges,
                              [[10, 26, 10]])
        with invalidater:
            # [  ]<--{--  }
            invalidater.invalidate(10, 20)
            rowCountChanged(invalidater, 10, -10)
            invalidater.invalidate(25, 35)
            self.assertEquals(invalidater.ranges,
                              [[10, 21, -10], [35, 46, 0]])
        with invalidater:
            # [  ]--{--}-->
            invalidater.invalidate(10, 20)
            rowCountChanged(invalidater, 10, 10)
            invalidater.invalidate(23, 28)
            self.assertEquals(invalidater.ranges,
                              [[10, 21, 10]])
        with invalidater:
            # [  ]<--{--}--
            invalidater.invalidate(10, 20)
            rowCountChanged(invalidater, 10, -10)
            invalidater.invalidate(23, 28)
            self.assertEquals(invalidater.ranges,
                              [[10, 21, -10], [33, 39, 0]])
        with invalidater:
            # [  {  }  ]
            invalidater.invalidate(10, 20)
            invalidater.invalidate(13, 18)
            self.assertEquals(invalidater.ranges,
                              [[10, 21, 0]])
        with invalidater:
            # [  {  }  ]-->
            invalidater.invalidate(10, 20)
            rowCountChanged(invalidater, 10, 10)
            invalidater.invalidate(13, 18)
            self.assertEquals(invalidater.ranges,
                              [[10, 21, 10]])
        with invalidater:
            # [  {  }  ]<--
            invalidater.invalidate(10, 20)
            rowCountChanged(invalidater, 10, -10)
            invalidater.invalidate(13, 18)
            self.assertEquals(invalidater.ranges,
                              [[10, 21, -10]])

def test_cases():
    return [InvalidationRangeTestCase]
