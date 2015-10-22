# Registers the Mustache language in Komodo.

import logging
from koUDLLanguageBase import KoUDLLanguage

log = logging.getLogger("koMustacheLanguage")
#log.setLevel(logging.DEBUG)

def registerLanguage(registry):
    log.debug("Registering language Mustache")
    registry.registerLanguage(KoMustacheLanguage())

class KoMustacheLanguage(KoUDLLanguage):

    # ------------ Komodo Registration Information ------------ #

    name = "Mustache"
    lexresLangName = "Mustache"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" % name
    _reg_categories_ = [("komodo-language", name)]
    _reg_clsid_ = "ff35a478-6e4e-4daf-a608-a3837c157fbe"

    primary = 0  # Whether the language shows up in Komodo's first level language menus.

    # ------------ Sub-language Controls ------------ #
    lang_from_udl_family = {
        'M': 'HTML',
        'CSS': 'CSS',
        'CSL': 'JavaScript',
        'TPL': 'Mustache'
    }

    sample = """Hello {{name}}
You have just won {{value}} dollars!
{{#in_ca}}
Well, {{taxed_value}} dollars, after taxes.
{{/in_ca}}
{{! ignore me }}
    """