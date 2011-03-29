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
# Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
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

from koLanguageServiceBase import *

class koADALanguage(KoLanguageBase):
    name = "Ada"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{6148E361-5E42-4AA1-B22D-BB2D02DE4FB1}"
    _reg_categories_ = [("komodo-language", name)]

    _stateMap = {
        'default': ('SCE_ADA_DEFAULT',),
        'keywords': ('SCE_ADA_WORD',),
        'identifiers': ('SCE_ADA_IDENTIFIER',),
        'comments': ('SCE_ADA_COMMENTLINE',),
        'numbers': ('SCE_ADA_NUMBER',),
        'strings': ('SCE_ADA_CHARACTER',
                    'SCE_ADA_STRING',),
        'stringeol': ('SCE_ADA_CHARACTEREOL',
                      'SCE_ADA_STRINGEOL',),
        'illegals': ('SCE_ADA_ILLEGAL',),
        'delimiters': ('SCE_ADA_DELIMITER',),
        'labels': ('SCE_ADA_LABEL',),
        }
    commentDelimiterInfo = {
        "line": [ "--" ]
    }

    defaultExtension = ".ada"
    sample = """-- simple programming with floating-point #s
with Ada.Float_Text_IO;
use Ada.Float_Text_IO;
procedure Think is
   A, B : Float := 0.0; -- A and B initially zero; note the period.
   I, J : Integer := 1;
begin
   A := B   7.0;
   I := J * 3;
   B := Float(I)   A;
   Put(B);
end Think;
"""
    def __init__(self):
        KoLanguageBase.__init__(self)
        del self.matchingSoftChars["'"]

    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(components.interfaces.ISciMoz.SCLEX_ADA)
            self._lexer.setKeywords(0, self._keywords)
            self._lexer.supportsFolding = 0
        return self._lexer


    _keywords = ["abort", "abs", "abstract", "accept", "access"
                 "aliased", "all", "and", "array", "at", "begin", "body",
                 "case", "constant", "declare", "delay", "delta",
                 "digits", "do", "else", "elsif", "end", "entry",
                 "exception", "exit", "for", "function", "generic",
                 "goto", "if", "in", "is", "limited", "loop", "mod",
                 "new", "not", "null", "of", "or", "others", "out",
                 "package", "pragma", "private", "procedure",
                 "protected", "raise", "range", "record", "rem",
                 "renames", "requeue", "return", "reverse",
                 "select", "separate", "subtype", "tagged",
                 "task", "terminate", "then", "type", "until", "use",
                 "when", "while", "with", "xor"]