#!/usr/bin/env python
# Copyright (c) 2010 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

from xpcom import components, ServerException

from koLanguageServiceBase import *

def registerLanguage(registery):
    registery.registerLanguage(koPowerProLanguage())

from xpcom import components, COMException, ServerException, nsError

class koPowerProLanguage(KoLanguageBase):
    name = "PowerPro"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{e0b08fa5-5db6-4a85-aacb-d44a19f5ce0e}"

    _stateMap = {
        'default': ('SCE_POWERPRO_DEFAULT',),
        'strings': ('SCE_POWERPRO_SINGLEQUOTEDSTRING',
                    'SCE_POWERPRO_DOUBLEQUOTEDSTRING',),
        'numbers': ('SCE_POWERPRO_NUMBER',),
        'comments': ('SCE_POWERPRO_COMMENTLINE',
                     'SCE_POWERPRO_COMMENTBLOCK',),
        'variables': ('SCE_POWERPRO_VERBATIM',),
        'keywords': ('SCE_POWERPRO_WORD',),
        'operators': ('SCE_POWERPRO_OPERATOR',),
        'functions': ('SCE_POWERPRO_FUNCTION',),
        'identifiers': ('SCE_POWERPRO_IDENTIFIER',),
    }
    defaultExtension = '.bar'
    
    sample = """No sample is available."""
    
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(
                components.interfaces.ISciMoz.SCLEX_POWERPRO)
            self._lexer.setKeywords(0, self._keywords)
        return self._lexer

    _keywords="""
    """.split()
