#!/usr/bin/env python
# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.


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
