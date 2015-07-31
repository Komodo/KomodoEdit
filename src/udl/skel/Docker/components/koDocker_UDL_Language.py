# Registers the Docker language in Komodo.

import logging
from koUDLLanguageBase import KoUDLLanguage

log = logging.getLogger("koDockerLanguage")
#log.setLevel(logging.DEBUG)

def registerLanguage(registry):
    log.debug("Registering language Docker")
    registry.registerLanguage(KoDockerLanguage())

class KoDockerLanguage(KoUDLLanguage):

    # ------------ Komodo Registration Information ------------ #

    name = "Docker"
    lexresLangName = "Docker"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" % name
    _reg_categories_ = [("komodo-language", name)]
    _reg_clsid_ = "54072a7f-a845-4b78-b63f-fc47c583e0b8"

    
    primary = 0  # Whether the language shows up in Komodo's first level language menus.

    extraFileAssociations = ["Dockerfile"]
    
    # ------------ Commenting Controls ------------ #

    commentDelimiterInfo = {
        "line": ['#'],
        "block": [],
    }

    # ------------ Indentation Controls ------------ #

    # To support automatic indenting and dedenting after "{([" and "})]"
    supportsSmartIndent = "brace"

    # ------------ Sub-language Controls ------------ #

    lang_from_udl_family = {'SSL': 'Docker'}
