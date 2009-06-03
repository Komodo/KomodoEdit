# Komodo TracWiki language service.
#

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
    _reg_clsid_ = "{6072ecd4-525e-11db-82d8-000d935d3368}"
    defaultExtension = '.tracwiki'
    primary = 0

    lang_from_udl_family = {'CSL': 'JavaScript', 'TPL': 'TracWiki', 'M': 'HTML', 'CSS': 'CSS', 'SSL': 'Python'}
    
    def get_linter(self):
        return None

# Komodo TracWiki language service.
#

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
    _reg_clsid_ = "{6072ecd4-525e-11db-82d8-000d935d3368}"
    defaultExtension = '.tracwiki'
    primary = 0

    lang_from_udl_family = {'CSL': 'JavaScript', 'TPL': 'TracWiki', 'M': 'HTML', 'CSS': 'CSS', 'SSL': 'Python'}
    
    def get_linter(self):
        return None

