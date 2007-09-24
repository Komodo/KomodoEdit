from xpcom import components, ServerException

from koLanguageServiceBase import *

def registerLanguage(registery):
    registery.registerLanguage(koASN1Language())
    
class koASN1Language(KoLanguageBase):
    name = "ASN1"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{b9ae6e99-1106-475c-a36f-36f34ce11c16}"

    _stateMap = {
        'default': ('SCE_ASN1_DEFAULT',),
        'keywords': ('SCE_ASN1_KEYWORD',),
        'identifiers': ('SCE_ASN1_IDENTIFIER',),
        'comments': ('SCE_ASN1_COMMENT',),
        'operators': ('SCE_ASN1_OPERATOR',),
        'numbers': ('SCE_ASN1_SCALAR',),
        'strings': ('SCE_ASN1_STRING',),
        'attributes': ('SCE_ASN1_ATTRIBUTE',),
        'oid': ('SCE_ASN1_OID',),
        'descriptor': ('SCE_ASN1_DESCRIPTOR',),
        'type': ('SCE_ASN1_TYPE',),
        }
    defaultExtension = None
    commentDelimiterInfo = {}
    
    sample = """
SAMPLE NOT AVAILABLE
"""
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(components.interfaces.ISciMoz.SCLEX_ASN1)
        return self._lexer
