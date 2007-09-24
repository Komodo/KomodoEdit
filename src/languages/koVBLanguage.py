from xpcom import components, ServerException

from koLanguageServiceBase import *

def registerLanguage(registery):
    registery.registerLanguage(koVisualBasicLanguage())
    registery.registerLanguage(koVBScriptLanguage())

# list obtained from http://msdn.microsoft.com/library/default.asp?url=/library/en-us/vblr7/html/vaorivblangkeywordsall.asp
keywords =  """addhandler addressof alias and
                andalso  ansi as assembly 
                auto boolean byref byte 
                byval call case catch 
                cbool cbyte cchar cdate 
                cdec cdbl char cint 
                class clng cobj const 
                cshort csng cstr ctype 
                date decimal declare default 
                delegate dim directcast do 
                double each else elseif 
                end enum erase error 
                event exit false finally 
                for friend function get 
                gettype gosub goto handles 
                if implements imports in 
                inherits integer interface is 
                let lib like long 
                loop me mod module 
                mustinherit mustoverride mybase myclass 
                namespace new next not 
                nothing notinheritable notoverridable object 
                on option optional or 
                orelse overloads overridable overrides 
                paramarray preserve private property 
                protected public raiseevent readonly 
                redim rem removehandler resume 
                return select set shadows 
                shared short single static 
                step stop string structure 
                sub synclock then throw 
                to true try typeof 
                unicode until variant when 
                while with withevents writeonly 
                xor""".split()

class koVisualBasicLanguage(KoLanguageBase):
    name = "VisualBasic"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{7B83199C-6C30-43ef-9087-329831FC6425}"

    defaultExtension = ".vb"
    commentDelimiterInfo = {
        "line": [ "'",  "rem ", "REM "  ],
    }

    supportsSmartIndent = "brace"
   
    def __init__(self):
        KoLanguageBase.__init__(self)
        del self.matchingSoftChars["'"]
     
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(components.interfaces.ISciMoz.SCLEX_VB)
            self._lexer.setKeywords(0, keywords)
            self._lexer.supportsFolding = 0
        return self._lexer

class koVBScriptLanguage(koVisualBasicLanguage):
    name = "VBScript"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{113d3a95-0488-4173-83ce-e51fe19c4c95}"

    defaultExtension = ".vbs"
    
