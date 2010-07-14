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

def registerLanguage(registery):
    registery.registerLanguage(koPascalLanguage())
    
class koPascalLanguage(KoLanguageBase):
    name = "Pascal"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{8AE35E4C-0EC9-49f2-A534-8FEAB91D261D}"

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
    supportsSmartIndent = "brace"
    
    def __init__(self):
        KoLanguageBase.__init__(self)
        self._style_info.update(
            _block_comment_styles = [sci_constants.SCE_C_COMMENT,
                                     sci_constants.SCE_C_COMMENTDOC,
                                     sci_constants.SCE_C_COMMENTDOCKEYWORD,
                                     sci_constants.SCE_C_COMMENTDOCKEYWORDERROR]
            )

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
until uses var virtual while with write xor""".split()

    _keywords2 = """write read default public protected private property
            published stored""".split()

