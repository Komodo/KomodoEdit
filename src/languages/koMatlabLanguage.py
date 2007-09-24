from xpcom import components, ServerException

from koLanguageServiceBase import *

def registerLanguage(registery):
    registery.registerLanguage(koMatlabLanguage())
    registery.registerLanguage(koOctaveLanguage())
    
class koMatlabLanguage(KoLanguageBase):
    name = "Matlab"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{913BAE69-8E17-4c91-B855-687F0A34CFF6}"

    defaultExtension = ".m.matlab"
    commentDelimiterInfo = { "line": [ "%" ]  }

    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(components.interfaces.ISciMoz.SCLEX_MATLAB)
            self._lexer.setKeywords(0, self._keywords)
        return self._lexer

    _keywords = """break case catch continue else elseif end for
                function global if otherwise persistent return
                switch try while""".split()


class koOctaveLanguage(koMatlabLanguage):
    name = "Octave"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{d738c609-0897-4dbe-bfd4-d7037deb0ed2}"

    defaultExtension = ".m"

    _keywords = """break case catch continue do else elseif end
                end_unwind_protect endfor endif endswitch endwhile
                for function endfunction global if otherwise persistent
                return switch try until unwind_protect unwind_protect_cleanup
                while""".split()
