from xpcom import components, ServerException

from koLanguageServiceBase import *

class koPOGetTextLanguage(KoLanguageBase):
    name = "GetText"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{f65ce5b1-0111-4ffe-8f9e-e2e4a8d3dbd7}"
    _reg_categories_ = [("komodo-language", name)]

    _stateMap = {
        'default': ('SCE_PO_DEFAULT',
                    'SCE_PO_ERROR'),
        'comments': ('SCE_PO_COMMENT',
                     'SCE_PO_FUZZY',
                     'SCE_PO_PROGRAMMER_COMMENT',
                     'SCE_PO_REFERENCE',
                     'SCE_PO_FLAGS'),
        'strings': ('SCE_PO_MSGID_TEXT',
                    'SCE_PO_MSGSTR_TEXT',
                    'SCE_PO_MSGCTXT_TEXT',
                    'SCE_PO_MSGID_TEXT_EOL',
                    'SCE_PO_MSGSTR_TEXT_EOL',
                    'SCE_PO_MSGCTXT_TEXT_EOL'),
        'keywords': ('SCE_PO_MSGID',
                     'SCE_PO_MSGSTR',
                     'SCE_PO_MSGCTXT'),
        }

    defaultExtension = '.po'
    commentDelimiterInfo = {"line": [ "#" ]}
    
    sample = """
#. TRANSLATORS: Please leave %s as it is, because it is needed by the program.
#. Thank you for contributing to this project.
#: src/name.c:36
msgid "My name is %s.\n"
msgstr ""
"""
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(
                components.interfaces.ISciMoz.SCLEX_PO)
            self._lexer.supportsFolding = 0
        return self._lexer
