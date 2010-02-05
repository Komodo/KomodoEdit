#!/usr/bin/env python
# Copyright (c) 2010 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

from xpcom import components, ServerException

from koLanguageServiceBase import *

def registerLanguage(registery):
    registery.registerLanguage(koSorcusLanguage())

from xpcom import components, COMException, ServerException, nsError

class koSorcusLanguage(KoLanguageBase):
    name = "Sorcus"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{894c880d-0946-42fe-883e-c871d125b0de}"

    _stateMap = {
        'default': ('SCE_SORCUS_DEFAULT',),
        'strings': ('SCE_SORCUS_STRING',),
        'stringeol': ('SCE_SORCUS_STRINGEOL',),
        'numbers': ('SCE_SORCUS_NUMBER',),
        'comments': ('SCE_SORCUS_COMMENTLINE',),
        'keywords': ('SCE_SORCUS_COMMAND',),
        'operators': ('SCE_SORCUS_OPERATOR',),
        'variable': ('SCE_SORCUS_CONSTANT',),
        'identifiers': ('SCE_SORCUS_IDENTIFIER',
                        'SCE_SORCUS_PARAMETER',),
    }
    defaultExtension = '.sorcus'
    sample = """No sample is available."""
    
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(
                components.interfaces.ISciMoz.SCLEX_SORCUS)
            self._lexer.setKeywords(0, self._keywords)
        return self._lexer

    #
    _keywords="""
    """.split()
