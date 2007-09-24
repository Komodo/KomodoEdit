import os
import logging
import re

log = logging.getLogger("koSimpleLexer")
# XXX duplicated in codeintel.parseutil, present here to make this entirely
# independent

SKIPTOK = 0x01 # don't consider this a token that is to be considered a part of the grammar, like '\n'
MAPTOK = 0x02  # use the token associated with the pattern when it matches
EXECFN= 0x04   # execute the function associated with the pattern when it matches
USETXT = 0x08  # if you match a single character and want its ascii value to be the token

# Lexer class borrowed from the PyLRd project,
# http://starship.python.net/crew/scott/PyLR.html
class Lexer:
    eof = -1

    def __init__(self, filename=None):
        self.filename = filename
        self.tokenmap = {}
        self.prgmap = {}
        self.prglist = []
        self.lasttok = -1
        self.text = ""
        self.textindex = 0
        self.tokennum2name = {}

    def nexttok(self):
        self.lasttok = self.lasttok + 1
        return self.lasttok

    def settext(self, t):
        self.text = t
        self.textindex = 0

    def addmatch(self, prg, func=None, tokname="", attributes=MAPTOK|EXECFN):
        self.prglist.append(prg)
        tok = -2
        if not func:
            attributes = attributes & ~EXECFN
        if not tokname:
            attributes = attributes & ~MAPTOK
        if attributes & MAPTOK:
            self.tokenmap[tokname] = tok = self.nexttok()
        else:
            tok = self.nexttok()
        self.prgmap[prg] = tok, attributes, func
        self.tokennum2name[tok] = tokname

    def scan(self):
        x = ""
        for prg in self.prglist:
            #x = "TEXT TO MATCH {%s<|>%s}"% (self.text[self.textindex-10:self.textindex],self.text[self.textindex:self.textindex+20])
            #print x
            mo = prg.match(self.text, self.textindex)
            if not mo: 
                continue
            self.textindex = self.textindex + len(mo.group(0))
            tmpres = mo.group(0)
            t, attributes, fn = self.prgmap[prg]
            #log.info("'%s' token: %r", self.tokennum2name[t], tmpres)
            if attributes & EXECFN:
                try:
                    tmpres = apply(fn, (mo,))
                except Exception, e:
                    log.exception(e)
                    line = len(re.split('\r|\n|\r\n', self.text[:self.textindex]))
                    raise Exception("Syntax Error in lexer at file %s line %d positon %d text[%s]" % (self.filename, line, self.textindex, self.text[self.textindex:self.textindex+300]))
            if attributes & USETXT:
                t = ord(mo.group(0)[0])
            return (t, tmpres)
        if self.textindex >= len(self.text):
            return (self.eof, "")
        
        line = len(re.split('\r|\n|\r\n', self.text[:self.textindex]))
        raise Exception("Syntax Error in lexer at file %s line %d positon %d text[%s]" % (self.filename, line, self.textindex, self.text[self.textindex-20:self.textindex+300]))


# regular expressions used in parsing SGML related documents
class recollector:
    def __init__(self):
        self.res = {}
        self.regs = {}
        
    def add(self, name, reg, mods=None ):
        self.regs[name] = reg % self.regs
        #print "%s = %s" % (name, self.regs[name])
        if mods:
            self.res[name] = re.compile(self.regs[name], mods) # check that it is valid
        else:
            self.res[name] = re.compile(self.regs[name]) # check that it is valid
