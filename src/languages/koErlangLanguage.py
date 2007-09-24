from xpcom import components, ServerException

from koLanguageServiceBase import *

# Erlang info at http://www.erlang.org/

def registerLanguage(registery):
    registery.registerLanguage(koErlangLanguage())
    
class koErlangLanguage(KoLanguageBase):
    name = "Erlang"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{0153c47a-f668-41d4-8519-9ecd6b1c5ba0}"

    _stateMap = {
        'default': ('SCE_ERLANG_DEFAULT',),
        'comments': ('SCE_ERLANG_COMMENT',),
        'variables': ('SCE_ERLANG_VARIABLE',),
        'numbers': ('SCE_ERLANG_NUMBER',),
        'keywords': ('SCE_ERLANG_KEYWORD',),
        'strings': ('SCE_ERLANG_STRING',
                    'SCE_ERLANG_CHARACTER',),
        'operators': ('SCE_ERLANG_OPERATOR',),
        'functions': ('SCE_ERLANG_FUNCTION_NAME',),
        'macros': ('SCE_ERLANG_MACRO',),
        'records': ('SCE_ERLANG_RECORD',),
        'atoms': ('SCE_ERLANG_ATOM',),
        'separators': ('SCE_ERLANG_SEPARATOR',),
        'nodes': ('SCE_ERLANG_NODE_NAME',),
        'unknown': ('SCE_ERLANG_UNKNOWN',),
    }
    defaultExtension = '.erl'
    commentDelimiterInfo = {
        "line": [ "%" ],
    }
    
    sample = """-module(test).
-export([fac/1]).

fac(0) -> 1;
fac(N) -> N * fac(N-1).
"""
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(components.interfaces.ISciMoz.SCLEX_ERLANG)
            self._lexer.setKeywords(0, self._keywords)
        return self._lexer

    _keywords="""
        after begin case catch cond end fun if let of query receive when
        define record export import include include_lib ifdef ifndef else endif undef
        apply attribute call do in letrec module primop try""".split()
