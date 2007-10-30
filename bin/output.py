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


# Fomatted output handling.

import sys, os

class FormattedOutput:
    def __init__(self, rightMargin=75, prefix=''):
        self.rightMargin = rightMargin
        self.prefix = prefix
        self.content = ''

    TT_WS, TT_NEWLINE, TT_WORD = range(3) # token types
    WHITESPACE = ' \t\r\f\v'  # excluding '\n' on purpose
    def parse(self, text):
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
  
    def wipeContent(self):
        """clear the current line (content)"""
        self.content = ''

    def writeLine(self):
        # the other content has already been written in self.add()
        sys.__stdout__.write('\n')
        self.wipeContent()

    def spaceLeft(self):
        return self.rightMargin - len(self.prefix + self.content)

    def add(self, ttype, token):
        """add a token to the current line content"""
        if not token:
            pass
        else:
            spaceLeft = self.spaceLeft()
            toadd = ''
            if ttype == self.TT_WS and len(token) > spaceLeft:
                # drop any whitespace beyond the right margin
                # tabs are evil, they are not handled gracefully here
                toadd = token[:spaceLeft]
            else:
                toadd = token
            # now have to write out the token and store it to the
            # current line (token)
            if not self.content:
                sys.__stdout__.write(self.prefix)
            sys.__stdout__.write(toadd)
            self.content = self.content + toadd

    def write(self, text):
        #sys.stderr.write('XXX write text:%s\n' % repr(text))
        tokens = self.parse(text)
        for ttype, token in tokens:
            #print 'XXX token:', ttype, repr(token)
            if ttype == self.TT_NEWLINE:
                self.writeLine()
            elif ttype == self.TT_WS:
                self.add(ttype, token)
            elif ttype == self.TT_WORD:
                #print 'XXX word:%s content:%s spaceLeft:%d' % (repr(token), repr(self.content), self.spaceLeft())
                if len(token) > self.spaceLeft():
                    #print 'XXX causes overflow'
                    if len(token) > self.rightMargin - len(self.prefix):
                        #print 'XXX break up word'
                        while token:
                            spaceLeft = self.spaceLeft()
                            piece, token = token[:spaceLeft], token[spaceLeft:]
                            #print 'XXX pieces:', repr(piece), repr(token)
                            self.add(ttype, piece)
                            if token:
                                self.writeLine()
                    else:
                        self.writeLine()
                        self.add(ttype, token)
                else:
                    self.add(ttype, token)

class MarkedUpOutput(FormattedOutput):
    def __init__(self, *args, **kwargs):
        FormattedOutput.__init__(self, *args, **kwargs)
        self.groupDepth = 0
        self.itemDepth = 0
        self._bullet = ''

    # understood types of markup
    MT_START_GROUP, MT_END_GROUP,\
        MT_START_ITEM, MT_END_ITEM,\
        MT_START_ERROR_ITEM, MT_END_ERROR_ITEM = range(6)
    def startGroup(self): self.markup(self.MT_START_GROUP)
    def endGroup(self): self.markup(self.MT_END_GROUP)
    def startItem(self): self.markup(self.MT_START_ITEM)
    def endItem(self): self.markup(self.MT_END_ITEM)
    def startErrorItem(self): self.markup(self.MT_START_ERROR_ITEM)
    def endErrorItem(self): self.markup(self.MT_END_ERROR_ITEM)

    def markup(self, mark):
        if mark == self.MT_START_GROUP:
            if self.content:
                self.writeLine()
            self.groupDepth = self.groupDepth + 1
            self.write(self.groupStartSeparator())
            self.prefix = '  ' + self.prefix
        elif mark == self.MT_END_GROUP:
            if self.content:
                self.writeLine()
            self.write(self.groupEndSeparator())
            self.prefix = self.prefix[2:]
            self.groupDepth = self.groupDepth - 1
        elif mark == self.MT_START_ITEM:
            if self.content:
                self.writeLine()
            self.itemDepth = self.itemDepth + 1
            self.write(self.itemStartSeparator())
            self.prefix = self.prefix + self.bullet()
        elif mark == self.MT_END_ITEM:
            if self.content:
                self.writeLine()
            self.write(self.itemEndSeparator())
            self.prefix = self.prefix[:len(self.prefix)-len(self.bullet())]
            self.itemDepth = self.itemDepth - 1
        elif mark == self.MT_START_ERROR_ITEM:
            if self.content:
                self.writeLine()
            self.prefix = self.prefix + '*** '
        elif mark == self.MT_END_ERROR_ITEM:
            if self.content:
                self.writeLine()
            self.prefix = self.prefix[:len(self.prefix)-len('*** ')]

    def bullet(self):
        bullets = ['o ', '- ']
        depth = max(0, self.itemDepth-1)
        if depth >= len(bullets):
            return bullets[len(bullets)-1]
        else:
            return bullets[depth]

    def groupStartSeparator(self):
        seps = [
            '='*(self.rightMargin - len(self.prefix)) + '\n',
            '-'*(self.rightMargin - len(self.prefix)) + '\n',
        ]
        depth = max(0, self.groupDepth-1)
        if depth >= len(seps):
            return seps[len(seps)-1]
        else:
            return seps[depth]

    def groupEndSeparator(self):
        seps = ['\n\n', '\n']
        depth = max(0, self.groupDepth-1)
        if depth >= len(seps):
            return seps[len(seps)-1]
        else:
            return seps[depth]

    def itemStartSeparator(self):
        return ''
    
    def itemEndSeparator(self):
        seps = ['\n', '']
        depth = max(0, self.itemDepth-1)
        if depth >= len(seps):
            return seps[len(seps)-1]
        else:
            return seps[depth]
    
    def writeLine(self):
        FormattedOutput.writeLine(self)
        # ensures that the bullets are blanked out after the first line
        self.prefix = ' '*len(self.prefix)


#---- a handy singleton for importing

markedUpOutput = MarkedUpOutput()
