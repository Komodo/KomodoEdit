# Registers the Handlebars language in Komodo.

import logging
from koUDLLanguageBase import KoUDLLanguage

log = logging.getLogger("koHandlebarsLanguage")
#log.setLevel(logging.DEBUG)

def registerLanguage(registry):
    log.debug("Registering language Handlebars")
    registry.registerLanguage(KoHandlebarsLanguage())

class KoHandlebarsLanguage(KoUDLLanguage):

    # ------------ Komodo Registration Information ------------ #

    name = "Handlebars"
    lexresLangName = "Handlebars"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" % name
    _reg_categories_ = [("komodo-language", name)]
    _reg_clsid_ = "59f91e08-64c2-40e7-9c4b-730c231af7d3"

    primary = 1  # Whether the language shows up in Komodo's first level language menus.

    # ------------ Sub-language Controls ------------ #
    lang_from_udl_family = {
        'M': 'HTML',
        'CSS': 'CSS',
        'CSL': 'JavaScript',
        'TPL': 'Handlebars'
    }

    sample = """<h1>Comments</h1>

<div id="comments">
  {{#each comments}}
  <h2><a href="/posts/{{../permalink}}#{{id}}">{{title}}</a></h2>
  <div>{{body}}</div>
  {{/each}}
</div>"""