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

"""
 USAGE: python wraptext.py <infile> <outfile>

 Wrap the text of the given input file at 77 columns and spit it out to the
 given output file.
"""

import sys, os

#---- word wrapping support (stolen from tmOutput.py)
class OutputError(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg

class FormattedOutput:
    """Controlled word-wrapping and indentation of output.
 
    Interface:
        "write" method
        "wordWrapping" boolean attribute
        "indent" and "dedent" methods

    Examples (passing "out=sys.stdout" is only required for doctest'ing) :
        >>> import tmOutput
        >>> out = tmOutput.FormattedOutput(out=sys.stdout)
        >>> out.write("A bunch of text that will get word wrapped at the default 75 columns.\\n")
        A bunch of text that will get word wrapped at the default 75 columns.
        >>> out.write("00  5 7   10  5 7   20  5 7   30  5 7   40  5 7   50  5 7   60  5 7   70  5 7   80\\n")
        00  5 7   10  5 7   20  5 7   30  5 7   40  5 7   50  5 7   60  5 7   70  5
        7   80
        >>> out.write("Note that\\n newlines are\\nstill  properly observed.\\n")
        Note that
         newlines are
        still  properly observed.
        >>> out.write("And_if_you_have_one_long_word_without_spaces_then_it_will_be_broken_at_the_margin_boundary.\\n")
        And_if_you_have_one_long_word_without_spaces_then_it_will_be_broken_at_the_
        margin_boundary.
        >>> # you can also temporarily turn word wrapping off
        ...
        >>> out.wordWrapping = 0
        >>> out.write("00  5 7   10  5 7   20  5 7   30  5 7   40  5 7   50  5 7   60  5 7   70  5 7   80\\n")
        00  5 7   10  5 7   20  5 7   30  5 7   40  5 7   50  5 7   60  5 7   70  5 7   80
        >>> out.wordWrapping = 1
        >>>
    """
    def __init__(self, rightMargin=75, indentString=' '*4,
                 wordWrapping=1, out=sys.__stdout__):
        self._rightMargin = rightMargin
        self.__indentString = indentString
        self.__indentation = []
        self.wordWrapping = wordWrapping
        self.out = out
        self.content = ''

    def close(self):
        # do nothing: This outputter does not own the stream that it is
        # writing to.
        pass

    # indentations are maintained in an ordered list which is joined before
    # printing
    def indent(self, indentString=None):
        if indentString is None:
            indentString = self.__indentString
        self.__indentation.append(indentString)
    def dedent(self):
        if len(self.__indentation) > 0:
            indentString = self.__indentation.pop()
        else:
            indentString = None
        return indentString
    def _GetIndentation(self):
        return "".join(self.__indentation)

    TT_WS, TT_NEWLINE, TT_WORD = range(3) # token types
    WHITESPACE = ' \t\r\f\v'  # excluding '\n' on purpose
    def _Parse(self, text):
        """return a list of tuples (TOKEN_TYPE, <token>)"""
        tokens = []
        i = 0
        while i < len(text):
            ch = text[i]
            if ch in ['\n']:
                tokens.append((self.TT_NEWLINE, ch))
                i = i + 1
            elif ch in self.WHITESPACE:
                spaces = ''
                while i < len(text) and text[i] in self.WHITESPACE:
                    spaces = spaces + text[i]
                    i = i + 1
                tokens.append((self.TT_WS, spaces))
            else:
                word = ''
                while i < len(text) and text[i] not in self.WHITESPACE+'\n':
                    word = word + text[i]
                    i = i + 1
                tokens.append((self.TT_WORD, word))
        return tokens
  
    def _WipeContent(self):
        """clear the current line (content)"""
        self.content = ''

    def _WriteLine(self):
        # the other content has already been written in self._Add()
        self.out.write('\n')
        self._WipeContent()

    def _SpaceLeft(self):
        return self._rightMargin - len(self._GetIndentation() + self.content)

    def _Add(self, ttype, token):
        """add a token to the current line content"""
        if not token:
            pass
        else:
            spaceLeft = self._SpaceLeft()
            toadd = ''
            if self.wordWrapping and ttype == self.TT_WS and \
              len(token) > spaceLeft:
                # drop any whitespace beyond the right margin
                # tabs are evil, they are not handled gracefully here
                toadd = token[:spaceLeft]
            else:
                toadd = token
            # now have to write out the token and store it to the
            # current line (token)
            if not self.content:
                self.out.write(self._GetIndentation())
            self.out.write(toadd)
            self.content = self.content + toadd

    def write(self, text):
        #sys.stderr.write('XXX write text:%s\n' % repr(text))
        tokens = self._Parse(text)
        for ttype, token in tokens:
            #print 'XXX token:', ttype, repr(token)
            if ttype == self.TT_NEWLINE:
                self._WriteLine()
            elif ttype == self.TT_WS:
                self._Add(ttype, token)
            elif ttype == self.TT_WORD:
                #print 'XXX word:%s content:%s spaceLeft:%d' % (repr(token), repr(self.content), self._SpaceLeft())
                if self.wordWrapping and len(token) > self._SpaceLeft():
                    #print 'XXX causes overflow'
                    if len(token) > self._rightMargin - len(self._GetIndentation()):
                        #print 'XXX break up word'
                        while token:
                            spaceLeft = self._SpaceLeft()
                            piece, token = token[:spaceLeft], token[spaceLeft:]
                            #print 'XXX pieces:', repr(piece), repr(token)
                            self._Add(ttype, piece)
                            if token:
                                self._WriteLine()
                    else:
                        self._WriteLine()
                        self._Add(ttype, token)
                else:
                    self._Add(ttype, token)



#---- script mainline
# process the command line
if len(sys.argv) < 3:
    sys.stderr.write("%s: error: invalid number of args\n" % sys.argv[0])
    sys.stderr.write(sys.modules["__main__"].__doc__)
    sys.exit(1)
inFileName, outFileName = sys.argv[1:]
if inFileName == outFileName:
    sys.stderr.write("%s: error: Can't handle in-place wrapping.\n" %\
        sys.argv[0])

# process file
fin = open(inFileName, "r")
fout = open(outFileName, "w")

wrapped = FormattedOutput(out=fout)
for line in fin.readlines():
    wrapped.write(line)

fin.close()
fout.close()

