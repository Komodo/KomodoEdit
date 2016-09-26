# Registers the Jinja2 language in Komodo.

import logging
from koXMLLanguageBase import KoDjangoTemplateFamilyBase


log = logging.getLogger("koJinja2Language")
#log.setLevel(logging.DEBUG)


def registerLanguage(registry):
    log.debug("Registering language Jinja2")
    registry.registerLanguage(KoJinja2Language())


class KoJinja2Language(KoDjangoTemplateFamilyBase):

    # ------------ Komodo Registration Information ------------ #

    name = "Jinja2"
    lexresLangName = "Jinja2"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" % name
    _reg_categories_ = [("komodo-language", name)]
    _reg_clsid_ = "f248fe85-caef-4ca9-9968-e4c45ba2b729"

    defaultExtension = '.jinja'
    #primary = 1  # Whether the language shows up in Komodo's first level language menus.
    searchURL = 'http://jinja.pocoo.org/docs/'

    # ------------ Commenting Controls ------------ #

    commentDelimiterInfo = {
        "line": [
            '##'   # http://jinja.pocoo.org/docs/dev/templates/#line-statements
        ],
        "block": [
            ('{#', '#}')  # http://jinja.pocoo.org/docs/dev/templates/#comments
        ],
    }

    # ------------ Indentation Controls ------------ #

    # To support automatic indenting and dedenting after "{([" and "})]"
    supportsSmartIndent = "brace"
    # Other smart indenting types are:
    #   'text', 'python', 'XML' and 'keyword'

    # Indent/dedent after these words.
    #_indenting_statements = ['case']
    #_dedenting_statements = ['return', 'break', 'continue']

    # ------------ Sub-language Controls ------------ #

    #Check: Update 'lang_from_udl_family' as appropriate for your
    #      lexer definition. There are four UDL language families:
    #           M (markup), i.e. HTML or XML
    #           CSL (client-side language), e.g. JavaScript
    #           SSL (server-side language), e.g. Perl, PHP, Python
    #           TPL (template language), e.g. RHTML, Django, Smarty
    #      'lang_from_udl_family' maps each UDL family code (M,
    #      CSL, ...) to the sub-language name in your language.
    #      Some examples:
    #        lang_from_udl_family = {   # A PHP file can contain
    #           'M': 'HTML',            #   HTML
    #           'SSL': 'PHP',           #   PHP
    #           'CSL': 'JavaScript',    #   JavaScript
    #        }
    #        lang_from_udl_family = {   # An RHTML file can contain
    #           'M': 'HTML',            #   HTML
    #           'SSL': 'Ruby',          #   Ruby
    #           'CSL': 'JavaScript',    #   JavaScript
    #           'TPL': 'RHTML',         #   RHTML template code
    #        }
    #        lang_from_udl_family = {   # A plain XML can just contain
    #           'M': 'XML',             #   XML
    #        }
    lang_from_udl_family = {'CSL': 'JavaScript', 'TPL': 'Jinja2', 'M': 'HTML', 'CSS': 'CSS'}

    # Used by KoDjangoTemplateFamilyBase
    _sliders = "else elif".split()
    _startWords = "autoescape block call elif else if filter for macro raw set trans with".split()

    sample = """{% if latest_poll_list %}
    <ul>
        {% for poll in latest_poll_list %}
            <li><a href="/polls/{{ poll.id }}/">{{ poll.question }}</a></li>
        {% endfor %}
    </ul>
{% else %}
    <p>No polls are available.</p>
{% endif %}
"""

