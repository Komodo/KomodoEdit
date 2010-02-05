#!/usr/bin/env python
# Copyright (c) 2010 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

from xpcom import components, ServerException

from koLanguageServiceBase import *

def registerLanguage(registery):
    registery.registerLanguage(koNimrodLanguage())

from xpcom import components, COMException, ServerException, nsError

class koNimrodLanguage(KoLanguageBase):
    name = "Nimrod"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{edf6481c-4b58-4b7f-acde-4506eeaca77f}"

    _stateMap = {
        'default': ('SCE_P_DEFAULT',),
        'strings': ('SCE_P_STRING',
                    'SCE_P_CHARACTER',),
        'numbers': ('SCE_P_NUMBER',),
        'comments': ('SCE_P_COMMENTLINE',),
        'keywords': ('SCE_P_WORD',),
        'operators': ('SCE_P_OPERATOR',),
        'identifiers': ('SCE_P_IDENTIFIER',),
    }
    defaultExtension = '.nim'
    
    sample = """No sample is available."""
    
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(
                components.interfaces.ISciMoz.SCLEX_PYTHON)
            self._lexer.setKeywords(0, self._keywords)
        return self._lexer

    # http://force7.de/nimrod/manual.html#identifiers-keywords
    _keywords="""addr and as asm
bind block break
case cast const continue converter
discard distinct div
elif else end enum except
finally for from generic
if implies import in include is isnot iterator
lambda
macro method mod
nil not notin
object of or out
proc ptr
raise ref return
shl shr
template try tuple type
var
when while with without
xor
yield
    """.split()
