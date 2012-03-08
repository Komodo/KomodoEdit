import logging
import unittest
from koTreeView import *
from testlib import tag

class TreeBoxObject(object):
    def __init__(self, log):
        self.log = log
        self.rowCount = 0
    @property
    def _tree(self):
        return self
    @property
    def selection(self):
        return None
    def invalidateRange(self, start, end):
        self.log.debug("invalidate range: %r -> %r", start, end)
    def rowCountChanged(self, index, delta):
        self.log.debug("row count changed: %r -> %r", index, delta)

""" Helper to keep the view's rowCount in sync with expected values """
def rowCountChanged(invalidater, index, delta):
    invalidater.view.rowCount += delta
    invalidater.rowCountChanged(index, delta)

class InvalidationRangeTestCase(unittest.TestCase):
    def setUp(self):
        self.log = logging.getLogger("InvalidationRange")
        #self.log.setLevel(logging.DEBUG)
        self.view = TreeBoxObject(self.log)

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
                              [[0, 0, -4], [5, 6, 0]])
            # h,          e, g
            rowCountChanged(invalidater, 0, 1)
            self.assertEquals(invalidater.ranges,
                              [[0, 4, -3], [5, 6, 0]])

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

    @tag("bug92682")
    def test_remove_and_readd(self):
        """Test that removing and adding rows will invalidate the newly-exposed
           rows"""
        invalidater = InvalidationRange(self.view, log=self.log)
        with invalidater:
            rowCountChanged(invalidater, 1, -17)
            self.assertEquals(invalidater.ranges,
                              [[1, 1, -17]])
            invalidater.invalidate(1, 2)
            self.assertEquals(invalidater.ranges,
                              [[1, 3, -17]])
            rowCountChanged(invalidater, 2, 18)
            self.assertEquals(invalidater.ranges,
                              [[1, 19, 1]])
        with invalidater:
            rowCountChanged(invalidater, 1, -17)
            self.assertEquals(invalidater.ranges,
                              [[1, 1, -17]])
            rowCountChanged(invalidater, 1, 17)
            self.assertEquals(invalidater.ranges,
                              [[1, 18, 0]])

class ParentIndexTestCase(unittest.TestCase):
    """ Test cases for finding the parent index """
    def setUp(self):
        self.log = logging.getLogger("koTreeView.parentIndex")
        #self.log.setLevel(logging.DEBUG)
        self.view = ObjectTreeView() #debug="koTreeView.parentIndex")
        boxObject = TreeBoxObject(self.log)
        self.view.setTree(boxObject)

        # This is a template of the tree we want to test with.  It's a tuple,
        # where each item is a tuple of (name, subtree).  Each subtree is again
        # a tuple of the same format.
        template = (
            ("root", (
                ("prev-gp-sibling", ()),
                ("grandparent", (
                    ("parent", (
                        ("one", ()),
                        ("two", ()),
                        ("three", ()),
                        ("four", ()),
                        ("five", ()),
                        ("six", ()),
                        ("seven", ()),
                    )),
                    ("next-p-sibling", (
                        ("cousin-one", ()),
                        ("cousin-two", ()),
                        ("cousin-three", ()),
                        ("cousin-four", ()),
                        ("cousin-five", ()),
                    )),
                )),
                ("next-gp-sibling", ()),
            )),
            ("next-root", ()),
        )

        self.build_tree(self.view, template)

    def build_tree(self, parent, template):
        assert isinstance(template, tuple), \
            "Trying to build tree from a non-tuple template %r" % (template,)
        for child in template:
            assert isinstance(child, tuple), \
                "Trying to build template but found non-tuple child %r" % (child,)
            assert len(child) == 2, \
                "Trying to build template but found invalid child %r" % (child,)
            item = ObjectTreeViewItem(log = self.view.log)
            setattr(item, "text", child[0])
            self.build_tree(item, child[1])
            parent.insertChild(item)

    def dump(self):
        """Dump the current tree"""
        def dump_node(node, indent):
            attrs = filter(lambda name: getattr(node, name, False),
                           ("open", "invisible", "hidden"))
            attrs = " %s" % (" ".join(attrs)) if attrs else ""
            self.log.info("%s<%s%s @ %r + %r>",
                          indent, node.text, attrs, node.rowIndex, node.rowCount)
            for child in node.children:
                dump_node(child, "  %s" % (indent,))
        self.log.info("-" * 10)
        dump_node(self.view, "")

    def get_item(self, text):
        """Get the first item with the given text"""
        found = []
        def do_filter(node):
            if node.text == text:
                found.append(node)
                raise StopIteration
            for child in node.children:
                do_filter(child)
        try:
            do_filter(self.view)
        except StopIteration:
            return found[0] if len(found) > 0 else None

    def test_template_construction(self):
        def dump_item(item, indent=""):
            self.log.debug("%03i %s%s", item.rowIndex, indent, item.text)
            for child in item.children:
                dump_item(child, "%s  " % (indent,))
        dump_item(self.view)

    def test_parentIndex_basic(self):
        def check_item(parent):
            for child in parent.children:
                self.assertEquals(parent.rowIndex,
                                  self.view.getParentIndex(child.rowIndex))
                check_item(child)
        for child in self.view.children:
            self.assertEquals(self.view.getParentIndex(child.rowIndex), -1)
            check_item(child)

    def test_close_flush(self):
        """Closing a not-visible child should still cause its parents to
        recalculate children row count data so that things are in sync once the
        child becomes visible again"""
        items = {}
        for name in ("root", "grandparent", "parent", "next-p-sibling"):
            items[name] = self.get_item(name)
            self.assertEquals(name, items[name].text, "got the wrong item")
            items[name].rowIndex # populate the cache
            items[name].rowCount # populate the cache
        items["root"].open = False
        items["grandparent"].invisible = True
        items["parent"].open = False
        items["next-p-sibling"].open = False
        items["root"].open = True
        self.assertEquals(items["grandparent"].rowCount, 2)

def test_cases():
    return [InvalidationRangeTestCase, ParentIndexTestCase]
