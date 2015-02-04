import unittest

from codeintel2.accessor import Accessor, AccessorCache

class _TestAccessor(Accessor):
    """Fake accessor testing class."""
    def __init__(self, content, styles):
        self.content = content
        self.style = styles
    def length(self):
        return len(self.content)
    def char_at_pos(self, pos):
        return self.content[pos]
    def style_at_pos(self, pos):
        return self.style[pos]
    def gen_char_and_style_back(self, start, stop):
        assert -1 <= stop <= start, "stop: %r, start: %r" % (stop, start)
        for pos in range(start, stop, -1):
            yield (self.char_at_pos(pos), self.style_at_pos(pos))
    def gen_char_and_style(self, start, stop):
        assert 0 <= start <= stop, "start: %r, stop: %r" % (start, stop)
        for pos in range(start, stop):
            yield (self.char_at_pos(pos), self.style_at_pos(pos))
    def text_range(self, start, end):
        return self.content[start:end]

class TestAccessorCache(unittest.TestCase):

    def test_basics(self):
        content = "This is my test buffer\r\nSecond   line\r\nThird line\r\n"
        styles =  "1111011011011110111111 2 21111110001111 2 21111101111 2 2".replace(" ", "")
        ta = _TestAccessor(content, map(int, styles))
        pos = len(content) - 2
        ac = AccessorCache(ta, pos)
        #ac._debug = True
        for i in range(2):
            assert(ac.getPrevPosCharStyle() == (pos-1, "e", 1))
            assert(ac.getPrecedingPosCharStyle(1) == (pos-5, " ", 0))
            assert(ac.getPrecedingPosCharStyle(0) == (pos-6, "d", 1))
            assert(ac.getPrecedingPosCharStyle(1) == (pos-11, "\n", 2))
            assert(ac.getPrecedingPosCharStyle()  == (pos-13, "e", 1))
            assert(ac.getTextBackWithStyle(1) == (pos-16, "line"))
            assert(ac.getPrevPosCharStyle() == (pos-17, " ", 0))
            assert(ac.getPrecedingPosCharStyle(0) == (pos-20, "d", 1))
            if i == 0:
                ac.resetToPosition(pos)
    
        assert(ac.getCurrentPosCharStyle() == (pos-20, "d", 1))
    
        #print pos
        #print ac.getSucceedingPosCharStyle()
        assert(ac.getNextPosCharStyle() == (pos-19, " ", 0))
        assert(ac.getSucceedingPosCharStyle() == (pos-16, "l", 1))
        assert(ac.getTextForwardWithStyle(1) == (pos-13, "line"))
        assert(ac.getNextPosCharStyle() == (pos-12, "\r", 2))
        assert(ac.getNextPosCharStyle() == (pos-11, "\n", 2))
        assert(ac.getSucceedingPosCharStyle(2) == (pos-10, "T", 1))
        assert(ac.getSucceedingPosCharStyle() == (pos-5, " ", 0))
        assert(ac.getSucceedingPosCharStyle() == (pos-4, "l", 1))
        assert(ac.getSucceedingPosCharStyle() == (pos, "\r", 2))
        assert(ac.getNextPosCharStyle() == (pos+1, "\n", 2))
    
        # Bug: http://bugs.activestate.com/show_bug.cgi?id=64227
        #      Ensure text_range uses correct parameters in boundary situations
        ac.resetToPosition(3)
        assert(ac.getTextBackWithStyle(1)[1] == "This")
        ac.resetToPosition(len(content) - 2)
        assert(ac.getTextForwardWithStyle(2)[1] == "\r\n")
