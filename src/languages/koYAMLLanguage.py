from xpcom import components, ServerException

from koLanguageServiceBase import *

# yaml.org

def registerLanguage(registery):
    registery.registerLanguage(koYAMLLanguage())
    
class koYAMLLanguage(KoLanguageBase):
    name = "YAML"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{9a7eb39b-5e5a-44a7-9161-94b4b82ce9be}"

    _stateMap = {
        'default': ('SCE_YAML_DEFAULT',),
        'keywords': ('SCE_YAML_KEYWORD',),
        'identifiers': ('SCE_YAML_IDENTIFIER',),
        'comments': ('SCE_YAML_COMMENT',),
        'numbers': ('SCE_YAML_NUMBER',),
        'strings': ('SCE_YAML_TEXT',),
        'references': ('SCE_YAML_REFERENCE',),
        'documents': ('SCE_YAML_DOCUMENT',),
        'errors': ('SCE_YAML_ERROR',),
        'operators': ('SCE_YAML_OPERATOR',),
        }

    defaultExtension = '.yaml' # .yml
    commentDelimiterInfo = {"line": [ "#" ]}
    
    _indent_open_chars = ':'
    supportsSmartIndent = 'python'
    
    sample = """---
players:
  Vladimir Kramnik: &kramnik
    rating: 2700
    status: GM
  Deep Fritz: &fritz
    rating: 2700
    status: Computer
  David Mertz: &mertz
    rating: 1400
    status: Amateur

matches:
  -
    Date: 2002-10-04
    White: *fritz
    Black: *kramnik
    Result: Draw
  -
    Date: 2002-10-06
    White: *kramnik
    Black: *fritz
    Result: White
"""
    def __init__(self):
        KoLanguageBase.__init__(self)
        self._style_info.update(
            _indent_styles = [sci_constants.SCE_YAML_OPERATOR],
            _indent_open_styles = [sci_constants.SCE_YAML_OPERATOR],
            )

    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(sci_constants.SCLEX_YAML)
            self._lexer.setKeywords(0, self._keywords)
            self._lexer.supportsFolding = 1
        return self._lexer

    _keywords = ['true', 'false', 'yes', 'no']
