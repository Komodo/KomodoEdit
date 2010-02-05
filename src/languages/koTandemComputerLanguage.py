#!/usr/bin/env python
# Copyright (c) 2010 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

from xpcom import components, ServerException

from koLanguageServiceBase import *

def registerLanguage(registery):
    registery.registerLanguage(koTACLLanguage())
    registery.registerLanguage(koTALLanguage())

from xpcom import components, COMException, ServerException, nsError

class _koTandemComputerLanguage(KoLanguageBase):
    _stateMap = {
        'default': ('SCE_C_DEFAULT',),
        'strings': ('SCE_C_STRING', 'SCE_C_CHARACTER',),
        'numbers': ('SCE_C_NUMBER',),
        'comments': ('SCE_C_COMMENT', 'SCE_C_COMMENTLINE',
                     'SCE_C_COMMENTDOC',),
        'keywords': ('SCE_C_WORD',),
        'operators': ('SCE_C_OPERATOR',),
        'identifiers': ('SCE_C_IDENTIFIER',),
    }
    sample = """No sample is available."""
    
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(self.scimozLexer)
            self._lexer.setKeywords(0, self._keywords)
        return self._lexer

    #
    _keywords="""
    """.split()
    
class koTACLLanguage(_koTandemComputerLanguage):
    name = "TACL"
    _reg_clsid_ = "{e16a35cf-3481-4c9c-9bb4-c70baba79fd5}"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    defaultExtension = '.tacl'
    scimozLexer = components.interfaces.ISciMoz.SCLEX_TACL

class koTALLanguage(_koTandemComputerLanguage):
    name = "TAL"
    _reg_clsid_ = "{491b9764-9cb3-4303-80ae-dcc11c52dc18}"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    defaultExtension = '.tal'
    scimozLexer = components.interfaces.ISciMoz.SCLEX_TAL
