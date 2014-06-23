# Registers the LaravelBlade language in Komodo.

import logging
from koXMLLanguageBase import koHTMLLanguageBase
from koLanguageKeywordBase import KoLanguageKeywordBase
import koLanguageServiceBase
from xpcom import components

log = logging.getLogger("koLaravelBladeLanguage")
#log.setLevel(logging.DEBUG)

def registerLanguage(registry):
    log.debug("Registering language LaravelBlade")
    registry.registerLanguage(KoLaravelBladeLanguage())

_sci_constants = components.interfaces.ISciMoz

class KoLaravelBladeLanguage(koHTMLLanguageBase, KoLanguageKeywordBase):

    # ------------ Komodo Registration Information ------------ #

    name = "LaravelBlade"
    lexresLangName = "LaravelBlade"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" % name
    _reg_categories_ = [("komodo-language", name)]
    _reg_clsid_ = "63214a00-1e70-4100-a655-f496e156a618"

    primary = 1
    defaultExtension = '.blade.php'

    supportsSmartIndent = "keyword"

    # ------------ Sub-language Controls ------------ #

    lang_from_udl_family = {'SSL': 'PHP', 'M': 'HTML', 'CSS':'CSS', 'CSL':'JavaScript'}
    
    _indenting_statements = ['@for', '@while', '@if', '@foreach', '@else', '@elseif', '@section', '@unless']
    _dedenting_statements = []
    _keyword_dedenting_keywords = """@endfor @endforeach @endwhile @else @elseif @endif
    @endforelse @endunless @endsection @yield_section 
                """.split()

    def __init__(self):
        koHTMLLanguageBase.__init__(self)
        # koHTMLLanguageBase already called the language superclass,
        # so KoLanguageKeywordBase doesn't need to.
        KoLanguageKeywordBase.__init__(self, call_super=False)
        self._dedent_style_info = \
            koLanguageServiceBase.koLangSvcStyleInfo(_default_styles=[_sci_constants.SCE_UDL_M_DEFAULT,
                                              _sci_constants.SCE_UDL_TPL_DEFAULT],
                               _keyword_styles=[_sci_constants.SCE_UDL_TPL_WORD])        
    def keyPressed(self, ch, scimoz):
        try:
            style_info = self._dedent_style_info
            res = KoLanguageKeywordBase._keyPressedAux(self, ch, scimoz, style_info)
            if res:
                return
        except:
            log.exception("Problem in KoLanguageKeywordBase._keyPressedAux")
        return koHTMLLanguageBase.keyPressed(self, ch, scimoz)
    
    def computeIndent(self, scimoz, indentStyle, continueComments):
        res = KoLanguageKeywordBase._computeIndent(self, scimoz, indentStyle, continueComments, self._dedent_style_info)
        if res:
            return res
        return koHTMLLanguageBase._computeIndent(self, scimoz, indentStyle, continueComments, self._dedent_style_info)
