#!/usr/bin/env python
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
#

"""sciutils - shared ISciMoz-based editing functionality

Useful stuff:

    getStyledPythonLogicalLine
        Get the logical Python line containing the given position.

    getPythonLogicalLineStartPosition
        Get the start position of the Python logical line containg the
        given position.

    SciMozTestCase & runSciMozTests
        PyUnit helpers for working with the test_scimoz system in Komodo (a
        system for running test suites that required a working SciMoz plugin).

    genLinesBwd, genContinuedLinesBwd & genPythonLogicalLinesBwd
    genLinesFwd, genContinuedLinesFwd & genPythonLogicalLinesFwd
        Generators for getting styled scintilla line data forwards and
        backwards from a starting point and with details like line
        continuations and line breaks within statements taken care of for you.

    XXX and others (i.e. this is out of date)
"""

import os
import sys
import logging
import unittest
import tokenize
import token
import re
import pprint
import textwrap

from xpcom import components, ServerException



#---- exceptions

class SciUtilsError(Exception):
    pass


#---- global data

log = logging.getLogger("sciutils")



#---- internal routines and classes

def _printBanner(title, style="=", width=65):
    lineLen = width - len(title) - 2  # -2 for spaces on either side
    leftLen = max(4, lineLen / 2)
    rightLen = lineLen - leftLen
    print "%s %s %s" % (style*leftLen, title, style*rightLen)

def _printBufferContext(offset, styledText, position):
    index = position - offset # 'index' is into styledText, 'position' into whole buffer
    text = ''.join([styledText[i] for i in range(0, len(styledText), 2)])
    lines = text.splitlines(1)
    start = 0
    end = None
    for line in lines:
        end = start + len(line)
        if start <= index < end:
            column = index - start
            line = line[:column] + "<|>" + line[column:]
        line = line.replace('\n', "<LF>").replace('\r', "<CR>")
        span = "%d-%d" % (start+offset, end+offset)
        print "  %7s: %s" % (span, line.decode("utf-8"))
        start = end
    print "-"*65

def _getPositionContext(scimoz, position, context=5):
    # This function isn't used anywhere in the Komodo source code,
    # but could be used by python macros, and needs to be made
    # unicode-safe
    start = position
    delta = context
    while start > 0 and delta > 0:
        start = scimoz.positionBefore(start)
        delta -= 1
    lim = scimoz.textLength
    end = position
    delta = context
    while end < lim and delta > 0:
        end = scimoz.positionAfter(end)
        delta -= 1
    context = scimoz.getTextRange(start, end)
    if start != 0:
        context = "..."+context
    if end != scimoz.textLength:
        context = context+"..."
    context = context.replace('\n', "<LF>").replace('\r', "<CR>")
    return context

def _data2text(data):
    text = ''.join([data[i] for i in range(0, len(data), 2)])
    text = text.replace('\n', "<LF>").replace('\r', "<CR>")
    return text
    
def _getPosBeforeEOL(offset, styledText, position):
    """Return the position before the EOL preceding the given pos."""
    i = (position - offset) * 2
    if i <= 0:
        pass
    if styledText[i-2] == '\n':
        i -= 2
        if i > 0 and styledText[i-2] == '\r':
            i -= 2
    elif styledText[i-2] == '\r':
        i -= 2
    return i/2 + offset

def _isident(char):
    return "a" <= char <= "z" or "A" <= char <= "Z" or char == "_"

def _isdigit(char):
    return "0" <= char <= "9"



#---- public module interface

class SciMozTestCase(unittest.TestCase):
    """This is a unittest.TestCase subclass to use for test suites requiring
    scimoz.
    
    Komodo now has a simple system for running PyUnit test suites that
    require a working SciMoz plugin. To run these test suites you go to:
        Test | SciMoz Tests
    if a Komodo dev build. Here is how you add a test suite to the system:

    1. Write a SciMozTestCase subclass. This is your test suite. See
        <http://www.python.org/doc/current/lib/module-unittest.html>
       for more info. Here is some boilerplat:

        import sciutils
        class MyTestCase(sciutils.SciMozTestCase):
            def test_foo(self):
                self._setupSciMoz("foo.bar.<|>", "Python")
                #... test code using self.scimoz

    2. Add the following method to your PyXPCOM component's IDL:

        void test_scimoz(in ISciMoz scimoz);

    3. Implement that method. It must (1) pass the 'scimoz' instance to
       the TestCase class and (2) create and run the test suite. Here is
       some boilerplate:

        def test_scimoz(self, scimoz):
            testCases = [MyTestCase1, MyTestCase2]
            sciutils.runSciMozTests(testCases, scimoz)

        See, for example, KoPythonCodeIntelCompletionLanguageService's
        test_scimoz() in koPythonLanguage.unprocessed.py.

    4. Hook up your test suite in
        src/chrome/komodo/content/test/test_scimoz.{xul|js}
       by adding a <menuitem> to the "test-names" <menulist> and adding a
       corresponding entry to the RunTest() function.

    5. (Optional) Setup your test so that you can make changes and re-run
       without having to re-start Komodo. To do this you must move the
       working code and the MyTestCase class(es) out to a separate Python
       file from your PyXPCOM component. Then you change your test_scimoz()
       to this:

        class KoFoo:
            _com_interfaces_ = [components.interfaces.koIFoo]
            ...
            def test_scimoz(self, scimoz):
                reload(foo)
                testCases = [foo.MyTestCase]
                sciutils.runSciMozTests(testCases, scimoz)
        
        See test_scimoz() in koISciUtils.py for an example.

    6. Look through some of the methods provide by this class that may
       be useful for writing your unit tests.
    """
    scimoz = None

    _scheme = None
    def _getScheme(self):
        if not self._scheme:
            schemeSvc = components.classes["@activestate.com/koScintillaSchemeService;1"].getService()
            prefs = components.classes["@activestate.com/koPrefService;1"]\
                    .getService(components.interfaces.koIPrefService).prefs
            schemeName = prefs.getStringPref("editor-scheme")
            self._scheme = schemeSvc.getScheme(schemeName)
        return self._scheme

    #XXX Better names for _parseBuffer and _encodeBuffer.
    def _parseBuffer(self, buffer):
        """Return the text and current position content for the given
        marked-up buffer.
        
        Markup:
            "<|>" indicated the current position
        """
        #XXX Might want to add markup for the "anchor".
        currentPos = buffer.find("<|>")
        if currentPos == -1:
            currentPos = len(buffer)
        text = buffer[:currentPos] + buffer[currentPos+3:]
        return text, currentPos

    def _encodeBuffer(self):
        """Return a string encoding the current SciMoz buffer contents
        and some state. Markup is the same as _parseBuffer().
        """
        #XXX Unicode issues here?
        text = self.scimoz.text
        currentPos = self.scimoz.currentPos
        text = text[:currentPos] + "<|>" + text[currentPos:]
        return text

    def _setupSciMoz(self, buffer, language):
        #XXX Probably shouldn't have a default language: force
        #    explicitness.
        text, currentPos = self._parseBuffer(buffer)

        # Change language and scheme.
        scheme = self._getScheme()
        scheme.applyScheme(self.scimoz, language, "default", 0)
        
        # Setup scintilla.
        self.scimoz.text = text
        self.scimoz.currentPos = self.scimoz.anchor = currentPos
        self.scimoz.colourise(0, -1)

    def assertAutocommentResultsIn(self, lang, buffer, expected):
        """Assert that the autocomment action for the given buffer and
        koILanguage instance has the given result.

            "lang" is a koILangage instance
            "buffer" is an encoded scintilla buffer -- where "encoded"
                means special markers for the current position and
                anchor are interpreted. See
                sciutils.py::SciMozTestCase._parseBuffer() for details.
            "expected" is the expected result buffer (encoded as well).
        """
        self._setupSciMoz(buffer, lang.name)
        self.lang.get_commenter().comment(self.scimoz)
        got = self._encodeBuffer()
        self.assertEqual(got, expected, textwrap.dedent("""
            Unexpected result auto-commenting '%s' buffer. Expected:
                %r
            Got:
                %r
            """ % (lang.name, expected, got)))

    def assertAutouncommentResultsIn(self, lang, buffer, expected):
        """Assert that the autocomment action for the given buffer and
        koILanguage instance has the given result.

            "lang" is a koILangage instance
            "buffer" is an encoded scintilla buffer -- where "encoded"
                means special markers for the current position and
                anchor are interpreted. See
                sciutils.py::SciMozTestCase._parseBuffer() for details.
            "expected" is the expected result buffer (encoded as well).
        """
        self._setupSciMoz(buffer, lang.name)
        self.lang.get_commenter().uncomment(self.scimoz)
        got = self._encodeBuffer()
        self.assertEqual(got, expected, textwrap.dedent("""
            Unexpected result auto-uncommenting '%s' buffer. Expected:
                %r
            Got:
                %r
            """ % (lang.name, expected, got)))


def runSciMozTests(testCases, scimoz):
    # Setup test cases. (unittest.py sucks: this is the only way to
    # get info to the tests)
    for tc in testCases:
        tc.scimoz = scimoz

    # unittest boilerplate mojo
    suite = unittest.TestSuite([unittest.makeSuite(tc)
                                for tc in testCases])
    runner = unittest.TextTestRunner(sys.stdout, verbosity=2)
    result = runner.run(suite)


def genLinesBwd(offset, styledText, position):
    r"""Generate styled lines backwards from the given position.
    
        "offset" is the position offset from the start of the source SciMoz
            buffer at which "styledText" begins. I.e. the whole buffer
            is not necessarily passed in.
        "styledText" is the styled text from which to extract.
        "position" is the position (NOT offset) from which to begin pulling
            out lines.
    
    Yields 2-tuples of the following form:
        (<scimoz position at start of line>,
         <line/style data of the line>)
    """
    DEBUG = 0
    if DEBUG:
        print
        _printBanner("genLinesBwd(offset=%d, styledText, position=%d)"\
                     % (offset, position))
        _printBufferContext(offset, styledText, position)
    
    index = position - offset
    EOLCHARS = tuple("\r\n")
    
    # The first line is slightly special in that there is no EOL to scan
    # first. (If "position" is at the start of a line, then we return the
    # empty string as the first line.)
    i = index*2 - 2
    end = index*2
    while i >= 0 and styledText[i] not in EOLCHARS:
        i -= 2
    start = i + 2
    line = styledText[start:end]
    if DEBUG: print "yield:%d-%d:%s" % (start/2+offset, end/2+offset, _data2text(line))
    yield (start/2+offset, line)

    while i >= 0:
        end = start
        # Scan over the EOL.
        if styledText[i] == '\n' and i-2 > 0 and styledText[i-2] == '\r':
            i -= 4
        else:
            i -= 2
        # Scan to start of line.
        while i >= 0 and styledText[i] not in EOLCHARS:
            i -= 2
        start = i + 2
        line = styledText[start:end] 
        if DEBUG: print "yield:%d-%d:%s" % (start/2+offset, end/2+offset, _data2text(line))
        yield (start/2+offset, line)

    if DEBUG: _printBanner("done")


def genLinesFwd(offset, styledText, position):
    r"""Generate styled lines forwards from the given position.
    
        "offset" is the position offset from the start of the source SciMoz
            buffer at which "styledText" begins. I.e. the whole buffer
            is not necessarily passed in.
        "styledText" is the styled text from which to extract.
        "position" is the position (NOT offset) from which to begin pulling
            out lines.
    
    Yields 2-tuples of the following form:
        (<scimoz position at start of line>,
         <line/style data of the line>)
    """
    DEBUG = 0
    if DEBUG:
        print
        _printBanner("genLinesFwd(offset=%d, styledText, position=%d)"\
                     % (offset, position))
        _printBufferContext(offset, styledText, position)
    
    index = position - offset
    EOLCHARS = tuple("\r\n")
    i = index*2
    lenStyledText = len(styledText)
    while i < lenStyledText:
        start = i
        
        # Scan up to EOL.
        while i < lenStyledText and styledText[i] not in EOLCHARS:
            i += 2

        # Scan over the EOL.
        if i < lenStyledText:
            if (styledText[i] == '\r' and
               i+2 < lenStyledText and styledText[i+2] == '\n'):
                i += 4
            else:
                i += 2
        line = styledText[start:i] 
        if DEBUG: print "yield:%d-%d:%s" % (start/2+offset, i/2+offset, _data2text(line))
        yield (i/2+offset, line)

    if DEBUG: _printBanner("done")


def genContinuedLinesBwd(offset, styledText, position, stylesToIgnore,
                         styleMask):
    r"""Generate styled "continued" lines backwards from the given position.
    
        "offset" is the position offset from the start of the source SciMoz
            buffer at which "styledText" begins. I.e. the whole buffer
            is not necessarily passed in.
        "styledText" is the styled text from which to extract.
        "position" is the position (NOT offset) from which to begin pulling
            out lines.
        "stylesToIgnore" is a list of SCE_* style numbers for the current
            language that should id which block structure characters should be
            ignored. Typically this is the list of comment and string styles.
        "styleMask" is a mask to apply to style bytes from styledText
            before comparison with stylesToIgnore
    
    Yields 2-tuples of the following form:
        (<scimoz position at start of line>,
         <line/style data of the line>)
    
    It groups together physical lines contined with a trailing '\' into
    one "continued line". The continuation character is replaced with a
    space.
    """
    DEBUG = 0
    if DEBUG:
        print
        _printBanner("genContinuedLinesBwd(offset=%d, styledText, "
                     "position=%d)" % (offset, position))
        _printBufferContext(offset, styledText, position)

    EOLCHARS = tuple("\r\n")
    cdata = None  # styled text data for the grouped "continued" line
    currPos = currData = None
    for precPos, precData in genLinesBwd(offset, styledText, position):
        if DEBUG:
            print "preceding line:%d-%d:%s"\
                  % (precPos, precPos+len(precData)/2, _data2text(precData))

        if currData is None: # first time through, load curr{Data|Pos}
            currData = precData
            currPos = precPos
            continue
        if DEBUG:
            print "current line:%d-%d:%s"\
                  % (currPos, currPos+len(currData)/2, _data2text(currData))
        
        # If there is a continuation char on the preceding line then
        # prepend that line to the current one.
        contCharIndex = len(precData) - 2
        while contCharIndex >= 0 and precData[contCharIndex] in EOLCHARS:
            contCharIndex -= 2
        numBackslashes = 0
        for i in range(contCharIndex, -2, -2):
            if precData[i] == '\\':
                numBackslashes += 1
            else:
                break
        contCharStyle = ord(precData[contCharIndex+1]) & styleMask
        if numBackslashes % 2 and contCharStyle not in stylesToIgnore:
            if DEBUG:
                print "preceding line has continuation char"
            precData = precData[:contCharIndex] + ' \x00' + precData[contCharIndex+2:]
            currData = precData + currData
            currPos = precPos
            continue
        
        # Otherwise, just yield the current line.
        if DEBUG:
            print "yield:%d-%d:%s"\
                  % (currPos, currPos+len(currData)/2, _data2text(currData))
        yield (currPos, currData)
        currData = precData
        currPos = precPos

    # Yield the last line.
    if currData:
        if DEBUG:
            print "yield:%d-%d:%s"\
                  % (currPos, currPos+len(currData)/2, _data2text(currData))
        yield (currPos, currData)

    if DEBUG: _printBanner("done")


def genContinuedLinesFwd(offset, styledText, position, stylesToIgnore,
                         styleMask):
    r"""Generate styled "continued" lines forwards from the given position.
    
        "offset" is the position offset from the start of the source SciMoz
            buffer at which "styledText" begins. I.e. the whole buffer
            is not necessarily passed in.
        "styledText" is the styled text from which to extract.
        "position" is the position (NOT offset) from which to begin pulling
            out lines.
        "stylesToIgnore" is a list of SCE_* style numbers for the current
            language that should id which block structure characters should be
            ignored. Typically this is the list of comment and string styles.
        "styleMask" is a mask to apply to style bytes from styledText
            before comparison with stylesToIgnore
    
    Yields 2-tuples of the following form:
        (<scimoz position at start of line>,
         <line/style data of the line>)
    
    It groups together physical lines contined with a trailing '\' into
    one "continued line". The continuation character is replaced with a
    space.
    """
    DEBUG = 0
    if DEBUG:
        print
        _printBanner("genContinuedLinesFwd(offset=%d, styledText, "
                     "position=%d)" % (offset, position))
        _printBufferContext(offset, styledText, position)

    EOLCHARS = tuple("\r\n")
    cdata = None  # styled text data for the grouped "continued" line
    currPos = currData = None
    for nextPos, nextData in genLinesFwd(offset, styledText, position):
        if currData is None: # first time through, load curr{Data|Pos}
            currData = nextData
            currPos = nextPos
            continue
        if DEBUG:
            print "current line:%d-%d:%s"\
                  % (currPos-len(currData)/2, currPos, _data2text(currData))
            print "next line:%d-%d:%s"\
                  % (nextPos-len(nextData)/2, nextPos, _data2text(nextData))
        
        # If there is a continuation char on the current line then append
        # the next line to the current one.
        contCharIndex = len(currData) - 2
        while contCharIndex >= 0 and currData[contCharIndex] in EOLCHARS:
            contCharIndex -= 2
        numBackslashes = 0
        for i in range(contCharIndex, -2, -2):
            if currData[i] == '\\':
                numBackslashes += 1
            else:
                break
        contCharStyle = ord(currData[contCharIndex+1]) & styleMask
        if numBackslashes % 2 and contCharStyle not in stylesToIgnore:
            if DEBUG:
                print "current line has continuation char"
            currData = currData[:contCharIndex] + ' \x00' + currData[contCharIndex+2:]
            currData += nextData
            currPos = nextPos
            continue
        
        # Otherwise, just yield the current line.
        if DEBUG:
            print "yield:%d-%d:%s"\
                  % (currPos-len(currData)/2, currPos, _data2text(currData))
        yield (currPos, currData)
        currData = nextData
        currPos = nextPos

    # Yield the last line.
    if currData:
        if DEBUG:
            print "yield:%d-%d:%s"\
                  % (currPos, currPos+len(currData)/2, _data2text(currData))
        yield (currPos, currData)

    if DEBUG: _printBanner("done")


def genPythonLogicalLinesBwd(offset, styledText, position, stylesToIgnore,
                             styleMask, DEBUG=None):
    r"""Generate styled Python logical lines backwards from the given position.
    
        "offset" is the position offset from the start of the source SciMoz
            buffer at which "styledText" begins. I.e. the whole buffer
            is not necessarily passed in.
        "styledText" is the styled text from which to extract.
        "position" is the position (NOT offset) from which to begin pulling
            out lines.
        "stylesToIgnore" is a list of SCE_* style numbers for the current
            language that should id which block structure characters should be
            ignored. Typically this is the list of comment and string styles.
        "styleMask" is a mask to apply to style bytes from styledText
            before comparison with stylesToIgnore
    
    Yields 2-tuples of the following form:
        (<scimoz position at start of line>,
         <line/style data of the line>)
    
    It groups together physical lines contined with explicit or implicit
    line joining rules similar to what is described here:
        http://www.python.org/doc/current/ref/logical.html
    """
    if DEBUG is None: DEBUG = 0
    if DEBUG:
        print
        _printBanner("genPythonLogicalLinesBwd(offset=%d, styledText, "
                     "position=%d)" % (offset, position))
        _printBufferContext(offset, styledText, position)

    BLOCKS = { # map block close char to block open char
        ')': '(',
        ']': '[',
        '}': '{',
    }
    STATE_INBLOCK, STATE_OUTOFBLOCK = range(2)
    state = STATE_OUTOFBLOCK
    stack = [] # stack of blocks: (<block close char>, <style>)
    ldata = None  # styled text data for the grouped "logical" line
    for pos, data in genContinuedLinesBwd(offset, styledText, position,
                                           stylesToIgnore, styleMask):
        if DEBUG:
            print "continued line:%d-%d:%s"\
                  % (pos, pos+len(data)/2, _data2text(data))
            
        if ldata is None:
            ldata = data
        else:
            ldata = data + ldata
        
        i = len(data) - 2
        while i >= 0:
            ch = data[i]
            style = ord(data[i+1]) & styleMask
            if state == STATE_OUTOFBLOCK:
                if ch in BLOCKS and not style in stylesToIgnore:
                    stack.append( (ch, style, BLOCKS[ch]) )
                    state = STATE_INBLOCK
            elif state == STATE_INBLOCK:
                if ch in BLOCKS and not style in stylesToIgnore:
                    stack.append( (ch, style, BLOCKS[ch]) )
                elif ch == stack[-1][2] and style == stack[-1][1]:
                    stack.pop()
                    if not stack:
                        state = STATE_OUTOFBLOCK
            i -= 2
        
        if state == STATE_OUTOFBLOCK:
            if DEBUG:
                print "yield:%d-%d:%s"\
                      % (pos, pos+len(ldata)/2, _data2text(ldata))
            yield (pos, ldata)
            ldata = None

    if ldata: # if a block char was not closed then just dump out what remains
        if DEBUG:
            print "yield:%d-%d:%s" % (pos, pos+len(ldata)/2, _data2text(ldata))
        yield (pos, ldata)
        ldata = None

    if DEBUG: _printBanner("done")


def genPythonLogicalLinesFwd(offset, styledText, position, stylesToIgnore,
                             styleMask, DEBUG=None):
    r"""Generate styled Python logical lines forwards from the given position.
    
        "offset" is the position offset from the start of the source SciMoz
            buffer at which "styledText" begins. I.e. the whole buffer
            is not necessarily passed in.
        "styledText" is the styled text from which to extract.
        "position" is the position (NOT offset) from which to begin pulling
            out lines.
        "stylesToIgnore" is a list of SCE_* style numbers for the current
            language that should id which block structure characters should be
            ignored. Typically this is the list of comment and string styles.
        "styleMask" is a mask to apply to style bytes from styledText
            before comparison with stylesToIgnore
    
    Yields 2-tuples of the following form:
        (<scimoz position at start of line>,
         <line/style data of the line>)
    
    It groups together physical lines contined with explicit or implicit
    line joining rules similar to what is described here:
        http://www.python.org/doc/current/ref/logical.html
    """
    if DEBUG is None: DEBUG = 0
    if DEBUG:
        print
        _printBanner("genPythonLogicalLinesFwd(offset=%d, styledText, "
                     "position=%d)" % (offset, position))
        _printBufferContext(offset, styledText, position)

    BLOCKS = { # map block open char to block close char
        '(': ')',
        '[': ']',
        '{': '}',
    }
    STATE_INBLOCK, STATE_OUTOFBLOCK = range(2)
    state = STATE_OUTOFBLOCK
    stack = [] # stack of blocks: (<block close char>, <style>)
    lpos = ldata = None  # styled text data for the grouped "logical" line
    for pos, data in genContinuedLinesFwd(offset, styledText, position,
                                           stylesToIgnore, styleMask):
        if DEBUG:
            print "continued line:%d-%d:%s"\
                  % (pos, pos+len(data)/2, _data2text(data))
            
        if ldata is None:
            ldata = data
            lpos = pos
        else:
            ldata += data
            lpos = pos
        
        i = 0
        while i < len(data):
            ch = data[i]
            style = ord(data[i+1]) & styleMask
            if state == STATE_OUTOFBLOCK:
                if ch in BLOCKS and not style in stylesToIgnore:
                    stack.append( (ch, style, BLOCKS[ch]) )
                    state = STATE_INBLOCK
            elif state == STATE_INBLOCK:
                if ch in BLOCKS and not style in stylesToIgnore:
                    stack.append( (ch, style, BLOCKS[ch]) )
                elif ch == stack[-1][2] and style == stack[-1][1]:
                    stack.pop()
                    if not stack:
                        state = STATE_OUTOFBLOCK
            i += 2
        
        if state == STATE_OUTOFBLOCK:
            if DEBUG:
                print "yield:%d-%d:%s"\
                      % (lpos-len(ldata)/2, lpos, _data2text(ldata))
            yield (lpos, ldata)
            ldata = None

    if ldata: # if a block char was not closed then just dump out what remains
        if DEBUG:
            print "yield:%d-%d:%s"\
                  % (lpos-len(ldata)/2, lpos, _data2text(ldata))
        yield (lpos, ldata)
        ldata = None

    if DEBUG: _printBanner("done")


def getStyledPythonLogicalLine(offset, styledText, position, stylesToIgnore,
                               styleMask, context=2):
    r"""Return the logical Python line for the given position.
    
        "offset" is the position offset from the start of the source SciMoz
            buffer at which "styledText" begins. I.e. the whole buffer
            is not necessarily passed in.
        "styledText" is the styled text from which to extract.
        "position" is the position (NOT offset) from which to begin pulling
            out lines.
        "stylesToIgnore" is a list of SCE_* style numbers for the current
            language that should id which block structure characters should be
            ignored. Typically this is the list of comment and string styles.
        "styleMask" is a mask to apply to style bytes from styledText
            before comparison with stylesToIgnore
        "context" (optional) is a number of lines of context to look above
            and below to see if the "reasonable" logical line is bigger.
            Defaults to 2 lines.
    
    It groups together physical lines contined with explicit or implicit
    line joining rules similar to what is described here:
        http://www.python.org/doc/current/ref/logical.html
    Note that continuation characters will be replaced with a space.

    Without parsing the whole buffer this method can, at best, make a guess.
    Take this line for example:
                     "bar"<|>
    Normally this would just return this whole line. But what if it were in
    this context?
        os.path.join("foo",
                     "bar"<|>
                    )
    It should return the whole os.path.join(...) thing. You can keep this
    going to the top-level, so basically we have to pick a "reasonable"
    context range.

    Returns a 2-tuple:
        (<position at start of logical line>,
         <line/style data for the line>)
    """
    DEBUG = 0
    if DEBUG:
        print
        _printBanner("getStyledPythonLogicalLine(offset=%d, styledText, "
                     "position=%d, context=%r)" % (offset, position, context))
        _printBufferContext(offset, styledText, position)

    genBwd = genPythonLogicalLinesBwd
    genFwd = genPythonLogicalLinesFwd

    # First find the end of the current logical line.
    for endPos, data in genFwd(offset, styledText, position, stylesToIgnore,
                               styleMask):
        break
    else:
        #XXX is this right? genFwd yields nothing if at end of document
        endPos = position
    # "endPos" is the start of the next line, need to back up before the EOL
    # to get on the desired line, and then re-add it afterwards.
    endPosPreEOL = _getPosBeforeEOL(offset, styledText, endPos)
    for retPos, retData in genBwd(offset, styledText, endPosPreEOL,
                                  stylesToIgnore, styleMask):
        break
    if endPosPreEOL != endPos:
        retData += styledText[(endPosPreEOL-offset)*2:(endPos-offset)*2] # re-add the EOL
    if DEBUG: print "without context:%d:%s" % (retPos, _data2text(retData))
    
    if context:
        # Look back 'context' lines.
        startPoss = [] # start positions for previous 'context' lines
        lines = -1
        for startPos, data in genLinesBwd(offset, styledText, position):
            lines += 1
            if lines == 0: continue # context starts _before_ current line
            startPoss.insert(0, startPos) # put furthest away first
            if startPos-offset < 0 or lines >= context:
                break
        for startPos in startPoss:
            for endPos, data in genFwd(offset, styledText, startPos,
                                       stylesToIgnore, styleMask):
                break
            if DEBUG:
                print "potential from context pos %s: %d-%d: %s"\
                      % (startPos, endPos-len(data)/2, endPos, _data2text(data))
            if endPos > retPos: # logical line has been expanded (or is the same)
                retPos = endPos - (len(data)/2)
                retData = data
                if DEBUG: print "expand:%d:%s" % (retPos, _data2text(retData))
                break
    
        # Look forward 'context' lines.
        endPoss = [] # end positions for succeeding 'context' lines
        lines = -1
        for endPos, data in genLinesFwd(offset, styledText, position):
            lines += 1
            if lines == 0: continue # context starts _after_ current line
            endPoss.insert(0, endPos) # put furthest away first
            if endPos+offset >= len(styledText) or lines >= context:
                break
        for endPos in endPoss:
            if endPos <= retPos+len(retData)/2:
                if DEBUG: print "already expanded to or past pos %s" % endPos
                break
            endPosPreEOL = _getPosBeforeEOL(offset, styledText, endPos)
            for startPos, data in genBwd(offset, styledText, endPosPreEOL,
                                         stylesToIgnore, styleMask):
                break
            if endPosPreEOL != endPos:
                data += styledText[(endPosPreEOL-offset)*2:(endPos-offset)*2] # re-add the EOL
            if DEBUG:
                print "potential from context pos %s: %d-%d: %s"\
                      % (endPos, startPos, startPos+len(data)/2, _data2text(data))
            if startPos <= retPos: # logical line has been expanded (or is the same)
                retPos = startPos
                retData = data
                #if endPos != scimoz.textLength:
                #    retData += scimoz.getStyledText(endPos-1, endPos) # grab last char
                if DEBUG: print "expand:%d:%s" % (retPos, _data2text(retData))
                break
    
    if DEBUG: print "return:%d:%s" % (retPos, _data2text(retData))
    if DEBUG: _printBanner("done")
    return (retPos, retData)


def getPythonLogicalLineStartPosition(offset, styledText, position,
                                      stylesToIgnore, styleMask, context=2):
    """Return the start position of the logical Python line at the given pos.

        "offset" is the position offset from the start of the source SciMoz
            buffer at which "styledText" begins. I.e. the whole buffer
            is not necessarily passed in.
        "styledText" is the styled text from which to extract.
        "position" is the position (NOT offset) from which to begin pulling
            out lines.
        "stylesToIgnore" is a list of SCE_* style numbers for the current
            language that should id which block structure characters should be
            ignored. Typically this is the list of comment and string styles.
        "styleMask" is a mask to apply to style bytes from styledText
            before comparison with stylesToIgnore
        "context" (optional) is a number of lines of context to look above
            and below to see if the "reasonable" logical line is bigger.
            Defaults to 2 lines.
    """
    pos, data = getStyledPythonLogicalLine(offset, styledText, position,
                                            stylesToIgnore, styleMask,
                                            context=context)
    return pos


def getSimplifiedLeadingPythonExpr(offset, styledText, position,
                                   stylesToIgnore, styleMask, DEBUG=None):
    """Return a "simplified" Python expression preceding the given position.
    
        "offset" is the position offset from the start of the source SciMoz
            buffer at which "styledText" begins. I.e. the whole buffer
            is not necessarily passed in.
        "styledText" is the styled text from which to extract.
        "position" is the position (NOT offset) from which to begin pulling
            out lines.
        "stylesToIgnore" is a list of SCE_* style numbers for the current
            language that should id which block structure characters should be
            ignored. Typically this is the list of comment and string styles.
        "styleMask" is a mask to apply to style bytes from styledText
            before comparison with stylesToIgnore
    
    "Simplified", here, means get rid of newlines, whitespace, and function
    call arguments -- basically any stuff that is not used by the code intel
    database system for determining the resultant object type of the
    expression. For example (in which <|> represents the given position):
    
        GIVEN                       RETURN
        -----                       ------
        foo<|>.                     foo
        foo(bar<|>.                 bar
        foo(bar,blam)<|>.           foo()
        foo(bar,                    foo()
            blam)<|>.
    """
    if DEBUG is None: DEBUG = 0
    if DEBUG:
        print
        _printBanner("getSimplifiedLeadingPythonExpr(offset=%d, styledText, "
                     "position=%d)" % (offset, position))
        _printBufferContext(offset, styledText, position)
        _sciUtilsSvc = components.classes["@activestate.com/koSciUtils;1"].\
                       getService(components.interfaces.koISciUtils)

    for startPos, data in genPythonLogicalLinesBwd(offset, styledText,
                                                   position, stylesToIgnore,
                                                   styleMask):
        break
    if DEBUG: print "extract from: %s" % _data2text(data)

    WHITESPACE = tuple(" \t\n\r\v\f")
    BLOCKCLOSES = tuple(")}]")
    STOPOPS = tuple("({[,&+=^|%/<>;:")
    expr = ""
    i = len(data)-2
    while i >= 0:
        ch = data[i]
        style = ord(data[i+1]) & styleMask
        #XXX Make strings -> ""?
        if ch in WHITESPACE:
            # drop all whitespace
            while i >= 0 and data[i] in WHITESPACE:
                if DEBUG: print "drop whitespace: %r" % data[i]
                i -= 2
            # If there are two whitespace-separated words then this is
            # (likely or always?) a language keyword or declaration construct
            # at which we want to stop. E.g.
            #   if foo<|> and ...
            #   def foo<|>(...
            #   float myfunc<|>(...
            #   int myvar = ...
            if i >= 0 and expr and _isident(expr[-1]) and (
               _isident(data[i]) or _isdigit(data[i])):
                if DEBUG: print "stop at (likely?) start of keyword or declaration: %r" % data[i]
                break
        elif style in stylesToIgnore: # drop styles to ignore
            while i >= 0 and (ord(data[i+1]) & styleMask) in stylesToIgnore:
                if DEBUG: print "drop char of style to ignore: %r" % data[i]
                i -= 2
        elif ch in BLOCKCLOSES:
            if DEBUG: print "found block at %d: %r" % (i/2+startPos, ch)
            expr += ch

            BLOCKS = { # map block close char to block open char
                ')': '(',
                ']': '[',
                '}': '{',
            }
            stack = [] # stack of blocks: (<block close char>, <style>)
            stack.append( (ch, style, BLOCKS[ch]) )
            i -= 2
            while i >= 0:
                ch = data[i]
                style = ord(data[i+1]) & styleMask
                if ch in BLOCKS and not style in stylesToIgnore:
                    stack.append( (ch, style, BLOCKS[ch]) )
                elif ch == stack[-1][2] and style == stack[-1][1]:
                    stack.pop()
                    if not stack:
                        break
                i -= 2

            if DEBUG: print "jump to matching brace at %d: %r" % (i/2+startPos, ch)
            expr += ch
            i -= 2
        elif ch in STOPOPS:
            break
        else:
            if DEBUG:
                styleName = _sciUtilsSvc.styleNameFromNum("Python", style)
                print "add char: %r (%s)" % (ch, styleName)
            expr += ch
            i -= 2
    expr = list(expr.strip()); expr.reverse(); expr = ''.join(expr)
    if DEBUG:
        print "return: %r" % expr
        _printBanner("done")
    return expr


_gPerlVarPat = re.compile(r"((?P<prefix>[$@%\\*&]+)\s*)?(?P<scope>(::)?\b((?!\d)\w*?(::|'))*)(?P<name>(?!\d)\w+)$")
def getLeadingPerlCITDLExpr(offset, styledText, position,
                            stylesToIgnore, styleMask, DEBUG=None):
    """Parse out the leading Perl expression and return a CITDL expression
    for it.
    
        "offset" is the position offset from the start of the source SciMoz
            buffer at which "styledText" begins. I.e. the whole buffer
            is not necessarily passed in.
        "styledText" is the styled text from which to extract.
        "position" is the position (NOT offset) from which to begin pulling
            out lines.
        "stylesToIgnore" is a list or mapping of SCE_* style numbers for the
            current language that should id which block structure characters
            should be ignored. Typically this is the list of comment and
            string styles.
        "styleMask" is a mask to apply to style bytes from styledText
            before comparison with stylesToIgnore

    We parse out the Perl expression preceding the given position (typically
    a calltip/autocomplete trigger position), simplify the expression
    (by removing whitespace, etc.) and translate that to an appropriate
    CITDL (*) expression. Returns None if there is no appropriate such
    expression.
    
    Optimization Notes:
    - We can throw out Perl expressions with function calls
      because CodeIntel does not currently handle return values.
    - We can throw out Perl exprs that span an EOL: 80/20 rule. (We currently
      don't throw these away, though.)
    - Abort at hash and list indexing: the types of elements in these objects
      are not tracked by CodeIntel.
    - Punt on Perl references, e.g. \$foo, \@bar. XXX I wonder if I can
      just ignore references and assume the user is doing the right thing.
      I.e. I just presume that a reference is dereferenced properly when
      required. Dunno.
    - Currently we don't really make use of the styling info (as does
      getSimplifiedLeadingPythonExpr() for Python) because we abort at
      indexing, function call arguments, etc. where recognizing
      string/number/regex boundaries would be useful. This info might be
      useful later if this algorithm is beefed up.
    
    For example (in which <|> represents the given position):
    
        GIVEN                       LEADING EXPR            CITDL EXPR
        -----                       ------------            ----------
        split<|>                    split                   split
        chmod<|>(                   chmod                   chmod
        $Foo::bar<|>(               $Foo::bar               Foo.$bar
        &$make_coffee<|>(           &$make_coffee           &$make_coffee
        Win32::OLE<|>->             Win32::OLE              Win32::OLE
        Win32::OLE->GetObject<|>(   Win32::OLE->GetObject   Win32::OLE.GetObject
        split join                  join                    join
        foo->bar                    foo->bar                foo.bar
        main::

    Note that the trigger character is sometimes necessary to resolve
    ambiguity. Given "Foo::Bar" without the trailing trigger char, we cannot
    know if the CITDL should be "Foo.Bar" or "Foo::Bar":

        GIVEN               CITDL EXPR
        -----               ----------
        Foo::Bar<|>::       Foo::Bar
        $Foo::Bar<|>::      Foo::Bar
        Foo::Bar<|>->       Foo::Bar
        Foo::Bar<|>(        Foo.Bar
        Foo::Bar<|>         Foo.Bar         # trigger char is a space here
        $Foo::Bar<|>->      Foo.$Bar
        $Foo::Bar<|>(       Foo.$Bar
        $Foo::Bar<|>        Foo.$Bar        # trigger char is a space here

    * http://specs.tl.activestate.com/kd/kd-0100.html#citdl
    """
    if DEBUG is None: DEBUG = 0
    if DEBUG:
        print
        _printBanner("getLeadingPerlCITDLExpr(offset=%d, styledText, "
                     "position=%d)" % (offset, position))
        _printBufferContext(offset, styledText, position)
        _sciUtilsSvc = components.classes["@activestate.com/koSciUtils;1"].\
                       getService(components.interfaces.koISciUtils)

    filter, citdl = None, []
    text = ''.join([styledText[i] for i in range(0, len(styledText), 2)])
    i = position-offset-1
    while i >= 0:
        # Parse off a perl variable/identifier.
        if DEBUG:
            print "look for Perl var at end of %r" % text[:i+1]
        match = _gPerlVarPat.search(text[:i+1])
        if not match:
            if DEBUG:
                if i > 20:
                    segment = '...'+text[i-20:i+1]
                else:
                    segment = text[:i+1]
                print "could not match a Perl var off %r" % segment
            citdl = None
            break
        prefix = match.group("prefix") or ""
        scope = match.group("scope")
        name = match.group("name")
        try:
            triggerChar = text[i+1]
        except IndexError, ex:
            log.warn("text does not include trailing trigger "
                     "char to resolve possible ambiguities in '%s'",
                     match.group(0))
            triggerChar = None
        if triggerChar == ':':
            # Foo::Bar<|>::       Foo::Bar
            # $Foo::Bar<|>::      Foo::Bar
            citdl.insert(0, scope+name) # intentionally drop prefix
            # The prefix string is relevant for filtering the list of
            # members for AutoComplete. E.g. if the prefix char is '&' then
            # only subs should be shown. If '%', then only hashes.
            filter = prefix
        elif triggerChar == '-' and not prefix:
            # Foo::Bar<|>->       Foo::Bar
            citdl.insert(0, scope+name)
        else:
            # Foo::Bar<|>(        Foo.Bar
            # Foo::Bar<|>         Foo.Bar         # trigger char is a space here
            # $Foo::Bar<|>->      Foo.$Bar
            # $Foo::Bar<|>(       Foo.$Bar
            # $Foo::Bar<|>        Foo.$Bar        # trigger char is a space here
            citdl.insert(0, prefix+name)
            if scope:
                scope = scope[:-2] # drop trailing '::'
                if scope:
                    citdl.insert(0, scope)
        i -= len(match.group(0))
        if DEBUG:
            print "parse out Perl var: %r (prefix=%r, scope=%r, name=%r): %r"\
                  % (match.group(0), prefix, scope, name, citdl)

        # Preceding characters will determine if we stop or continue.
        WHITESPACE = tuple(" \t\n\r\v\f")
        while i >= 0 and text[i] in WHITESPACE:
            #if DEBUG: print "drop whitespace: %r" % text[i]
            i -= 1
        if i >= 0 and (ord(styledText[i*2+1]) & styleMask) in stylesToIgnore:
            if DEBUG:
                style = ord(styledText[i*2+1]) & styleMask
                styleName = _sciUtilsSvc.styleNameFromNum("Perl", style)
                print "stop at style to ignore: %r (%s)" % (text[i], styleName)
            break
        elif i >= 1 and text[i-1:i+1] == '->':
            if DEBUG: print "parse out '->'"
            i -= 2
            while i >= 0 and text[i] in WHITESPACE:
                #if DEBUG: print "drop whitespace: %r" % text[i]
                i -= 1
            continue
        else:
            break

    if citdl:
        retval = (filter, '.'.join(citdl))
    else:
        retval = (filter, None)
    if DEBUG:
        print "return: %r" % (retval,)
        _printBanner("done")
    return retval


# Example Ruby "leading expressions":
#   send
#   File.open
#   Zlib::Deflate.deflate
#   0.step (XXX punt on numbers for now)
#   @assigned
#   @@foo
#   $blah
#   @assigned.foo
#   $_  (XXX punt on the special vars for now)
_gRubyLeadingExprPat = re.compile(r"""
    (
        (       # the set of those with @, @@, $ prefix
            (@@|@|$)%(ident)s(\.%(ident)s)*    
        )
        |
        (       # or, the set of those without the prefix
            %(ident)s(::%(ident)s)*(\.%(ident)s)*
        )
        [?!]?   # methods can end with '?' or '!' (XXX what about '='?)
    )\s*$          # anchored at the end of the string
    """ % {"ident": "((?!\d)\w+)"}, re.X)
def getLeadingRubyCITDLExpr(offset, styledText, position,
                            stylesToIgnore, styleMask, DEBUG=None):
    """Parse out the leading Ruby expression and return a CITDL expression
    for it.
    
        "offset" is the position offset from the start of the source SciMoz
            buffer at which "styledText" begins. I.e. the whole buffer
            is not necessarily passed in.
        "styledText" is the styled text from which to extract.
        "position" is the position (NOT offset) from which to begin pulling
            out lines.
        "stylesToIgnore" is a list or mapping of SCE_* style numbers for the
            current language that should id which block structure characters
            should be ignored. Typically this is the list of comment and
            string styles.
        "styleMask" is a mask to apply to style bytes from styledText
            before comparison with stylesToIgnore

    We parse out the Ruby expression preceding the given position (typically
    a calltip/autocomplete trigger position), simplify the expression
    (by removing whitespace, etc.) and translate that to an appropriate
    CITDL (*) expression. Returns None if there is no appropriate such
    expression.
    
    Optimization Notes:
    - We can throw out Ruby expressions with function calls
      because CodeIntel does not currently handle return values.
    - Abort at hash and list indexing: the types of elements in these objects
      are not tracked by CodeIntel.
    - Currently we don't really make use of the styling info (as does
      getSimplifiedLeadingPythonExpr() for Python) because we abort at
      indexing, function call arguments, etc. where recognizing
      string/number/regex boundaries would be useful. This info might be
      useful later if this algorithm is beefed up.
    
    For example (in which <|> represents the given position):
    
        GIVEN                       LEADING EXPR            CITDL EXPR
        -----                       ------------            ----------
        send<|>(                    send                    send
        foo.instance_of?<|>(        foo.instance_of?        foo.instance_of?
        File.open<|>(               File.open               File.open
        Zlib::Deflate.deflate<|>(   Zlib::Deflate.deflate   Zlib::Deflate.deflate
            XXX Should that be "Zlib.Deflate.deflate"?
        0.step<|>(                  0.step                  0.step
            XXX Or should this be "Number.step"? Eventually, yes we should translate
                language literals to their class/object name here (ditto
                for Python strings, lists, etc.). However, for now we
                punt. First step would be to actually trigger on those:
                we skip now.
        @assigned<|>.               @assigned               @assigned
        @@foo<|>.                   @foo                    @foo
        $blah<|>.                   @blah                   @blah
        YAML::PRIVATE_TYPES[r].call<|>(                     <punt because of []>
        [$2].pack(                                          <punt>
        @db_class<|>::WidgetClassName                       <punt: looks to be rare>

    * http://specs.activestate.com/komodo30/func/code_intelligence.html#citdl
    """
    if DEBUG is None: DEBUG = 0
    if DEBUG:
        print
        _printBanner("getLeadingRubyCITDLExpr(offset=%d, styledText, "
                     "position=%d)" % (offset, position))
        _printBufferContext(offset, styledText, position)
        _sciUtilsSvc = components.classes["@activestate.com/koSciUtils;1"].\
                       getService(components.interfaces.koISciUtils)

    # Parse off a Ruby leading expression.
    text = ''.join([styledText[i] for i in range(0, len(styledText), 2)])
    i = position-offset-1
    if DEBUG:
        print "look for Ruby var at end of %r" % text[:i+1]
    match = _gRubyLeadingExprPat.search(text[:i+1])
    if not match:
        expr = None
        if DEBUG:
            if i > 20:
                segment = '...'+text[i-20:i+1]
            else:
                segment = text[:i+1]
            print "could not match a Ruby var off %r" % segment
    else:
        expr = match.group(0)
        if DEBUG:
            print "parsed out leading Ruby expr: %r" % expr

    # Convert to a CITDL expression (CodeIntel uses "." for attribute
    # lookup).
    if expr:
        expr = expr.replace("::", ".")

    if DEBUG:
        print "return: %r" % (expr,)
        _printBanner("done")
    return expr



#---- self-test suites

class SciUtilsTestCase(SciMozTestCase):
    _langSvcs = {}
    def _getLanguageService(self, languageName):
        if languageName not in self._langSvcs:
            contractID = "@activestate.com/koLanguage?language=%s;1" % languageName.replace(" ", "%20")
            langSvc = components.classes[contractID].getService()
            self._langSvcs[languageName] = langSvc
        return self._langSvcs[languageName]

    def setUp(self):
        pyLangSvc = self._getLanguageService("Python")
        perlLangSvc = self._getLanguageService("Perl")
        rubyLangSvc = self._getLanguageService("Ruby")
        self.stylesToIgnore = {
            "Python": pyLangSvc.getCommentStyles()+pyLangSvc.getStringStyles(),
            "Perl": perlLangSvc.getCommentStyles()+perlLangSvc.getStringStyles(),
#XXX This isn't so straightforward
##            "Ruby": rubyLangSvc.getCommentStyles()+perlLangSvc.getStringStyles(),
        }

    def assertPerlCITDLExpr(self, language, offset, buffer, expected_citdl,
                            expected_filter=None):
        self._setupSciMoz(buffer, language)
        styleMask = (1 << self.scimoz.styleBits) - 1
        data = self.scimoz.getStyledText(offset, self.scimoz.textLength)
        actual = getLeadingPerlCITDLExpr(
            offset, data, self.scimoz.currentPos,
            self.stylesToIgnore[language], styleMask)
        expected = (expected_filter, expected_citdl)
        self.assertEqual(actual, expected,
                         "leading Perl CITDL expr is not as expected: expected %r, got %r"\
                         % (expected, actual))

    def test_getLeadingPerlCITDLExpr(self):
        self.assertPerlCITDLExpr("Perl", 0, "split<|> ", "split")
        self.assertPerlCITDLExpr("Perl", 0, "chmod<|>(", "chmod")
        self.assertPerlCITDLExpr("Perl", 0, "&$make_coffee<|>(", "&$make_coffee")
        self.assertPerlCITDLExpr("Perl", 0, "$foo . $bar<|>->", "$bar")
        self.assertPerlCITDLExpr("Perl", 0, "foo[split<|> ", "split")
        #XXX Might want to consider aborting on the following case because
        #    barewords are allowed in Perl hash indexing.
        self.assertPerlCITDLExpr("Perl", 0, "foo{split<|> ", "split")
        self.assertPerlCITDLExpr("Perl", 0, "foo()<|>", None)
        self.assertPerlCITDLExpr("Perl", 3, "XYZfoo()<|>", None)
        self.assertPerlCITDLExpr("Perl", 3, "XYZsplit<|> ", "split")
        self.assertPerlCITDLExpr("Perl", 0, "foo(a,b)<|>", None)
        self.assertPerlCITDLExpr("Perl", 0, "my $a = $foo<|>->", "$foo")

        self.assertPerlCITDLExpr("Perl", 0, "foo;bar<|>(", "bar")
        self.assertPerlCITDLExpr("Perl", 0, "foo(bar,baz<|>(", "baz")
        self.assertPerlCITDLExpr("Perl", 0, "split join<|> ", "join")
        self.assertPerlCITDLExpr("Perl", 0, "foo->bar<|>(", "foo.bar")
        self.assertPerlCITDLExpr("Perl", 0, "Win32::OLE<|>->", "Win32::OLE")
        self.assertPerlCITDLExpr("Perl", 0, "Win32::OLE->GetObject<|>(", "Win32::OLE.GetObject")

        self.assertPerlCITDLExpr("Perl", 0,
                                 "split(/foo/,\n    join<|>(", "join")
        self.assertPerlCITDLExpr("Perl", 0,
                                 "split(/foo()/,\n    join<|>(", "join")
        self.assertPerlCITDLExpr("Perl", 0,
                                 "split(/foo/,\r\n    join<|>(", "join")

        self.assertPerlCITDLExpr("Perl", 0,
                                 "sub foo {}\n\nsplit<|> ", "split")

        # Preceding statement was not properly terminated with ';'.
        self.assertPerlCITDLExpr("Perl", 0,
                                 "$ua->agent()\nmy<|> ", "my")

        ## Can't actually test this because, I think, the styling in the
        ## test SciMoz gets PL_ERROR instead of the PL_COMMENTLINE for the
        ## comment line here.
        #self.assertPerlCITDLExpr("Perl", 0,
        #                         "# Data::Dumper->\n\nDumperX<|>(",
        #                         # NOT Data::Dumper.DumperX
        #                         "DumperX")

        testcases = r"""
            Foo::Bar<|>(        # Foo.Bar
            Foo::Bar<|>         # Foo.Bar
            Foo::Bar<|>::       # Foo::Bar ''
            Foo::Bar<|>->       # Foo::Bar
            $Foo::Bar<|>->      # Foo.$Bar
            $Foo::Bar<|>::      # Foo::Bar '$'
            @Foo::Bar<|>::      # Foo::Bar '@'
            %Foo::Bar<|>::      # Foo::Bar '%'
            &Foo::Bar<|>::      # Foo::Bar '&'
            *Foo::Bar<|>::      # Foo::Bar '*'
            @$Foo::Bar<|>::     # Foo::Bar '@$'
            %$Foo::Bar<|>::     # Foo::Bar '%$'
            &$Foo::Bar<|>::     # Foo::Bar '&$'
            $Foo::Bar<|>(       # Foo.$Bar
            $Foo::Bar<|>        # Foo.$Bar

            m<|>        # m
            split<|>    # split
            baz<|>      # baz
            $2baz<|>    #
            $baz<|>     # $baz
            @baz<|>     # @baz
            %baz<|>     # %baz
            *baz<|>     # *baz
            &baz<|>     # &baz
            &$baz<|>    # &$baz
            \$baz<|>    # \$baz
            $foo = \*baz<|>         # \*baz
            $::bar<|>               # $bar
            ::Bar2::_baz<|>(        # ::Bar2._baz
            $FOO::Bar2::_baz<|>     # FOO::Bar2.$_baz
            @FOO::Bar2::_baz<|>     # FOO::Bar2.@_baz
            %FOO::Bar2::_baz<|>     # FOO::Bar2.%_baz
            *FOO::Bar2::_baz<|>     # FOO::Bar2.*_baz
            &FOO::Bar2::_baz<|>     # FOO::Bar2.&_baz
            &$FOO::Bar2::_baz<|>    # FOO::Bar2.&$_baz
            \$FOO::Bar2::_baz<|>    # FOO::Bar2.\$_baz
            \*FOO::Bar2::_baz<|>    # FOO::Bar2.\*_baz

            $ baz<|>     # $baz

        """.splitlines(0)
        for testcase in testcases:
            if not testcase.strip(): continue
            input, expected = testcase.split('#')
            expected = expected.strip()
            if not expected:
                expected_citdl, expected_filter = None, None
            elif ' ' in expected:
                expected_citdl, expected_filter_repr = expected.split()
                expected_filter = eval(expected_filter_repr)
            else:
                expected_citdl, expected_filter = expected, None
            self.assertPerlCITDLExpr("Perl", 0, input, expected_citdl,
                                     expected_filter)

    def assertStyledLineIs(self, getFunc, language, offset, buffer, context,
                            expectedPos, expectedText):
        self._setupSciMoz(buffer, language)
        styleMask = (1 << self.scimoz.styleBits) - 1
        data = self.scimoz.getStyledText(offset, self.scimoz.textLength)
        actualPos, data = getFunc(offset, data, self.scimoz.currentPos,
                                  self.stylesToIgnore[language],
                                  styleMask, context=context)
        actualText = ''.join([data[i] for i in range(0, len(data), 2)])
        
        self.assertEqual(actualText, expectedText, """\
line text is not as expected:
---------- expected this ----------
%s
---------- got this ---------------
%s
-----------------------------------"""
% (expectedText.replace('\n', "<LF>").replace('\r', "<CR>"),
   actualText.replace('\n', "<LF>").replace('\r', "<CR>")))
        self.assertEqual(actualPos, expectedPos,
                         "line pos is not as expected: expected %d, got %d"\
                         % (expectedPos, actualPos))

    def test_getStyledPythonLogicalLine(self):
        getFunc = getStyledPythonLogicalLine
        self.assertStyledLineIs(getFunc, "Python", 0, "spam\nfoo(bar,<|> spam)\nbar", 2,
                                 5, "foo(bar, spam)\n")
        self.assertStyledLineIs(getFunc, "Python", 0, "spam\r\nfoo(bar,<|> spam)\r\nbar", 2,
                                 6, "foo(bar, spam)\r\n")
        self.assertStyledLineIs(getFunc, "Python", 0, "spam\rfoo(bar,<|> spam)\rbar", 2,
                                 5, "foo(bar, spam)\r")

        self.assertStyledLineIs(getFunc, "Python", 0, "spam\nfoo(bar,\n\t<|>spam)\nbar", 2,
                                 5, "foo(bar,\n\tspam)\n")
        self.assertStyledLineIs(getFunc, "Python", 0, "spam\nfoo\\\n(bar,<|>spam)\nbar", 2,
                                 5, "foo \n(bar,spam)\n")

        # Specifically testing the 'context' handling here.
        self.assertStyledLineIs(getFunc, "Python", 0,
            'os.path.join("foo",\n"blam",\n"bar",\n"baz",<|>\n"ham",\n"spam",\n"eggs")', 2,
            35, '"baz",\n')
        self.assertStyledLineIs(getFunc, "Python", 0,
            'os.path.join("foo",\n"blam",\n"bar",\n"baz",<|>\n"ham",\n"spam",\n"eggs")', 3,
            0, 'os.path.join("foo",\n"blam",\n"bar",\n"baz",\n"ham",\n"spam",\n"eggs")')
        self.assertStyledLineIs(getFunc, "Python", 0,
            'os.path.join("foo",\n"blam",\n"bar",<|>\n"baz",\n"ham",\n"spam",\n"eggs")', 2,
            0, 'os.path.join("foo",\n"blam",\n"bar",\n"baz",\n"ham",\n"spam",\n"eggs")')
        self.assertStyledLineIs(getFunc, "Python", 0,
            'os.path.join("foo",\n"blam",\n"bar",\n"baz",\n"ham"<|>,\n"spam",\n"eggs")', 2,
            0, 'os.path.join("foo",\n"blam",\n"bar",\n"baz",\n"ham",\n"spam",\n"eggs")')

        self.assertStyledLineIs(getFunc, "Python", 0,
            'os.path.join("foo",\n"blam",\n"bar",\n"baz",<|>\n"ham",\n"spam",\n"eggs")\n', 3,
            0, 'os.path.join("foo",\n"blam",\n"bar",\n"baz",\n"ham",\n"spam",\n"eggs")\n')
        self.assertStyledLineIs(getFunc, "Python", 0,
            'os.path.join("foo",\r\n"blam",\r\n"bar",\r\n"baz",<|>\r\n"ham",\r\n"spam",\r\n"eggs")\r\n', 3,
            0, 'os.path.join("foo",\r\n"blam",\r\n"bar",\r\n"baz",\r\n"ham",\r\n"spam",\r\n"eggs")\r\n')
        self.assertStyledLineIs(getFunc, "Python", 0,
            'os.path.join("foo",\r"blam",\r"bar",\r"baz",<|>\r"ham",\r"spam",\r"eggs")\r', 3,
            0, 'os.path.join("foo",\r"blam",\r"bar",\r"baz",\r"ham",\r"spam",\r"eggs")\r')

        self.assertStyledLineIs(getFunc, "Python", 0,
            'foo\n<|> # hi\nbar\n', 2,
            4, ' # hi\n')
        self.assertStyledLineIs(getFunc, "Python", 3,
            'XYZfoo\n<|> # hi\nbar\n', 2,
            7, ' # hi\n')

    def assertGeneratedTextIs(self, genFunc, language, offset, buffer,
                              expected):
        self._setupSciMoz(buffer, language)
        if genFunc in (genLinesBwd, genLinesFwd):
            data = self.scimoz.getStyledText(offset, self.scimoz.textLength)
            generator = genFunc(offset, data, self.scimoz.currentPos)
        else:
            styleMask = (1 << self.scimoz.styleBits) - 1
            data = self.scimoz.getStyledText(offset, self.scimoz.textLength)
            generator = genFunc(offset, data, self.scimoz.currentPos,
                                self.stylesToIgnore[language],
                                styleMask)
        actual = []
        for pos, data in generator:
            text = ''.join([data[i] for i in range(0, len(data), 2)])
            if expected and len(expected[0]) == 2:
                # Expected output including the 'pos' return values was
                # specified.
                actual.append( (pos, text) )
            else:
                actual.append(text)
            
        self.assertEqual(actual, expected, """\
generated lines are not as expected:
---------- expected this ----------
%s
---------- got this ---------------
%s
-----------------------------------"""
% (pprint.pformat(expected), pprint.pformat(actual)))

    def test_genLinesBwd(self):
        genFunc = genLinesBwd
        self.assertGeneratedTextIs(genFunc, "Python", 0, "foo<|>", ["foo"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "foo<|>bar", ["foo"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "foo\nbar<|>", ["bar", "foo\n"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "foo\r\nbar<|>", ["bar", "foo\r\n"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "foo\rbar<|>", ["bar", "foo\r"])
        self.assertGeneratedTextIs(genFunc, "Python", 1, "Xfoo<|>", ["foo"])
        self.assertGeneratedTextIs(genFunc, "Python", 1, "Xfoo<|>bar", ["foo"])
        self.assertGeneratedTextIs(genFunc, "Python", 1, "Xfoo\nbar<|>", ["bar", "foo\n"])
        self.assertGeneratedTextIs(genFunc, "Python", 1, "Xfoo\r\nbar<|>", ["bar", "foo\r\n"])
        self.assertGeneratedTextIs(genFunc, "Python", 1, "Xfoo\rbar<|>", ["bar", "foo\r"])

        self.assertGeneratedTextIs(genFunc, "Python", 0, "foo\r\nbar\n\nspam\r\reggs<|>",
                                    ["eggs", "\r", "spam\r", "\n", "bar\n", "foo\r\n"])

        self.assertGeneratedTextIs(genFunc, "Python", 3, "XYZxyzfoo\rbar<|>\r",
                                    [(10, "bar"), (3, "xyzfoo\r")])

    def test_genLinesFwd(self):
        genFunc = genLinesFwd
        self.assertGeneratedTextIs(genFunc, "Python", 0, "foo<|>", [])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "<|>foo", ["foo"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "foo<|>bar", ["bar"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "<|>foo\nbar", ["foo\n", "bar"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "<|>foo\r\nbar", ["foo\r\n", "bar"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "<|>foo\rbar", ["foo\r", "bar"])

        self.assertGeneratedTextIs(genFunc, "Python", 0, "<|>foo\r\nbar\n\nspam\r\reggs",
                                   ["foo\r\n", "bar\n", "\n", "spam\r", "\r", "eggs"])

        self.assertGeneratedTextIs(genFunc, "Python", 3, "XYZxyz<|>foo\rbar",
                                   [(10, "foo\r"), (13, "bar")])


    def test_genContinuedLinesBwd(self):
        genFunc = genContinuedLinesBwd
        self.assertGeneratedTextIs(genFunc, "Python", 0, "foo<|>", ["foo"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "foo<|>bar", ["foo"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "foo\nbar<|>", ["bar", "foo\n"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "foo\\\nbar<|>", ["foo \nbar"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "foo\\\r\nbar<|>", ["foo \r\nbar"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "foo\\\rbar<|>", ["foo \rbar"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "foo\\\\\nbar<|>spam", ["bar", "foo\\\\\n"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "foo\\\\\\\nbar<|>spam", ["foo\\\\ \nbar"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "foo\\\nbar<|>", ["foo \nbar"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "foo #\\\nbar<|>", ["bar", "foo #\\\n"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "foo '''\\\n'''bar<|>", ["'''bar", "foo '''\\\n"])

        self.assertGeneratedTextIs(genFunc, "Python", 3, "XYZfoo\\\nbar<|>",
                                    [(3, "foo \nbar")])


    def test_genContinuedLinesFwd(self):
        genFunc = genContinuedLinesFwd
        self.assertGeneratedTextIs(genFunc, "Python", 0, "foo<|>", [])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "<|>foo", ["foo"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "foo<|>bar", ["bar"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "<|>foo\nbar", ["foo\n", "bar"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "<|>foo\\\nbar", ["foo \nbar"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "<|>foo\\\r\nbar", ["foo \r\nbar"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "<|>foo\\\rbar", ["foo \rbar"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "spam<|>foo\\\\\nbar", ["foo\\\\\n", "bar"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "spam<|>foo\\\\\\\nbar", ["foo\\\\ \nbar"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "<|>foo\\\nbar", ["foo \nbar"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "<|>foo #\\\nbar", ["foo #\\\n", "bar"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "<|>foo '''\\\n'''bar", ["foo '''\\\n", "'''bar"])

        self.assertGeneratedTextIs(genFunc, "Python", 0,
                                   "spam\r<|>foo\\\r(bar, spam)\rbar",
                                   [(22, "foo \r(bar, spam)\r"), (25, "bar")])

        self.assertGeneratedTextIs(genFunc, "Python", 3,
                                   "XYZxyz<|>foo\\\nbar",
                                   [(14, "foo \nbar")])


    def test_genPythonLogicalLinesBwd(self):
        genFunc = genPythonLogicalLinesBwd
        self.assertGeneratedTextIs(genFunc, "Python", 0, "foo<|>", ["foo"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "foo<|>bar", ["foo"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "foo\nbar<|>", ["bar", "foo\n"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "foo\\\nbar<|>", ["foo \nbar"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "foo\\\r\nbar<|>", ["foo \r\nbar"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "foo\\\rbar<|>", ["foo \rbar"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "foo\\\\\nbar<|>spam", ["bar", "foo\\\\\n"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "foo\\\\\\\nbar<|>spam", ["foo\\\\ \nbar"])

        self.assertGeneratedTextIs(genFunc, "Python", 0, "foo(\nbar)<|>", ["foo(\nbar)"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "foo(blam,\n\tbar)<|>", ["foo(blam,\n\tbar)"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "foo(blam, bar)<|>", ["foo(blam, bar)"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "foo\n(blam, bar)<|>", ["(blam, bar)", "foo\n"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "foo\\\n(blam, bar)<|>", ["foo \n(blam, bar)"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "foo('''spam \nand eggs''', bar)<|>",
                                    ["foo('''spam \nand eggs''', bar)"])
        #XXX Not supporting this for now.
        #self.assertGeneratedTextIs(genFunc, "Python", 0, "'''spam \nand eggs'''.split()<|>",
        #                            ["'''spam \nand eggs'''.split()"])

        self.assertGeneratedTextIs(genFunc, "Python", 0, """\
# a complex call
foo(bar, (1,2),
    # another tricky ( comment
    "({],boo").\\
bar
# a tricky ) comment
# a dictionary
{'one': 1,
 'two': 2}<|>""",
["{'one': 1,\n 'two': 2}",
 "# a dictionary\n",
 "# a tricky ) comment\n",
 'foo(bar, (1,2),\n    # another tricky ( comment\n    "({],boo"). \nbar\n',
 "# a complex call\n"])

        self.assertGeneratedTextIs(genFunc, "Python", 0,
            'os.path.join("foo",\n"blam",\n"bar",\n"baz",\n"ham",\n"spam",\n"eggs")<|>',
            ['os.path.join("foo",\n"blam",\n"bar",\n"baz",\n"ham",\n"spam",\n"eggs")'])

        self.assertGeneratedTextIs(genFunc, "Python", 3,
                                   "XYZfoo\\\n(blam, bar)<|>",
                                   [(3, "foo \n(blam, bar)")])


    def test_genPythonLogicalLinesFwd(self):
        genFunc = genPythonLogicalLinesFwd
        self.assertGeneratedTextIs(genFunc, "Python", 0, "foo<|>", [])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "<|>foo", ["foo"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "foo<|>bar", ["bar"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "<|>foo\nbar", ["foo\n", "bar"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "<|>foo\\\nbar", ["foo \nbar"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "<|>foo\\\r\nbar", ["foo \r\nbar"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "<|>foo\\\rbar", ["foo \rbar"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "spam<|>foo\\\\\nbar", ["foo\\\\\n", "bar"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "spam<|>foo\\\\\\\nbar", ["foo\\\\ \nbar"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "<|>foo\\\nbar", ["foo \nbar"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "<|>foo #\\\nbar", ["foo #\\\n", "bar"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "<|>foo '''\\\n'''bar", ["foo '''\\\n", "'''bar"])

        self.assertGeneratedTextIs(genFunc, "Python", 0, "<|>foo(\nbar)", ["foo(\nbar)"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "<|>foo(blam,\n\tbar)", ["foo(blam,\n\tbar)"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "<|>foo(blam, bar)", ["foo(blam, bar)"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "<|>foo\n(blam, bar)", ["foo\n", "(blam, bar)"])
        self.assertGeneratedTextIs(genFunc, "Python", 0, "<|>foo\\\n(blam, bar)", ["foo \n(blam, bar)"])

        self.assertGeneratedTextIs(genFunc, "Python", 0, """\
<|># a complex call
foo(bar, (1,2),
    # another tricky ( comment
    "({],boo").\\
bar
# a tricky ) comment
# a dictionary
{'one': 1,
 'two': 2}""",
["# a complex call\n",
 'foo(bar, (1,2),\n    # another tricky ( comment\n    "({],boo"). \nbar\n',
 "# a tricky ) comment\n",
 "# a dictionary\n",
 "{'one': 1,\n 'two': 2}"])

        self.assertGeneratedTextIs(genFunc, "Python", 3,
                                   "XYZxyz<|>foo\\\n(blam, bar)",
                                   [(22, "foo \n(blam, bar)")])


    def assertLeadingExpr(self, language, offset, buffer, expected):
        self._setupSciMoz(buffer, language)
        styleMask = (1 << self.scimoz.styleBits) - 1
        data = self.scimoz.getStyledText(offset, self.scimoz.textLength)
        actual = getSimplifiedLeadingPythonExpr(
            offset, data, self.scimoz.currentPos,
            self.stylesToIgnore[language], styleMask)
        self.assertEqual(actual, expected,
                         "leading expr is not as expected: expected %r, got %r"\
                         % (expected, actual))

    def test_getSimplifiedLeadingPythonExpr_simple(self):
        self.assertLeadingExpr("Python", 0, "foo<|>", "foo")
        self.assertLeadingExpr("Python", 0, "foo.bar<|>", "foo.bar")
        self.assertLeadingExpr("Python", 0, "foo(bar<|>", "bar")
        self.assertLeadingExpr("Python", 0, "foo[bar<|>", "bar")
        self.assertLeadingExpr("Python", 0, "foo{bar<|>", "bar")
        self.assertLeadingExpr("Python", 0, "foo()<|>", "foo()")
        self.assertLeadingExpr("Python", 3, "XYZfoo()<|>", "foo()")
        self.assertLeadingExpr("Python", 0, "foo(a,b)<|>", "foo()")
        self.assertLeadingExpr("Python", 0, "a = foo<|>", "foo")
        self.assertLeadingExpr("Python", 0, "a = foo(bar<|>, blam)", "bar")
        self.assertLeadingExpr("Python", 3, "XYZa = foo(bar<|>, blam)", "bar")
    def test_getSimplifiedLeadingPythonExpr_complex(self):
        self.assertLeadingExpr("Python", 0, "foo(',', (1+2))<|>", "foo()")
        self.assertLeadingExpr("Python", 0, "foo(',({[', {one:1,two:2})<|>", "foo()")
        self.assertLeadingExpr("Python", 0, "(',({[', {one:1,two:2})<|>", "()")
    def test_getSimplifiedLeadingPythonExpr_multiline(self):
        self.assertLeadingExpr("Python", 0, "foo(bar,\nblam<|>)", "blam")
        self.assertLeadingExpr("Python", 0, "foo(bar,\nblam).spam<|>", "foo().spam")
        self.assertLeadingExpr("Python", 0, "foo.\\\nbar<|>", "foo.bar")
        self.assertLeadingExpr("Python", 0, "foo(1, # one\n2).bar<|>", "foo().bar")
        self.assertLeadingExpr("Python", 0, "foo(1, # o)ne\n2).bar<|>", "foo().bar")
        self.assertLeadingExpr("Python", 0, "foo(1, # (o)ne\n2).bar<|>", "foo().bar")
        self.assertLeadingExpr("Python", 0, "foo(1, # (one\n2).bar<|>", "foo().bar")
        self.assertLeadingExpr("Python", 0, "foo( #this is a ) comment\nb,d)<|>", "foo()")
        self.assertLeadingExpr("Python", 0, "foo\\\n(',({[', {one:1,two:2})<|>", "foo()")
    def test_getSimplifiedLeadingPythonExpr_extra(self):
        self.assertLeadingExpr("Python", 0, "if foo<|>(", "foo")
        self.assertLeadingExpr("Python", 0, "elif foo<|>(", "foo")
        self.assertLeadingExpr("Python", 0, "for foo<|>(", "foo")
        self.assertLeadingExpr("Python", 0, "while foo<|>(", "foo")
        self.assertLeadingExpr("Python", 0, "def foo<|>(", "foo")
        self.assertLeadingExpr("Python", 0, "class foo<|>(", "foo")
        self.assertLeadingExpr("Python", 0, "import foo<|>(", "foo")
        self.assertLeadingExpr("Python", 0, "from foo<|>(", "foo")
        self.assertLeadingExpr("Python", 0, "boo3 foo<|>(", "foo")
