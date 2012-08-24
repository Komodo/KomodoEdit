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

# Reflow code -- used by koLanguageCommandHandler, but in
# a standalone file to make usable by doctest.

r"""
>>> sreflow("This is a long paragraph which is useful in testing reflow\n", 30, '\n')
'This is a long paragraph which\nis useful in testing reflow\n'
>>> tst = "tomato\n\nbar\n\nasdas\n"
>>> sreflow(tst, 30, '\n')
'tomato\n\nbar\n\nasdas\n'
>>> tst = "tomato\n\nbar\n\nasdas "
>>> sreflow(tst, 30, '\n')
'tomato\n\nbar\n\nasdas '
>>> tst = "  Susan: I assume that would push out our release date, though, right?\r\n\r\n  Tom: What? No, no, absolutely not. In fact, I've been building a prototype just to get a feel for it, and I'm pretty sure that we could have an alpha out earlier than what we've currently got planned.\r\n\r\n  Susan: Why earlier?"
>>> sreflow(tst, 40, '\n')
"  Susan: I assume that would push out\n  our release date, though, right?\n\r\n  Tom: What? No, no, absolutely not. In\n  fact, I've been building a prototype\n  just to get a feel for it, and I'm\n  pretty sure that we could have an\n  alpha out earlier than what we've\n  currently got planned.\n\r\n  Susan: Why earlier?"
>>> tst = "# - get PySQLite into our silo'd Python and make it easy for dev builders\n#   on all platforms\n# - what mechanism to use to change code browser fileset?\n# - What about cleaning out info from the DB for deleted files?\n#   Perhaps that can be done lazily when looking up symbols? I.e.\n#   when about to report a symbol that comes from a file, check\n#   that that file still exists. That might be too slow. Perhaps\n#   the logic could be: check that the file still exists if we ..."

>>> print tst
# - get PySQLite into our silo'd Python and make it easy for dev builders
#   on all platforms
# - what mechanism to use to change code browser fileset?
# - What about cleaning out info from the DB for deleted files?
#   Perhaps that can be done lazily when looking up symbols? I.e.
#   when about to report a symbol that comes from a file, check
#   that that file still exists. That might be too slow. Perhaps
#   the logic could be: check that the file still exists if we ...
>>> p = Paragraphize(tst)
>>> len(p)
3
>>> print sreflow(tst, 40, '\n')
# - get PySQLite into our silo'd Python
#   and make it easy for dev builders on
#   all platforms
# - what mechanism to use to change code
#   browser fileset?
# - What about cleaning out info from
#   the DB for deleted files? Perhaps
#   that can be done lazily when looking
#   up symbols? I.e. when about to
#   report a symbol that comes from a
#   file, check that that file still
#   exists. That might be too slow.
#   Perhaps the logic could be: check
#   that the file still exists if we ...
>>> email = '    > This is a really really really really really really really really long sentence\n    > and this is the next line.'
>>> print sreflow(email, 40, '\n')
    > This is a really really really
    > really really really really really
    > long sentence and this is the next
    > line.
>>> homer = u"The other instances in Homer of double names in the language of men and gods are 2.813 \u03c4\u1f74\u03bd \u1f26 \u03c4\u03bf\u03b9 \u1f04\u03bd\u03b4\u03c1\u03b5\u03c2 \u0392\u03b1\u03c4 end!"
>>> print repr(reflow(homer, 40, '\n'))
u'The other instances in Homer of double\nnames in the language of men and gods\nare 2.813 \u03c4\u1f74\u03bd \u1f26 \u03c4\u03bf\u03b9 \u1f04\u03bd\u03b4\u03c1\u03b5\u03c2 \u0392\u03b1\u03c4 end!'
>>> print repr(reflow(homer, 20, '\n'))
u'The other instances\nin Homer of double\nnames in the\nlanguage of men and\ngods are 2.813 \u03c4\u1f74\u03bd \u1f26\n\u03c4\u03bf\u03b9 \u1f04\u03bd\u03b4\u03c1\u03b5\u03c2 \u0392\u03b1\u03c4 end!'
>>> embedded_non_breaking_space = u"abcdefgh1 abcdefgh2 abcdefgh3\xa0abcdefgh4\xa0abcdefgh5 abcdefgh6"
>>> print repr(reflow(embedded_non_breaking_space, 35, '\n'))
u'abcdefgh1 abcdefgh2\nabcdefgh3\xa0abcdefgh4\xa0abcdefgh5\nabcdefgh6'
"""

import re
import sys

TABWIDTH = 8

class Line(unicode):
    r"""Line objects are "smart" wrappers around lines.  They know about
    all of the indentation-related semantics of the line, such as:
      - whether the line is all whitespace or not
      - what the whitespace indent of the line is
      - whether the line starts w/ a bullet
      - if the line starts with a bullet, what the indent corresponding
        to the space "after" the bullet is.
        
    >>> t = Line("   * and so on")
    >>> t.iswhitespace
    False
    >>> t.bulleted
    True
    >>> t.indentWidths
    [3, 5]
    >>> t.leadingIndent
    '   '
    >>> t.leadingIndentWidth
    3
    >>> t = Line('\n')
    >>> t.iswhitespace
    True
    >>> t = Line('   # foobar')
    >>> t.iscomment
    True
    >>> t.uncomment()
    u'foobar'
    >>> line1 = Line("# - get PySQLite into our silo'd Python and make it easy for dev builders\n")
    >>> line2 = Line("#   on all platforms\n")
    >>> line1.iscomment
    True
    >>> line2.iscomment
    True
    >>> line1.leadingIndent
    '# '
    >>> line2.leadingIndent
    '#   '
    >>> line1.indentWidths
    [2, 4]
    """
    def __init__(self, line):
        unicode.__init__(line)
        self._line = line
        self.iswhitespace = not line.strip()
        self.indentWidths = []
        self.iscode, self.codeIndent = findcode(line)
        if self.iscode:
            self.iscomment = False
            self.bulleted = False
        self.iscomment, self.commentIndent = findcomment(line)
        if self.iscomment:
            self.bulleted, self.bullet = findbullet(line[len(self.commentIndent):])
            self.leadingIndent = self.commentIndent
        else:
            self.bulleted, self.bullet = findbullet(line)
            self.leadingIndent = line[:len(line)-len(line.lstrip())]
        self.leadingIndentWidth = len(self.leadingIndent)
        if self.bulleted:
            if self.iscomment:
                self.indentWidths = [self.leadingIndentWidth, len(self.commentIndent) + len(self.bullet)]
            else:
                self.indentWidths = [self.leadingIndentWidth, len(self.bullet)]
        else:
            self.indentWidths = [self.leadingIndentWidth]
    def uncomment(self):
        line = Line(self._line[len(self.commentIndent):])
        line.iscomment = self.iscomment
        line.leadingIndent = self.leadingIndent
        return line
    def _strip(self):
        if self.iscode:
            return unicode(self)
        if self.bulleted:
            return self[len(self.bullet):].rstrip()
        else:
            return self[len(self.leadingIndent):].rstrip()
    def __str__(self):
        return unicode(self._line)

bulletRe = re.compile("(\s*?[\*%-]\s+)(.*)")

def findbullet(line):
    r"""Return a tuple of (bulleted, bullet) where bulleted is true or false.
    If 'bullet' is true, then the second argument is the bullet part of the
    'line' string, including any whitespace between the bullet and the beginning of the text
    
    >>> findbullet("foo asd as")
    (False, 'foo asd as')
    >>> findbullet("   * so")
    (True, '   * ')
    >>> findbullet('- - - ')
    (True, '- ')
    >>> findbullet('   * and so on')
    (True, '   * ')
    """
    match = bulletRe.match(line)
    if match:
        return True, match.groups(1)[0]
    else:
        return False, line

# Match email lines that start with ">", ">>" or "> >" but not python prefixes
# like ">>>"

commentRe = re.compile("(\s*?(?:\/\*|(?:#+)|(?:>)|(?:>>)|(?:> >)|(?://+)|(?:--))(?!>)\s*)(.*)")
def findcomment(line):
    r"""Return a tuple of (iscomment, commentIndent) where 'iscomment' is true
    or false depending on whether the current line is prefixed by a comment
    marker (typically '#', '//', '/*' or '*').
    
    If 'iscomment' is true, then the second argument is the indent up to and
    including the whitespace after the comment marker
    
    >>> findcomment("foo asd as")
    (False, 'foo asd as')
    >>> findcomment("   /* so")
    (True, '   /* ')
    >>> findcomment('    #  tomato')
    (True, '    #  ')
    >>> findcomment('    ###  tomato')
    (True, '    ###  ')
    >>> findcomment('    //  tomato')
    (True, '    //  ')
    >>> findcomment('    >>>  tomato')
    (False, '    >>>  tomato')
    >>> findcomment('    > tomato')
    (True, '    > ')
    """
    match = commentRe.match(line)
    if match:
        return True, match.groups(1)[0]
    else:
        return False, line

codeRe = re.compile("(\s*?)(?:>>>\s)|(?:\.\.\.\s)")
def findcode(line):
    r"""Return a tuple of (iscode, codeIndent) where 'iscode' is true
    or false depending on whether the current line is recognized as likely
    to be inline code.
    
    If 'iscode' is true, then 'codeIndent' is the indent up to and
    including the first non-whitespace character.
    
    If iscode is false, then 'codeIndent' is the whole line.
    
    >>> findcode("foo asd as")
    (False, 'foo asd as')
    >>> findcode("   >>> x = 3")
    (True, '   ')
    """
    match = codeRe.match(line)
    if match:
        return True, match.groups(1)[0]
    else:
        return False, line

class Para(list):
    r"""
    >>> x = Para(Line('  * '))
    >>> x[0]
    u'  * '
    >>> type(x[0])
    <class 'reflow.Line'>
    >>> x[0].indentWidths
    [2, 4]
    
    # Paragraphs accept only lines congruent with their contents
    >>> p = Para(Line("No indentation"))
    >>> p.accept(Line("   Indentation"))
    False
    >>> p.accept(Line("but no indent is ok"))
    True
    >>> p.accept(Line("    "))  # should fail
    False
    >>> b = Para(Line("  * this is a bullleted line"))
    >>> l = Line("    which accepts a line which is indented accordingly")
    >>> b.accept(l)
    True
    >>> b.append(l)
    >>> l = Line("    and so on and so on and so on")
    >>> b.append(l)
    >>> b.reflow(30, '\n')
    >>> [str(x) for x in b]
    ['  * this is a bullleted line\n', '    which accepts a line which\n', '    is indented accordingly\n', '    and so on and so on and so\n', '    on']
    
    # now test the handling of comments
    >>> tst = " # - this is\n #   a test"
    >>> x = Paragraphize(tst)
    >>> len(x)
    1
    >>> x[0]
    [u' # - this is\n', u'a test']
    >>> x[0].reflow(10, '\n')
    >>> x
    [[u' # - this\n', u' #   is a\n', u' #   test']]
    """
    def __init__(self, line):
        list.__init__(self)
        list.append(self, line)
        self.iswhitespace = not line.strip()
    def accept(self, line):
        # code paragraphs always accept code lines.
        if line.iscode and self[0].iscode:
            return True
        # bullets always start new paragraphs
        if line.bulleted:
            return False
        # whitespace lines always start a new paragraph
        if line.iswhitespace:
            return False
        # non-whitespace lines start paragraphs if the current
        # paragraph is a whitespace paragraph
        if self[-1].iswhitespace:
            return False
        # lines with congruent indentation are accepted
        if line.indentWidths[0] in self[0].indentWidths:
            return True
        return False
    def reflow(self, width, eol):
        if self[-1].endswith(' ') or self[-1].endswith('\t'):
            trail = self[-1][-1]
        else:
            trail = ''
        logical_line = Line(self[0].rstrip())
        for line in self[1:]:
            logical_line += ' ' + line.strip()
        NEWLINE = None
        if self[-1].endswith(eol):
            NEWLINE = eol
        if self[0].iscomment:
            if self[0].bulleted:
                first_indent = self[0].leadingIndent + self[0].bullet
                other_indents = self[0].leadingIndent + ' ' * len(self[0].bullet)
            else:
                first_indent = other_indents = self[0].leadingIndent
        else:
            if self[0].bulleted:
                first_indent = self[0].bullet
                other_indents = ' ' * len(self[0].bullet)
            else:
                first_indent = other_indents = self[0].leadingIndent
        lineNo = 0
        lines = []
        # See Komodo bug 83764 -- reflow breaks non-breakable spaces and
        # Python bug 6537 -- string.split breaks non-breakable spaces
        # The Python bug is rejected -- owner says to use textwrap
        # Our problem is more complex, so this code hides non-breaking
        # spaces from string.split.
        # Note: If I use re.split([\r\n \t]+), extra newlines get added
        # to the end of the text.
        breakable_parts = logical_line[len(first_indent):].split(u"\xa0")
        words = []
        for bp in breakable_parts:
          new_words = bp.split()
          if words:
            words[-1] += u"\xa0"
            if new_words:
              words[-1] += new_words[0]
              del new_words[0]
          words += new_words
        if not words: return
        curLine = first_indent + words[0]
        for word in words[1:]:
            if len(word) + len(curLine) + 1 <= width:  # 1 for space
                curLine += ' ' + word
                continue
            # exceeded the length
            lines.append(curLine + eol)
            curLine = other_indents + word
        if NEWLINE:
            curLine += NEWLINE
        lines.append(curLine+trail)
        self[:] = [Line(line) for line in lines]
    def _strip(self):
        """Remove string markup or comment markup"""
        return ''.join([line._strip() for line in self])
    
    def htmlify(self, htmlbuffer, htmlcontext):
        stripped = self._strip()
        if not stripped:
            return
        lastIndent = htmlcontext.currentIndentWidth
        currentIndent = self[0].indentWidths[-1]
        dontCompareIndents = False
        if self[0].iscode and not htmlcontext.inPRE:
            htmlbuffer.write('<pre>\n')
            htmlbuffer.write(''.join(self))
            htmlcontext.inPRE = True
            return
        if not self[0].iscode and htmlcontext.inPRE:
            htmlbuffer.write('</pre>\n')
            htmlcontext.inPRE = False
        if self[0].bulleted and not htmlcontext.inUL:
            # we need to switch on to a bulleted list context
            htmlbuffer.write('<ul>')
            dontCompareIndents = True
            htmlcontext.inUL = True
        elif not self[0].bulleted and htmlcontext.inUL:
            htmlbuffer.write('</ul>')
            htmlcontext.inUL = False
        if not dontCompareIndents:
            if lastIndent < currentIndent:
                # we need to push an indent
                htmlbuffer.write('<dl>')
                htmlcontext.inDL = True
            if lastIndent > currentIndent:
                # we need to pop an indent
                htmlbuffer.write('</dl>')
                htmlcontext.inDL = False
        htmlcontext.currentIndentWidth = currentIndent
        if htmlcontext.inUL:
            htmlbuffer.write('<li>')
        if htmlcontext.inDL:
            htmlbuffer.write('<dt/><dd>')
        htmlbuffer.write('<p>' + stripped + '</p>\n')
        if htmlcontext.inDL:
            htmlbuffer.write('</dd>')
        if htmlcontext.inUL:
            htmlbuffer.write('</li>')

class Paragraphize(list):
    def __init__(self, text):
        r"""Given a text, return 1 or more paragraph objects, where
        a paragraph is defined for 'reflow' purposes, thus:
          - a line consisting only of whitespace is its own
            paragraph and is a marker of a paragraph end.
          - a line starting with a 'bullet' is a paragraph beginning.

        >>> print Paragraphize("Foo\nbar\n\nbaz")
        [[u'Foo\n', u'bar\n'], [u'\n'], [u'baz']]
        >>> print Paragraphize("this\n   \nis\n")
        [[u'this\n'], [u'   \n'], [u'is\n']]

        >>> tst =  '''Given a text, return 1 or more paragraph objects, where\na paragraph is defined for 'reflow' purposes, thus:\n'''
        >>> f = Paragraphize(tst)
        >>> f[0]
        [u'Given a text, return 1 or more paragraph objects, where\n', u"a paragraph is defined for 'reflow' purposes, thus:\n"]
        >>> [para.reflow(40, '\n') for para in f]
        [None]
        >>> f[0]
        [u'Given a text, return 1 or more paragraph\n', u'objects, where a paragraph is defined\n', u"for 'reflow' purposes, thus:\n"]
        >>> tst2 =  '''foo, where\na paragraph is defined for 'reflow' purposes, thus:\n  - this is a test\n'''
        >>> tst2
        "foo, where\na paragraph is defined for 'reflow' purposes, thus:\n  - this is a test\n"
        >>> g = Paragraphize(tst2)
        >>> g[0]
        [u'foo, where\n', u"a paragraph is defined for 'reflow' purposes, thus:\n"]
        >>> g[1]
        [u'  - this is a test\n']
        >>> [para.reflow(40, '\n') for para in g]
        [None, None]
        >>> g[0]
        [u'foo, where a paragraph is defined for\n', u"'reflow' purposes, thus:\n"]


        >>> tst =  '''Given a text, return 1 or more paragraph objects, where\na paragraph is defined for 'reflow' purposes, thus:\n  - a line consisting only of whitespace is its own\n    paragraph and is a marker of a paragraph end.\n  - a line starting with a 'bullet' is a paragraph beginning.\n'''
        >>> f = Paragraphize(tst)
        >>> [para.reflow(40, '\n') for para in f]
        [None, None, None]
        >>> for para in f:
        ...     print ''.join(para),
        ...
        Given a text, return 1 or more paragraph
        objects, where a paragraph is defined
        for 'reflow' purposes, thus:
          - a line consisting only of whitespace
            is its own paragraph and is a marker
            of a paragraph end.
          - a line starting with a 'bullet' is a
            paragraph beginning.

        and now with tabs:

        >>> tst =  '''Given a text, return 1 or more paragraph objects, where\na paragraph is defined for 'reflow' purposes, thus:\n\t  - a line consisting only of whitespace is its own\n\t    paragraph and is a marker of a paragraph end.\n  - a line starting with a 'bullet' is a paragraph beginning.\n'''
        >>> f = Paragraphize(tst)
        >>> [para.reflow(30, '\n') for para in f]
        [None, None, None]
        >>> for para in f:
        ...     print ''.join(para),
        ...
        Given a text, return 1 or more
        paragraph objects, where a
        paragraph is defined for
        'reflow' purposes, thus:
                  - a line consisting
                    only of whitespace
                    is its own
                    paragraph and is a
                    marker of a
                    paragraph end.
          - a line starting with a
            'bullet' is a paragraph
            beginning.
            
        >>> tst = "tomato\ncucumber\n\nbar\n\nasdas\n"
        >>> f = Paragraphize(tst)
        >>> print f
        [[u'tomato\n', u'cucumber\n'], [u'\n'], [u'bar\n'], [u'\n'], [u'asdas\n']]
        >>> junk = [para.reflow(30, '\n') for para in f]
        >>> print f
        [[u'tomato cucumber\n'], [u'\n'], [u'bar\n'], [u'\n'], [u'asdas\n']]
        >>> tst = "    Foo: bar\n\n    Baz: tomato\n\n    Cucumber: vegetable"
        >>> f = Paragraphize(tst)
        >>> f[0]
        [u'    Foo: bar\n']
        >>> f[2]
        [u'    Baz: tomato\n']
        >>> f[2].reflow(30, '\n')
        >>> f[2]
        [u'    Baz: tomato\n']

        # the following tests handling of paragraphs following blank paragraphs
        >>> tst = '''    Sam: Sounds right. Make sure you don't get a rabid anti-capitalist, though.\n\n    Tom: Right - I hear IBM and Nokia are hotbeds of rabid anti-capitalism.\n\n    Susan: Please get someone who washes and wears shoes.'''
        >>> f = Paragraphize(tst)
        >>> len(f)
        5
        """
        list.__init__(self)
        # convert to Line objects (they know all we need to know about themselves
        lines = text.expandtabs(TABWIDTH).splitlines(1)
        lines = [Line(line) for line in lines]
        if not lines: return # no text
        currentPara = Para(lines[0])
        self.append(currentPara)
        for line in lines[1:]:
            if currentPara.accept(line):
                if line.iscomment:
                    line = Line(line.uncomment())
                currentPara.append(line)
            else:
                currentPara = Para(line)
                self.append(currentPara)

def reflow(text, width, eol):
    paragraphs = Paragraphize(text)
    [para.reflow(width, eol) for para in paragraphs]
    reflowed = ''.join([''.join(para) for para in paragraphs])
    return reflowed

# For doctests only
def sreflow(*args):
    return str(reflow(*args))
    
class HTMLContext:
    inDL = False
    inUL = False
    inPRE = False
    currentIndentWidth = 0

def htmlify(text):
    r""" Given a chunk of text (a python docstring or a comment), return
    an HTML fragment that corresponds to it, converting 'implied' paragraphs
    to <p>...</p> blocks, bullets to bulleted lists, bold and italic
    markup to corresponding code.  A very lightweight rst2html, in other words.
    
    >>> htmlify('''foo''')
    '<p>foo</p>\n'
    >>> htmlify('''This is a first line\n\nThis is a second line.''')
    '<p>This is a first line</p>\n<p>This is a second line.</p>\n'
    
    >>> txt = '''First paragraph\n\nSecond paragraph.\n\n    Indented paragraph\n\n    >>> x = 3\n    >>> and so on\n\nBack to first indent.\n\n    * First bullet\n\n    * Second bullet\n\nBack to first indent.'''
    >>> htmlify(txt)
    '<p>First paragraph</p>\n<p>Second paragraph.</p>\n<dl><dt/><dd><p>Indented paragraph</p>\n</dd><pre>\n    >>> x = 3\n    >>> and so on\n</pre>\n</dl><p>Back to first indent.</p>\n<ul><li><p>First bullet</p>\n</li><li><p>Second bullet</p>\n</li></ul></dl><p>Back to first indent.</p>\n'
    """
    paragraphs = Paragraphize(text)
    htmlcontext = HTMLContext()
    import cStringIO
    buffer = cStringIO.StringIO()
    
    [paragraph.htmlify(buffer, htmlcontext) for paragraph in paragraphs]
    return buffer.getvalue()

def _test():
    import doctest, reflow
    print "...testing doctests..."
    return doctest.testmod(reflow)

if __name__ == '__main__':
    _test()

if 0:
    import sys
    if len(sys.argv) == 2:
        fname = sys.argv[1]
        text  = open(fname).read()
        html = htmlify(text)
        open(fname +'.html', 'w').write(html)
        
    elif len(sys.argv) >= 3:
        fname, lineNo = sys.argv[1:3]
        lineNo = int(lineNo)
        lines = open(fname).readlines()
        docstringlines = []
        inDocString = False
        for line in lines[lineNo:]:
            if line.find('"""') != -1:  # found it
                if not inDocString:
                    docstringlines.append(line[line.find('"""')+3:])
                    inDocString = True
                    continue
                else:
                    docstringlines.append(line[:line.find('"""')])
                    text = ''.join(docstringlines)
                    html = htmlify(text)
                    sys.stdout.write(html)
                    sys.exit(0)
                    break
            else:
                if not inDocString:
                    continue
                else:
                    docstringlines.append(line)
