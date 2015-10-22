#!python
# Copyright (c) 2015 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

import re

from xpcom import components

from koLanguageServiceBase import *

log = logging.getLogger('koSwiftLanguage')
#log.setLevel(logging.DEBUG)

class koSwiftLanguage(KoLanguageBase, KoLanguageBaseDedentMixin):
    name = "Swift"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{9DC92814-A6D2-401a-C12B-9271710D7381}"
    _reg_categories_ = [("komodo-language", name)]

    shebangPatterns = [
        re.compile(r'\A#!.*(swift).*$', re.I | re.M),
    ]

    accessKey = 'w'
    defaultExtension = ".swift"
    commentDelimiterInfo = {
        "line": [ "//" ],
        "block": [ ("/*", "*/") ],
        "markup": "*",
    }
    _indenting_statements = [u'case']
    _dedenting_statements = [u'throw', u'return', u'break', u'continue', u'fallthrough']
    
    namedBlockDescription = 'Swift functions, classes, and structs'
    namedBlockRE = r'(func|class|struct|override)\s*([\w|\_]*?)'
    supportsSmartIndent = "brace"
    sample = """/*
  Copyright (C) 2015 Apple Inc. All Rights Reserved.
  See LICENSE.txt for this sample's licensing information

  Abstract:
  Defines the Player class.
*/
 
import SpriteKit
import GameController
 
class Player: NSObject {
    // MARK: Types
    enum HeroType {
        case Warrior, Archer
    }
    struct Keys {
        static let projectileUserDataPlayer = "Player.Keys.projectileUserDataPlayer"
    }
    
    // MARK: Properties
    var heroType: HeroType?
    var score = 0
    
    override init() {
        // Pick one of the two hero classes at random for additional players in multiplayer games.
        if arc4random_uniform(2) == 0 {
            heroType = .Warrior
        }
        else {
            heroType = .Archer
        }
    }
}
"""

    def __init__(self):
        KoLanguageBase.__init__(self)
        KoLanguageBaseDedentMixin.__init__(self)
        self._style_info.update(
            _block_comment_styles = [sci_constants.SCE_C_COMMENT,
                                     sci_constants.SCE_C_COMMENTDOC,
                                     sci_constants.SCE_C_COMMENTDOCKEYWORD,
                                     sci_constants.SCE_C_COMMENTDOCKEYWORDERROR],
#            _variable_styles = [components.interfaces.ISciMoz.SCE_C_IDENTIFIER,
#                                components.interfaces.ISciMoz.SCE_C_STRINGRAW]
            )
        self._setupIndentCheckSoftChar()
        self._fastCharData = \
            FastCharData(trigger_char=";",
                         style_list=(sci_constants.SCE_C_OPERATOR, ),
                         skippable_chars_by_style={ sci_constants.SCE_C_OPERATOR : "])", },
                         for_check=True)
        
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(components.interfaces.ISciMoz.SCLEX_CPP)
            self._lexer.setProperty('lexer.cpp.allow.dollars', '1') # closure parameters
            self._lexer.setProperty('lexer.cpp.backquoted.strings', '1') # for using reserved words as identifiers
            self._lexer.supportsFolding = 1
            self._lexer.setProperty('fold.cpp.syntax.based', '1')
            self._lexer.setKeywords(0, self._keywords)
            self._lexer.setKeywords(1, self._keywords1)
        
        return self._lexer

    _keywords = [
        # Declarations.
        "class", "deinit", "enum", "extension", "func", "import", "init",
        "inout", "internal", "let", "operator", "private", "protocol", "public",
        "static", "struct", "subscript", "typealias", "var",
        # Statements.
        "break", "case", "continue", "default", "defer", "do", "else",
        "fallthrough", "for", "guard", "if", "in", "repeat", "return", "switch",
        "where", "while",
        # Expressions and types.
        "as", "catch", "dynamicType", "false", "is", "nil", "rethrows", "super",
        "self", "Self", "throw", "throws", "true", "try", "__COLUMN__",
        "__FILE__", "__FUNCTION__", "__LINE__",
        # Patterns.
        #"_",
        # Context.
        "associativity", "convenience", "dynamic", "didSet", "final", "get",
        "infix", "indirect", "lazy", "left", "mutating", "none", "nonmutating",
        "optional", "override", "postfix", "precedence", "prefix", "Protocol",
        "required", "right", "set", "Type", "unowned", "weak", "willSet",
    ]
    
    _keywords1 = [
        # Primitive types.
        "Void", "Float", "Double", "String", "Bool", "Character",
        "UnicodeScalar",
        # Collection types.
        "Array", "Set", "Dictionary",
        # Integer types.
        "Int", "Int8", "Int16", "Int32", "Int64",
        "UInt", "UInt8", "UInt16", "UInt32", "UInt64",
    ]
