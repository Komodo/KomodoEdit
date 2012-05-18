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

from koLanguageServiceBase import KoLexerLanguageService
from koLanguageKeywordBase import KoCommonBasicLanguageService

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
                unicode until variant wend when 
                while with withevents writeonly 
                xor""".split()

class koVisualBasicLanguage(KoCommonBasicLanguageService):
    name = "VisualBasic"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{7B83199C-6C30-43ef-9087-329831FC6425}"
    _reg_categories_ = [("komodo-language", name)]

    defaultExtension = ".vb"
    commentDelimiterInfo = {
        "line": [ "'",  "rem ", "REM "  ],
    }

    # Problems: 'private' and 'public' and 'shared' can come before a function name.
    def __init__(self):
        KoCommonBasicLanguageService.__init__(self)
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
    _reg_categories_ = [("komodo-language", name)]

    defaultExtension = ".vbs"
    
