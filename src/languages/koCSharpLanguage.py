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


class koCSharpLanguage(KoLanguageBase, KoLanguageBaseDedentMixin):
    name = "C#"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{BC6A9F39-650F-48d4-B286-4D569DDB1F43}"
    _reg_categories_ = [("komodo-language", name)]

    accessKey='#'
    commentDelimiterInfo = {
        "line": [ "//" ],
        "block": [ ("/*", "*/") ],
        "markup": "*",
    }
    _dedenting_statements = [u'throw', u'return', u'break', u'continue']

    defaultExtension = ".cs"
    supportsSmartIndent = "brace"

    def __init__(self):
        KoLanguageBase.__init__(self)
        KoLanguageBaseDedentMixin.__init__(self)
        self._style_info.update(
            _block_comment_styles = [sci_constants.SCE_C_COMMENT,
                                     sci_constants.SCE_C_COMMENTDOC,
                                     sci_constants.SCE_C_COMMENTDOCKEYWORD,
                                     sci_constants.SCE_C_COMMENTDOCKEYWORDERROR]
            )
        self._setupIndentCheckSoftChar()
    
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(components.interfaces.ISciMoz.SCLEX_CPP)
            self._lexer.setKeywords(0, self._keywords)
            self._lexer.supportsFolding = 1
            self._lexer.setProperty('fold.cpp.syntax.based', '1')
        return self._lexer

    def getEncodingWarning(self, encoding):
        if not encoding.use_byte_order_marker and encoding.encoding_info.byte_order_marker != '':
            return 'It is recommended that any %s file include a signature if it\'s encoding supports one' % self.name                
        else: # It's all good
            return ''
        
    _keywords = ["abstract", "as", "base", "bool", "break", "byte",
                 "case", "catch", "char", "checked", "class", "const", "continue",
                 "decimal", "default", "delegate", "do", "double", "else", "enum",
                 "event", "explicit", "extern", "false", "finally", "fixed",
                 "float", "for", "foreach", "goto", "if", "implicit", "in", "int",
                 "interface", "internal", "is", "lock", "long", "namespace", "new",
                 "null", "object", "operator", "out", "override", "params",
                 "private", "protected", "public", "readonly", "ref", "return",
                 "sbyte", "sealed", "short", "sizeof", "stackalloc", "static",
                 "string", "struct", "switch", "this", "throw", "true", "try",
                 "typeof", "uint", "ulong", "unchecked", "unsafe", "ushort",
                 "using", "virtual", "void", "while"]
    
    sample = """using System;
namespace Sieve
{
  class Class1 {   // This is a comment 
    static void Main(string[] args) {
      if (args.Length != 1) {
        Console.WriteLine("Usage:\tsieve [iterations]");
        return;
      }
      int NUM = int.Parse(args[0]);
      long dt = DateTime.Now.Ticks;
      int[] primes = new int[8192+1];
      int pbegin = 0;
      int begin = 2;
      int end = 8193;

      while (NUM-- != 0) {
        for (int i = 0; i < end; i++) {
          primes[i] = 1;
        }

        for (int i = begin; i < end; ++i) {
          if (primes[i] != 0) {
            int p = i - pbegin;
            for (int k = i + p; k < end; k += p) {
              primes[k] = 0;
            };
          };
        };
      };

      long dt2 = DateTime.Now.Ticks;
      System.Console.WriteLine("Milliseconds = {0}", (dt2-dt)/10000);
    }
  }
}
"""
