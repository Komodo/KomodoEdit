from xpcom import components, ServerException

from koLanguageServiceBase import *

# keyword lists in lexMSSQL
# statements
# data_types
# system_tables
# global_variables
# functions
# stored_procedures
# operators

def registerLanguage(registery):
    registery.registerLanguage(koMSSQLLanguage())
    
class koMSSQLLanguage(KoLanguageBase):
    name = "MSSQL"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{f1ee2866-9fcf-441e-bb1d-42274eb7f397}"

    _stateMap = {
        'default': ('SCE_MSSQL_DEFAULT',),
        'keywords': ('SCE_MSSQL_STATEMENT',
                     'SCE_MSSQL_DATATYPE',
                     'SCE_MSSQL_SYSTABLE',
                     'SCE_MSSQL_DEFAULT_PREF_DATATYPE',),
        'functions': ('SCE_MSSQL_FUNCTION',
                      'SCE_MSSQL_STORED_PROCEDURE',),
        'comments': ('SCE_MSSQL_COMMENT',
                     'SCE_MSSQL_LINE_COMMENT',),
        'numbers': ('SCE_MSSQL_NUMBER',),
        'strings': ('SCE_MSSQL_STRING',),
        'column_names': ('SCE_MSSQL_COLUMN_NAME',
                      'SCE_MSSQL_COLUMN_NAME_2',),
        'operators': ('SCE_MSSQL_OPERATOR',),
        'identifiers': ('SCE_MSSQL_IDENTIFIER',),
        'variables': ('SCE_MSSQL_VARIABLE',
                      'SCE_MSSQL_GLOBAL_VARIABLE',),
        }
    defaultExtension = None
    commentDelimiterInfo = {}
    
    sample = """
SAMPLE NOT AVAILABLE
"""
    def __init__(self):
        KoLanguageBase.__init__(self)
        del self.matchingSoftChars['"']
    
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(
                components.interfaces.ISciMoz.SCLEX_MSSQL)
            self._lexer.supportsFolding = 1
        return self._lexer
