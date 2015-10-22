# Registers the R language in Komodo.

import logging
from koUDLLanguageBase import KoUDLLanguage

log = logging.getLogger("koRLanguage")
#log.setLevel(logging.DEBUG)

def registerLanguage(registry):
    log.debug("Registering language R")
    registry.registerLanguage(KoRLanguage())

class KoRLanguage(KoUDLLanguage):

    # ------------ Komodo Registration Information ------------ #

    name = "R"
    lexresLangName = "R"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" % name
    _reg_categories_ = [("komodo-language", name)]
    _reg_clsid_ = "ec4a2833-5994-4c94-9be5-db6a8952029f"

    defaultExtension = '.R,.r,.Rout,.Rhistory,.Rt,.Rout.save,.Rout.fail,.S'
    primary = 0  # Whether the language shows up in Komodo's first level language menus.

    # ------------ Commenting Controls ------------ #

    commentDelimiterInfo = {
        "line": ['#'],
        "block": [],
    }

    # ------------ Indentation Controls ------------ #

    supportsSmartIndent = "brace"

    # ------------ Sub-language Controls ------------ #

    lang_from_udl_family = {'SSL': 'R'}
