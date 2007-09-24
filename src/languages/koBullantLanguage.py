from xpcom import components, ServerException

from koLanguageServiceBase import *

def registerLanguage(registery):
    registery.registerLanguage(koBullantLanguage())
    
class koBullantLanguage(KoLanguageBase):
    name = "Bullant"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{96A10671-291B-4000-A51E-899C933A2CA7}"

    defaultExtension = ".ant"
    commentDelimiterInfo = {
        "line": [ "#" ],
        "block": [ ("@off", "@on") ],
    }
    
    def __init__(self):
        KoLanguageBase.__init__(self)
        self._style_info.update(
            _block_comment_styles = [sci_constants.SCE_C_COMMENTLINE,
                                     sci_constants.SCE_C_COMMENT]
            )
    
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(components.interfaces.ISciMoz.SCLEX_BULLANT)
            self._lexer.setKeywords(0, self._keywords)
        return self._lexer

    _keywords = ["abstract", "all", "ancestor", "and", "application" \
                "assert", "attributes", "author", "begin" \
                "callback", "class", "concrete", "config", "constants", "construct", "continue" \
                "depends", "description", "downcast", "driver" \
                "elif", "else", "ensures", "error", "exception", "exposure", "extension" \
                "false", "fatal", "final", "function", "generics", "glyph" \
                "help", "hidden", "host", "immutable", "in", "inherits", "is" \
                "kernel", "label", "leave", "library", "locals" \
                "mutable", "none", "not", "null", "obsolete", "options", "or", "other" \
                "parameters", "peer", "private", "public" \
                "raise", "reason", "restricted", "retry", "return" \
                "returns", "rollback", "route" \
                "security", "self", "settings", "severity", "step" \
                "task", "test", "transaction", "true" \
                "unknown", "varying", "warning", "when" \
                "method", "end", "if", "until", "while", "trap", "case", "debug", "for", "foreach", "lock" \
                "boolean", "character", "character$", "date", "date$", "datetime", "datetime$" \
                "float", "hex$", "identifier", "identifier$", "integer", "interval", "interval$" \
                "money", "money$", "raw", "raw$", "string", "tick", "tick$", "time", "time$" \
                "version", "version$"]

