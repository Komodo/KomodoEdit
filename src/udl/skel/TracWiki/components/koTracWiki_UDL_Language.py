# Komodo TracWiki language service.
#

from xpcom import components

import logging
from koUDLLanguageBase import KoUDLLanguage

log = logging.getLogger("koTracWikiLanguage")
#log.setLevel(logging.DEBUG)

def registerLanguage(registry):
    log.debug("Registering language TracWiki")
    registry.registerLanguage(KoTracWikiLanguage())


class KoTracWikiLanguage(KoUDLLanguage):
    name = "TracWiki"
    lexresLangName = "TracWiki"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" % name
    _reg_clsid_ = "{b843faa8-aeea-4fcb-aeb9-36c4483c6f95}"
    _reg_categories_ = [("komodo-language", name)]
    defaultExtension = '.tracwiki'
    primary = 0
    _total_string_styles = None

    lang_from_udl_family = {'CSS': name, 'TPL': name, 'M': 'HTML', 'CSL': 'JavaScript', 'SSL': 'Python'}

    sample = """
== Level 2 ==
=== Level 3 ^([#hn note])^

'''bold'''
''italic''
'''''Wikipedia style'''''
`monospaced (''other markup ignored'')`

>> ... (I said)
> (he replied)
"""

    def getStringStyles(self):
        if self._total_string_styles is None:
            scin = components.interfaces.ISciMoz
            self._total_string_styles = [scin.SCE_UDL_CSS_DEFAULT,
                                   scin.SCE_UDL_CSS_COMMENT,
                                   scin.SCE_UDL_CSS_NUMBER,
                                   scin.SCE_UDL_CSS_STRING,
                                   scin.SCE_UDL_CSS_WORD,
                                   scin.SCE_UDL_CSS_IDENTIFIER,
                                   scin.SCE_UDL_CSS_OPERATOR,
                                   ] + KoUDLLanguage.getStringStyles(self)
        return self._total_string_styles

