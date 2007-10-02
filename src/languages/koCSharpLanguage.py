from xpcom import components, ServerException

from koLanguageServiceBase import *

def registerLanguage(registery):
    registery.registerLanguage(koCSharpLanguage())


class koCSharpLanguage(KoLanguageBase):
    name = "C#"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{BC6A9F39-650F-48d4-B286-4D569DDB1F43}"

    accessKey='#'
    commentDelimiterInfo = {
        "line": [ "//" ],
        "block": [ ("/*", "*/") ],
        "markup": "*",
    }
    _dedenting_statements = [u'throw', u'return', u'break', u'continue']
    _indenting_statements = [u'case']

    defaultExtension = ".cs"
    supportsSmartIndent = "brace"

    def __init__(self):
        KoLanguageBase.__init__(self)
        self._style_info.update(
            _block_comment_styles = [sci_constants.SCE_C_COMMENT,
                                     sci_constants.SCE_C_COMMENTDOC,
                                     sci_constants.SCE_C_COMMENTDOCKEYWORD,
                                     sci_constants.SCE_C_COMMENTDOCKEYWORDERROR]
            )
        self.setupIndentCheckSoftChar()
    
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(components.interfaces.ISciMoz.SCLEX_CPP)
            self._lexer.setKeywords(0, self._keywords)
            self._lexer.supportsFolding = 1
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
