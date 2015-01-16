# Komodo reStructuredText language service.
#

from xpcom import components

import logging
from koUDLLanguageBase import KoUDLLanguage

log = logging.getLogger("koReStructuredTextLanguage")
#log.setLevel(logging.DEBUG)

def registerLanguage(registry):
    log.debug("Registering language reStructuredText")
    registry.registerLanguage(KoReStructuredTextLanguage())


class KoReStructuredTextLanguage(KoUDLLanguage):
    name = "reStructuredText"
    lexresLangName = "reStructuredText"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" % name
    _reg_clsid_ = "{d98cc808-2981-4aa0-841b-e5e920d83177}"
    _reg_categories_ = [("komodo-language", name)]
    defaultExtension = '.rst'
    primary = 0
    supportsFolding = 0

    lang_from_udl_family = {'CSL': name, 'TPL': name, 'M': 'HTML', 'CSS': 'CSS', 'SSL': 'Python'}
    _total_string_styles = None

    sample = """:Version: 1.0 of 2001/08/08

=====
Title
=====
Subtitle
--------
List:
- This is item 1
- This is item 2 

External hyperlinks, like Python_.

.. _Python: http://www.python.org/

"""

    def getStringStyles(self):
        if self._total_string_styles is None:
            scin = components.interfaces.ISciMoz
            self._total_string_styles = [scin.SCE_UDL_CSL_DEFAULT,
                                   scin.SCE_UDL_CSL_COMMENT,
                                   scin.SCE_UDL_CSL_COMMENTBLOCK,
                                   scin.SCE_UDL_CSL_NUMBER,
                                   scin.SCE_UDL_CSL_STRING,
                                   scin.SCE_UDL_CSL_WORD,
                                   scin.SCE_UDL_CSL_IDENTIFIER,
                                   scin.SCE_UDL_CSL_OPERATOR,
                                   scin.SCE_UDL_CSL_REGEX,
                                   ] + KoUDLLanguage.getStringStyles(self)
        return self._total_string_styles
