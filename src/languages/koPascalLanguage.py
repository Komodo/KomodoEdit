# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
# 
# The contents of this file are subject to the Mozilla Public License
# Version 1.1 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
# 
# Software distributed under the License is distributed on an "AS IS"
# basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
# License for the specific language governing rights and limitations
# under the License.
# 
# The Original Code is Komodo code.
# 
# The Initial Developer of the Original Code is ActiveState Software Inc.
# Portions created by ActiveState Software Inc are Copyright (C) 2000-2012
# ActiveState Software Inc. All Rights Reserved.
# 
# Contributor(s):
#   ActiveState Software Inc
# 
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
# 
# ***** END LICENSE BLOCK *****

from xpcom import components, ServerException

from koLanguageKeywordBase import KoLanguageKeywordBase
from koLanguageServiceBase import KoLexerLanguageService, FastCharData

sci_constants = components.interfaces.ISciMoz

class koPascalLanguage(KoLanguageKeywordBase):
    name = "Pascal"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{8AE35E4C-0EC9-49f2-A534-8FEAB91D261D}"
    _reg_categories_ = [("komodo-language", name)]

    defaultExtension = ".pas"
    commentDelimiterInfo = {
        # See the following for info on Pascal comments:
        #  http://www.math.uni-hamburg.de/it/software/fpk/ref/node7.html
        #XXX The line Pascal comment is a Delphi only thing, so I am leaving
        #    it out for now.
        #"line": [ "//" ],
        "block": [ ("{",  "}"),
                   ("(*", "*)") ],
        "markup": "*",
    }
    supportsSmartIndent = "keyword"
    _indenting_statements = ['begin', 'record', 'repeat', 'case', ]
    _dedenting_statements = ['goto', 'halt', ]
    _keyword_dedenting_keywords = ['end', 'until', ]

    _stateMap = {
        'default': ('SCE_PAS_DEFAULT',),
        'keywords': ('SCE_PAS_WORD', 'SCE_PAS_ASM'),
        'comments': ('SCE_PAS_COMMENT', 'SCE_PAS_COMMENT2', 'SCE_PAS_COMMENTLINE',),
        'identifiers': ('SCE_PAS_IDENTIFIER',),
        'preprocessor': ('SCE_PAS_PREPROCESSOR', 'SCE_PAS_PREPROCESSOR2'),
        'numbers': ('SCE_PAS_NUMBER', 'SCE_PAS_HEXNUMBER',),
        'strings': ('SCE_PAS_STRING', 'SCE_PAS_STRINGEOL', 'SCE_PAS_CHARACTER',),
        }

    sample = """
program MyProg(input, output)
(* Warning: this program might not compile. *)
  begin
    { that's because there's no
      Pascal compiler on this machine.
    }
    var myVar:integer;
    myVar := 5;
    if (myVar > 3) begin
      writeln("Pascal is fun!!!!")
    end
  end
end.
"""    
    def __init__(self):
        KoLanguageKeywordBase.__init__(self)
        self._style_info.update(
            _block_comment_styles = [sci_constants.SCE_PAS_COMMENT,
                                     sci_constants.SCE_PAS_COMMENT2,
                                     sci_constants.SCE_PAS_COMMENTLINE],
            _indent_styles = [sci_constants.SCE_PAS_OPERATOR],
            _variable_styles = [sci_constants.SCE_PAS_IDENTIFIER],
            _lineup_close_styles = [sci_constants.SCE_PAS_OPERATOR],
            _lineup_styles = [sci_constants.SCE_PAS_OPERATOR],
            _keyword_styles = [sci_constants.SCE_PAS_WORD],
            _default_styles = [sci_constants.SCE_PAS_DEFAULT],
            _ignorable_styles = [sci_constants.SCE_PAS_COMMENT,
                                 sci_constants.SCE_PAS_COMMENT2,
                                 sci_constants.SCE_PAS_COMMENTLINE,
                                 sci_constants.SCE_PAS_NUMBER],
            )
        self._fastCharData = \
            FastCharData(trigger_char=";",
                         style_list=(sci_constants.SCE_PAS_OPERATOR, ),
                         skippable_chars_by_style={ sci_constants.SCE_PAS_OPERATOR : "])" },
                         for_check=True)

    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(components.interfaces.ISciMoz.SCLEX_PASCAL)
            self._lexer.setKeywords(0, self._keywords)
            self._lexer.setKeywords(1, self._keywords2)
            self._lexer.supportsFolding = 1
        return self._lexer

    _keywords = """and array asm begin case cdecl class const constructor default 
destructor div do downto else end end. except exit exports external far file 
finalization finally for function goto if implementation in index inherited 
initialization inline interface label library message mod near nil not 
object of on or out overload override packed pascal private procedure program 
property protected public published raise read record register repeat resourcestring 
safecall set shl shr stdcall stored string then threadvar to try type unit 
until uses var virtual while with write writeln xor""".split()

    _keywords2 = """write read default public protected private property
            published stored""".split()

