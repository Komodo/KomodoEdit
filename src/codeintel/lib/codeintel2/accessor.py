#!python
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
# 
# The contents of this file are subject to the Mozilla Public License
# Version 1.1 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
# 
# Software distributed under the License is distributed on an "AS IS"
# basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
# License for the specific language governing rights and limitations
# under the License.
# 
# The Original Code is Komodo code.
# 
# The Initial Developer of the Original Code is ActiveState Software Inc.
# Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
# ActiveState Software Inc. All Rights Reserved.
# 
# Contributor(s):
#   ActiveState Software Inc
# 
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
# 
# ***** END LICENSE BLOCK *****


"""The Accessor interface (and implementations) for accessing scintilla
lexer-based styled buffers.
"""
from __future__ import print_function

import bisect
import math
import re
import threading

from SilverCity import ScintillaConstants

from codeintel2.common import *
from codeintel2 import util

if _xpcom_:
    from xpcom import components
    from xpcom.client import WeakReference
    from xpcom import COMException



class Accessor(object):
    """Virtual base class for a lexed text accessor. This defines an API
    with which lexed text data (the text content, styling info, etc.) is
    accessed by trigger/completion/etc. handling. Actual instances will
    be one of the subclasses.
    """
    def char_at_pos(self, pos):
        raise VirtualMethodError()
    def style_at_pos(self, pos):
        raise VirtualMethodError()
    def line_and_col_at_pos(self, pos):
        raise VirtualMethodError()
    def gen_char_and_style_back(self, start, stop):
        """Generate (char, style) tuples backward from start to stop
        a la range(start, stop, -1) -- i.e. exclusive at 'stop' index.

        For SciMozAccessor this can be implemented more efficiently than
        the naive usage of char_at_pos()/style_at_pos().
        """
        raise VirtualMethodError()
    def gen_char_and_style(self, start, stop):
        """Generate (char, style) tuples forward from start to stop
        a la range(start, stop) -- i.e. exclusive at 'stop' index.

        For SciMozAccessor this can be implemented more efficiently than
        the naive usage of char_at_pos()/style_at_pos().
        """
        raise VirtualMethodError()
    def match_at_pos(self, pos, s):
        """Return True if the given string matches the text at the given
        position.
        """
        raise VirtualMethodError()
    def line_from_pos(self, pos):
        """Return the 0-based line number for the given position."""
        raise VirtualMethodError()
    def lines_from_positions(self, positions):
        """Yield the associate 0-based line for each of a number of
        positions.  This can be much faster than multiple calls to
        `line_from_pos` for some accessors.
        """
        for pos in positions:
            yield self.line_from_pos(pos)
    def line_start_pos_from_pos(self, pos):
        """Return the position of the start of the line of the given pos."""
        raise VirtualMethodError()
    def pos_from_line_and_col(self, line, col):
        """Return the position of the given line and column."""
        raise VirtualMethodError()
    @property
    def text(self):
        """All buffer content (as a unicode string)."""
        raise VirtualMethodError()
    def text_range(self, start, end):
        raise VirtualMethodError()
    def length(self):
        """Return the length of the buffer.

        Note that whether this returns a *character* pos or a *byte* pos is
        left fuzzy so that SilverCity and SciMoz implementations can be
        efficient. All that is guaranteed is that the *_at_pos() methods
        work as expected.
        """
        raise VirtualMethodError()
    #def gen_pos_and_char_fwd(self, start_pos):
    #    """Generate (<pos>, <char>) tuples forward from the starting
    #    position until the end of the document.
    #    
    #    Note that whether <pos> is a *character* pos or a *byte* pos is
    #    left fuzzy so that SilverCity and SciMoz implementations can be
    #    efficient.
    #    """
    #    raise VirtualMethodError()
    def gen_tokens(self):
        """Generator for all styled tokens in the buffer.
        
        Currently this should yield token dict a la SilverCity's
        tokenize_by_style().
        """
        raise VirtualMethodError()
    def contiguous_style_range_from_pos(self, pos):
        """Returns a 2-tuple (start, end) giving the span of the sequence of
        characters with the style at position pos."""
        raise VirtualMethodError()


class SilverCityAccessor(Accessor):
    def __init__(self, lexer, content):
        self.lexer = lexer
        self.reset_content(content)

    def reset_content(self, content):
        """A backdoor specific to this accessor to allow the equivalent of
        updating the buffer/file/content.
        """
        if isinstance(content, unicode):
            content = content.encode("utf-8")
        self.content = content
        self.__tokens_cache = None
        self.__position_data_cache = None

    __tokens_cache = None
    @property
    def tokens(self):
        if self.__tokens_cache is None:
            self.__tokens_cache = self.lexer.tokenize_by_style(self.content)
        return self.__tokens_cache

    def char_at_pos(self, pos):
        return self.content[pos]

    def _token_at_pos(self, pos):
        #XXX Locality of reference should offer an optimization here.
        # Binary search for appropriate token.
        lower, upper = 0, len(self.tokens)  # [lower-limit, upper-limit)
        if upper == 1:
            return self.tokens[0]
        elif upper == 0:
            return {"style": 0, "start_index": 0, "end_index": 0} # blank document
        # This being a binary search, we should have a maximum of log2(upper)
        # iterations.  Enforce that in case we have an issue and hit an infinite
        # loop.
        for iter_count in range(int(math.ceil(math.log(upper, 2)) + 1)):
            idx = ((upper - lower) / 2) + lower
            if idx >= len(self.tokens):
                return self.tokens[-1]
            token = self.tokens[idx]
            #print "_token_at_pos %d: token idx=%d text[%d:%d]=%r"\
            #      % (pos, idx, token["start_index"], token["end_index"],
            #         token["text"])
            start, end = token["start_index"], token["end_index"]
            if pos < token["start_index"]:
                upper = idx
            elif pos > token["end_index"]:
                lower = idx + 1
            else:
                return token
        else:
            raise CodeIntelError("style_at_pos binary search sentinel hit: "
                                 "there is likely a logic problem here!")

    def style_at_pos(self, pos):
        return self._token_at_pos(pos)["style"]

    def line_and_col_at_pos(self, pos):
        line = self.line_from_pos(pos)
        byte_offset, char_offset = self.__position_data[line][:2]

        line_char_offset = char_offset
        assert isinstance(self.content, str), \
            "codeintel should be internally UTF-8"
        try:
            while byte_offset < pos:
                byte_offset += len(self.content[char_offset])
                char_offset += 1
        except IndexError:
            char_offset += 1 # EOF
        return line, char_offset - line_char_offset
    
    #PERF: If perf is important for this accessor then could do much
    #      better with smarter use of _token_at_pos() for these two.
    def gen_char_and_style_back(self, start, stop):
        assert -1 <= stop <= start, "stop: %r, start: %r" % (stop, start)
        for pos in range(start, stop, -1):
            yield (self.char_at_pos(pos), self.style_at_pos(pos))
    def gen_char_and_style(self, start, stop):
        assert 0 <= start <= stop, "start: %r, stop: %r" % (start, stop)
        for pos in range(start, stop):
            yield (self.char_at_pos(pos), self.style_at_pos(pos))

    def match_at_pos(self, pos, s):
        assert not isinstance(s, unicode), "codeintel should be internally utf8"
        if isinstance(s, unicode):
            s = s.encode("utf-8")
        return self.content[pos:pos+len(s)] == s

    __position_data_cache = None
    @property
    def __position_data(self):
        """A list holding the cache of line position data.  The index is the
        line number; the value is a four-tuple of (start pos in bytes,
        start pos in chars, line length in bytes, line length in chars).
        """
        if self.__position_data_cache is None:
            data = []
            offset = 0
            for match in re.finditer("\r\n|\r|\n", self.content):
                end = match.end()
                data.append((offset, end - offset))
                offset = end
            data.append((offset, len(self.content) - offset))
            self.__position_data_cache = data
        return self.__position_data_cache

    def line_from_pos(self, pos):
        r"""
            >>> sa = SilverCityAccessor(lexer,
            ...         #0         1           2         3
            ...         #01234567890 123456789 01234567890 12345
            ...         'import sys\nif True:\nprint "hi"\n# bye')
            >>> sa.line_from_pos(0)
            0
            >>> sa.line_from_pos(9)
            0
            >>> sa.line_from_pos(10)
            0
            >>> sa.line_from_pos(11)
            1
            >>> sa.line_from_pos(22)
            2
            >>> sa.line_from_pos(34)
            3
            >>> sa.line_from_pos(35)
            3
        """
        # Search for (byte_pos,) in the position data so we will always come
        # "before" the line we want (i.e. we have the index of the line itself)
        # the +1 is to make sure we get the line after (so we can subtract it)
        # this is because for a position not at line start, we get the next line
        # instead.
        return bisect.bisect_left(self.__position_data, (pos + 1,)) - 1

    def line_start_pos_from_pos(self, pos):
        return self.__position_data[self.line_from_pos(pos)][0]
    def pos_from_line_and_col(self, line, col):
        return self.__position_data[line][0] + col

    @property
    def text(self):
        return self.content
    def text_range(self, start, end):
        return self.content[start:end]
    def length(self):
        return len(self.content)
    def gen_tokens(self):
        for token in self.tokens:
            yield token
    def contiguous_style_range_from_pos(self, pos):
        token = self._token_at_pos(pos)
        return (token["start_index"], token["end_index"] + 1)


class SciMozAccessor(Accessor):
    def __init__(self, scimoz, silvercity_lexer):
        self.scimoz = WeakReference(scimoz)
        self.silvercity_lexer = silvercity_lexer
    def char_at_pos(self, pos):
        return self.scimoz().getWCharAt(pos)
    def style_at_pos(self, pos):
        return self.scimoz().getStyleAt(pos)
    def line_and_col_at_pos(self, pos):
        scimoz = self.scimoz()
        line = scimoz.lineFromPosition(pos)
        col = pos - scimoz.positionFromLine(line)
        return line, col

    # These two are *much* faster than repeatedly calling char_at_pos()
    # and style_at_pos().
    def gen_char_and_style_back(self, start, stop):
        if start > stop:
            # For scimoz.getStyledText(), it's (inclusive, exclusive)
            styled_text = self.scimoz().getStyledText(stop+1, start+1)
            for i in range(len(styled_text)-2, -2, -2):
                yield (styled_text[i], ord(styled_text[i+1]))
        elif start == stop:
            pass
        else:
            raise AssertionError("start (%r) < stop (%r)" % (start, stop))
    def gen_char_and_style(self, start, stop):
        if start < stop:
            # For scimoz.getStyledText(), it's (inclusive, exclusive)
            styled_text = self.scimoz().getStyledText(start, stop)
            for i in range(0, len(styled_text), 2):
                yield (styled_text[i], ord(styled_text[i+1]))
        elif start == stop:
            pass
        else:
            raise AssertionError("start (%r) > stop (%r)" % (start, stop))

    #XXX def match_at_pos(self, pos, s):...
    def line_from_pos(self, pos):
        return self.scimoz().lineFromPosition(pos)

    def lines_from_positions(self, positions):
        # Note: for a large enough set of positions it might be faster
        # to use the algorithm in SilverCityAccessor.
        scimoz = self.scimoz()
        for pos in positions:
            yield scimoz.lineFromPosition(pos)

    def line_start_pos_from_pos(self, pos):
        scimoz = self.scimoz()
        return scimoz.positionFromLine(scimoz.lineFromPosition(pos))
    def pos_from_line_and_col(self, line, col):
        return self.scimoz().positionFromLine(line) + col
    @property
    def text(self):
        return self.scimoz().text
    def text_range(self, start, end):
        return self.scimoz().getTextRange(start, end)
    def length(self):
        return self.scimoz().length
        #raise NotImplementedError(
        #    "Calculating the *character* length of a SciMoz buffer can "
        #    "be expensive. Are you sure you want to use this method? "
        #    "Try accessor.gen_pos_and_char_fwd() first.")
    def gen_tokens(self):
        if self.silvercity_lexer:
            #PERF: This is not a great solution but see bug 54217.
            acc = SilverCityAccessor(self.silvercity_lexer, self.text)
            for token in acc.gen_tokens():
                yield token
        else:
            # Silvercity lexer doesn't exist, use styles straight from SciMoz.
            scimoz = self.scimoz()
            styled_text = scimoz.getStyledText(0, scimoz.length)
            text = styled_text[::2]
            styles = styled_text[1::2]
            start_index = 0
            prev_style = -1
            last_i = len(styles) - 1
            for i in range(len(styles)):
                style = styles[i]
                if style != prev_style or i == last_i:
                    token_text = text[start_index:i]
                    if token_text:
                        token = {
                            'style': ord(prev_style),
                            'text': token_text,
                            'start_index': start_index,
                            'end_index': i-1,
                            'start_column': 0, # unset
                            'end_column': 0,   # unset
                            'start_line': 0,   # unset
                            'end_line': 0,     # unset
                        }
                        yield token
                    start_index = i
                    prev_style = style
    def contiguous_style_range_from_pos(self, pos):
        curr_style = self.style_at_pos(pos)
        i = pos - 1
        while i >= 0 and self.style_at_pos(i) == curr_style:
            i -= 1
        start_pos = i + 1
        
        last_pos = self.length()
        i = pos + 1
        while i < last_pos and self.style_at_pos(i) == curr_style:
            i += 1
        end_pos = i # Point one past the end
        return (start_pos, end_pos)

    @property
    def udl_family_chunk_ranges(self):
        """Generate a list of continguous UDL-family ranges.
        
        Generates 3-tuples:
            (<udl-family>, <start-byte-offset>, <end-byte-offset>)
        where
            <udl-family> is one of "M", "CSS", "CSL", "SSL", "TPL"
            <start-byte-offset> is inclusive
            <end-byte-offset> is exclusive (like a Python range)
        
        Note: For non-UDL languages this will return on chunk that is the
        whole document and <udl-family> will be None.
        """
        # LexUDL will set indicator 18 on the start char (or set of chars)
        # beginning a new UDL family section.
        scimoz = self.scimoz()

        # Note: value must match that in LexUDL.cxx and koILinter.idl.
        DECORATOR_UDL_FAMILY_TRANSITION = 18

        pos = 0
        length = scimoz.length
        while pos < length:
            start = scimoz.indicatorStart(DECORATOR_UDL_FAMILY_TRANSITION, pos)
            end = scimoz.indicatorEnd(DECORATOR_UDL_FAMILY_TRANSITION, start+1)
            if start == end == 0: # No indicators.
                yield (None, 0, length)
                break
            start = max(start-1, 0)
            #print "range: %d (%r) - %d (%r): %s" % (
            #    start, scimoz.getWCharAt(start),
            #    end, scimoz.getWCharAt(end-1),
            #    self._udl_family_from_style(scimoz.getStyleAt(pos)))
            #print util.indent(repr(scimoz.getTextRange(start, end)))
            yield (self._udl_family_from_style(scimoz.getStyleAt(pos)),
                   start, end)
            pos = end + 1
    
    _udl_family_from_start_style = {
       ScintillaConstants.SCE_UDL_M_DEFAULT: "M",
       ScintillaConstants.SCE_UDL_CSS_DEFAULT: "CSS",
       ScintillaConstants.SCE_UDL_CSL_DEFAULT: "CSL",
       ScintillaConstants.SCE_UDL_SSL_DEFAULT: "SSL",
       ScintillaConstants.SCE_UDL_TPL_DEFAULT: "TPL",
    }
    _udl_family_start_styles = list(sorted(_udl_family_from_start_style.keys()))
    @classmethod
    def _udl_family_from_style(cls, style):
        """Determine which UDL family this style is in. Returns one
        of M, CSS, CSL, SSL or TPL.
        """
        idx = bisect.bisect_right(cls._udl_family_start_styles, style)
        start_style = cls._udl_family_start_styles[idx-1]
        fam = cls._udl_family_from_start_style[start_style]
        return fam

class AccessorCache:
    """Utility class used to cache buffer styling information"""

    def __init__(self, accessor, position, fetchsize=20, debug=False):
        """Document accessor cache contructor. Will cache fetchsize style info
        pieces starting from position - 1.
        
        @param accessor {Accessor} a form of document accessor
        @param position {int} where in the document to start caching from (exclusive)
        @param fetchsize {int} how much cache is stored/retrived at a time
        """
        self._accessor = accessor
        self._cachefetchsize = fetchsize
        self._debug = debug
        #self._debug = True
        self._reset(position)

    # Private
    def _reset(self, position):
        self._pos = position
        self._ch = None
        self._style = None
        # cachePos is used to store where self._pos is inside the _cache
        self._cachePos = 0
        self._chCache = []
        self._styleCache = []
        # cacheXXXBufPos is used to store where cache is relative to the buffer
        # _cacheFirstBufPos is inclusive
        self._cacheFirstBufPos = position
        # _cacheLastBufPos is exclusive
        self._cacheLastBufPos  = position

    def _initializeCacheBackwards(self):
        self._cachePos -= 1
        self._extendCacheBackwards()

    def _extendCacheBackwards(self, byAmount=None):
        if self._cacheFirstBufPos > 0:
            if byAmount is None:
                byAmount = self._cachefetchsize
            # Generate another n tuples (pos, char, style)
            start = max(0, (self._cacheFirstBufPos - byAmount))
            # Add more to the start of the cache
            extendCount = (self._cacheFirstBufPos - start)
            ch_list = []
            style_list = []
            for ch, style in self._accessor.gen_char_and_style(start, self._cacheFirstBufPos):
                ch_list.append(ch)
                style_list.append(style)
            self._chCache = ch_list + self._chCache
            self._styleCache = style_list + self._styleCache
            self._cachePos += extendCount
            self._cacheFirstBufPos = start
            if self._debug:
                print("Extended cache by %d, _cachePos: %d, len now: %d" % (
                    extendCount, self._cachePos, len(self._chCache)))
                print("Ch cache now: %r" % (self._chCache))
        else:
            raise IndexError("No buffer left to examine")

    def _initializeCacheForwards(self):
        self._cachePos -= 1
        self._extendCacheForwards()

    def _extendCacheForwards(self, byAmount=None):
        buf_length = self._accessor.length()
        if self._cacheLastBufPos < buf_length:
            if byAmount is None:
                byAmount = self._cachefetchsize
            # Generate another n tuples (pos, char, style)
            end = min(buf_length, (self._cacheLastBufPos + byAmount))
            # Add more to the end of the cache
            extendCount = end - self._cacheLastBufPos
            for ch, style in self._accessor.gen_char_and_style(self._cacheLastBufPos, end):
                self._chCache.append(ch)
                self._styleCache.append(style)
            self._cacheLastBufPos = end
            if self._debug:
                print("Extended cache by %d, _cachePos: %d, len now: %d" % (
                    extendCount, self._cachePos, len(self._chCache)))
                print("Ch cache now: %r" % (self._chCache))
        else:
            raise IndexError("No buffer left to examine")

    # Public
    def dump(self, limit=20):
        if len(self._chCache) > 0:
            print("  pos: %r, ch: %r, style: %r, cachePos: %r, cache len: %d\n  cache: %r" % (self._cachePos + self._cacheFirstBufPos,
                                                             self._chCache[self._cachePos],
                                                             self._styleCache[self._cachePos],
                                                             self._cachePos,
                                                             len(self._chCache),
                                                             self._chCache))
        else:
            print("New cache: %r" % (self._chCache[-limit:]))

    def setCacheFetchSize(self, size):
        self._cachefetchsize = size

    def resetToPosition(self, position):
        if self._debug:
            print("resetToPosition: %d" % (position))
            print("self._cacheFirstBufPos: %d" % (self._cacheFirstBufPos))
            print("self._cacheLastBufPos: %d" % (self._cacheLastBufPos))
        if position >= self._cacheLastBufPos:
            if position >= self._cacheLastBufPos + self._cachefetchsize:
                # Clear everything
                self._reset(position)
                return
            else:
                # Just extend forwards
                if self._debug:
                    print("resetToPosition: extending cache forwards")
                self._extendCacheForwards()
        elif position < self._cacheFirstBufPos:
            if position < self._cacheFirstBufPos - self._cachefetchsize:
                # Clear everything
                self._reset(position)
                return
            else:
                # Just extend back
                if self._debug:
                    print("resetToPosition: extending cache backwards")
                self._extendCacheBackwards()
        else:
            # It's in the current cache area, we keep that then
            pass
        self._cachePos = position - self._cacheFirstBufPos
        self._ch = self._chCache[self._cachePos]
        self._style = self._styleCache[self._cachePos]
        self._pos = position
        if self._debug:
            print("self._cachePos: %d, cacheLen: %d" % (self._cachePos, len(self._chCache)))
            print("resetToPosition: p: %r, ch: %r, st: %r" % (self._pos, self._ch, self._style))

    #def pushBack(self, numPushed=1):
    #    """Push back the items that were recetly popped off.
    #    @returns {int} Number of pushed items
    #    """
    #    pushItems = self._popped[-numPushed:]
    #    pushItems.reverse()
    #    self._cache += pushItems
    #    if len(self._popped) > 0:
    #        self._currentTuple = self._popped[-1]
    #    else:
    #        self._currentTuple = (self._currentTuple[0] + numPushed, None, None)
    #    return len(pushItems)

    def getCurrentPosCharStyle(self):
        """Get the current buffer position information.
        @returns {tuple} with values (pos, char, style)
        """
        return (self._pos, self._ch, self._style)

    def getPrevPosCharStyle(self, ignore_styles=None, max_look_back=100):
        """Get the previous buffer position information.
        @param ignore_styles {tuple}
        @returns {tuple} with values (pos, char, style), these values will
        all be None if it exceeds the max_look_back.
        @raises IndexError can be raised when nothing left to consume.
        """
        count = 0
        while count < max_look_back:
            count += 1
            self._cachePos -= 1
            if self._cachePos < 0:
                self._extendCacheBackwards()
            self._style = self._styleCache[self._cachePos]
            if ignore_styles is None or self._style not in ignore_styles:
                self._ch = self._chCache[self._cachePos]
                break
        else:
            # Went too far without finding what looking for
            return (None, None, None)
        self._pos = self._cachePos + self._cacheFirstBufPos
        if self._debug:
            print("getPrevPosCharStyle:: pos:%d ch:%r style:%d" % (self._pos, self._ch, self._style))
        return (self._pos, self._ch, self._style)

    def peekPrevPosCharStyle(self, ignore_styles=None, max_look_back=100):
        """Same as getPrevPosCharStyle, but does not move the buffer position.
        @param ignore_styles {tuple}
        @returns {tuple} with values (pos, char, style), these values will
        all be None if it exceeds the max_look_back.
        @raises IndexError can be raised when nothing left to consume.
        """
        # Store the old values.
        old_pos = self._pos
        old_ch = self._ch
        old_style = self._style
        old_cachePos = self._cachePos
        old_cacheFirstBufPos = self._cacheFirstBufPos
        try:
            pos, ch, style = self.getPrevPosCharStyle(ignore_styles, max_look_back)
        finally:
            # Restore old values.
            self._pos = old_pos
            self._ch = old_ch
            self._style = old_style
            # The cache may have gotten extended (which is fine), but in that
            # case the old_cachePos is no longer correct, so update it.
            cache_extended_by = old_cacheFirstBufPos - self._cacheFirstBufPos
            self._cachePos = old_cachePos + cache_extended_by
        if self._debug:
            print("peekPrevPosCharStyle:: pos:%d ch:%r style:%d" % (pos, ch, style))
        return (pos, ch, style)

    def getPrecedingPosCharStyle(self, current_style=None, ignore_styles=None,
                                 max_look_back=200):
        """Go back and get the preceding style.
        @returns {tuple} with values (pos, char, style)
        Returns None for both char and style, when out of characters to look
        at and there is still no previous style found.
        """
        if current_style is None:
            if not self._styleCache:
                self._initializeCacheBackwards()
            current_style = self._styleCache[self._cachePos]
        try:
            new_ignore_styles = [current_style]
            if ignore_styles is not None:
                new_ignore_styles += list(ignore_styles)
            return self.getPrevPosCharStyle(new_ignore_styles, max_look_back)
        except IndexError:
            pass
        # Did not find the necessary style
        return None, None, None

    def getTextBackWithStyle(self, current_style=None, ignore_styles=None,
                             max_text_len=200):
        """Go back and get the preceding text, which is of a different style.
        @returns {tuple} with values (pos, text), pos is position of first text char
        """
        old_p = self._pos
        new_p, c, style = self.getPrecedingPosCharStyle(current_style,
                                                        ignore_styles,
                                                        max_look_back=max_text_len)
        #print "Return %d:%d" % (new_p, old_p+1)
        if style is None:   # Ran out of text to look at
            new_p = max(0, old_p - max_text_len)
            return new_p, self.text_range(new_p, old_p+1)
        else:
            # We don't eat the new styling info
            self._cachePos += 1
            return new_p+1, self.text_range(new_p+1, old_p+1)

    def getNextPosCharStyle(self, ignore_styles=None, max_look_ahead=100):
        """Get the next buffer position information.
        @param ignore_styles {tuple}
        @returns {tuple} with values (pos, char, style), these values will
        all be None if it exceeds the max_look_ahead.
        @raises IndexError can be raised when nothing left to consume.
        """
        max_pos = self._cachePos + max_look_ahead
        while self._cachePos < max_pos:
            self._cachePos += 1
            if self._cachePos >= len(self._chCache):
                self._extendCacheForwards()
            self._style = self._styleCache[self._cachePos]
            if ignore_styles is None or self._style not in ignore_styles:
                self._ch = self._chCache[self._cachePos]
                break
        else:
            # Went too far without finding what looking for
            return (None, None, None)
        self._pos = self._cachePos + self._cacheFirstBufPos
        if self._debug:
            print("getNextPosCharStyle:: pos:%d ch:%r style:%d" % (self._pos, self._ch, self._style))
        return (self._pos, self._ch, self._style)

    def getSucceedingPosCharStyle(self, current_style=None, ignore_styles=None,
                                  max_look_ahead=200):
        """Go forward and get the next different style.
        @returns {tuple} with values (pos, char, style)
        Returns None for both char and style, when out of characters to look
        at and there is still no previous style found.
        """
        if current_style is None:
            if not self._styleCache:
                self._initializeCacheForwards()
            current_style = self._styleCache[self._cachePos]
        try:
            new_ignore_styles = [current_style]
            if ignore_styles is not None:
                new_ignore_styles += list(ignore_styles)
            return self.getNextPosCharStyle(new_ignore_styles, max_look_ahead)
        except IndexError:
            pass
        # Did not find the necessary style
        return None, None, None

    def getTextForwardWithStyle(self, current_style=None, ignore_styles=None,
                                max_text_len=200):
        """Go forward and get the succeeding text, which is of a different style.
        @returns {tuple} with values (pos, text), pos is position of last text char.
        """
        old_p = self._pos
        new_p, c, style = self.getSucceedingPosCharStyle(current_style,
                                                         ignore_styles,
                                                         max_look_ahead=max_text_len)
        if style is None:   # Ran out of text to look at
            new_p = min(self._accessor.length(), old_p + max_text_len)
            return new_p, self.text_range(old_p, new_p)
        else:
            # We don't eat the new styling info
            self._cachePos -= 1
            return new_p-1, self.text_range(old_p, new_p)

    def text_range(self, start, end):
        """Return text in range buf[start:end]
        
        Note: Start position is inclusive, end position is exclusive.
        """
        if start >= self._cacheFirstBufPos and end <= self._cacheLastBufPos:
            cstart = start - self._cacheFirstBufPos
            cend = end - self._cacheFirstBufPos
            if self._debug:
                print("text_range:: cstart: %d, cend: %d" % (cstart, cend))
                print("text_range:: start: %d, end %d" % (start, end))
                print("text_range:: _cacheFirstBufPos: %d, _cacheLastBufPos: %d" % (self._cacheFirstBufPos, self._cacheLastBufPos))
            # It's all in the cache
            return "".join(self._chCache[cstart:cend])
        if self._debug:
            print("text_range:: using parent text_range: %r - %r" % (start, end))
        return self._accessor.text_range(start, end)
