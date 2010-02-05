#!/usr/bin/env python
# Copyright (c) 2010 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

from xpcom import components, ServerException

from koLanguageServiceBase import *

def registerLanguage(registery):
    registery.registerLanguage(koMarkdownLanguage())

from xpcom import components, COMException, ServerException, nsError

class koMarkdownLanguage(KoLanguageBase):
    name = "Markdown"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{6bb5154a-4e58-4778-8dbb-a550c3830769}"

    _stateMap = {
        'default': ('SCE_MARKDOWN_DEFAULT',),
        'strings': ('SCE_MARKDOWN_STRONG1',
                    'SCE_MARKDOWN_STRONG2',
                    'SCE_MARKDOWN_EM1',
                    'SCE_MARKDOWN_EM2',
                    ),
        'numbers': ('SCE_MARKDOWN_BLOCKQUOTE',
                      'SCE_MARKDOWN_STRIKEOUT',
                      'SCE_MARKDOWN_HRULE',
                      'SCE_MARKDOWN_LINK',
                      ),
        'comments': ('SCE_MARKDOWN_HEADER1',
                     'SCE_MARKDOWN_HEADER2',
                     'SCE_MARKDOWN_HEADER3',),
        'variables': ('SCE_MARKDOWN_HEADER4',
                     'SCE_MARKDOWN_HEADER5',
                     'SCE_MARKDOWN_HEADER6',),
        'keywords': ('SCE_MARKDOWN_PRECHAR',),
        'operators': ('SCE_MARKDOWN_ULIST_ITEM',
                      'SCE_MARKDOWN_OLIST_ITEM'
                      ),
        'functions': ('SCE_MARKDOWN_LINE_BEGIN',),
        'macros': ('SCE_MARKDOWN_CODE',
                   'SCE_MARKDOWN_CODE2',
                   ),
        'identifiers': ('SCE_MARKDOWN_CODEBK',),
    }
    defaultExtension = '.mdml'
    commentDelimiterInfo = {"line": [ ";" ]}
    
    sample = """No sample is available."""
    
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(
                components.interfaces.ISciMoz.SCLEX_MARKDOWN)
            self._lexer.setKeywords(0, self._keywords)
        return self._lexer

    # These keywords are commands
    _keywords="""
    """.split()
