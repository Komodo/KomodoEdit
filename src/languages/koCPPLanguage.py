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

from xpcom import components
from koLintResult import *
from koLintResults import koLintResults
import os, sys, re
import tempfile
import process
import koprocessutils
import which

from koLanguageServiceBase import *

import logging
log = logging.getLogger("CPPLanguage")
#log.setLevel(logging.DEBUG)

class koCPPLanguage(KoLanguageBase, KoLanguageBaseDedentMixin):
    name = "C++"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{0613C3CC-EAA4-47f9-B2C3-A73270FFFB19}"
    _reg_categories_ = [("komodo-language", name)]

    searchURL = "http://www.google.com/search?q=site%3Ahttp%3A%2F%2Fwww.cppreference.com%2F+%W"

    accessKey = 'c'
    primary = 1
    modeNames = ['c','c++']
    defaultExtension = ".cpp"
    commentDelimiterInfo = {
        "line": [ "//" ],
        "block": [ ("/*", "*/") ],
        "markup": "*",
    }
    _dedenting_statements = [u'throw', u'return', u'break', u'continue']
    supportsSmartIndent = "brace"
    sample = """#include <windows.h>
#include <iostream>
#include <algorithm>
#include <vector>
#include <cstdlib>

using namespace std;    // This is a comment 
int main(int argc, char *argv[]) 
{
  if (argc != 2) {
    std::cerr << \"Usage:\\tsieve [iterations]\"; 
    return 1;
  };

  size_t NUM = atoi(argv[1]);
  DWORD dw = ::GetTickCount();
  vector<char> primes(8192 + 1);
  vector<char>::iterator pbegin = primes.begin();
  vector<char>::iterator begin = pbegin + 2;
  vector<char>::iterator end = primes.end();

  while (NUM--) {
    fill(begin, end, 1);
    for (vector<char>::iterator i = begin; 
              i < end; ++i) {
      if (*i)  {
        const size_t p = i - pbegin;
        for (vector<char>::iterator k = i + p; 
          k < end; k += p) {
          *k = 0;
        }
      }
    }
  }
  DWORD dw2 = ::GetTickCount();
  std::cout << \"Milliseconds = \" << dw2-dw << std::endl;
  return 0;
}
"""

    def __init__(self):
        KoLanguageBase.__init__(self)
        KoLanguageBaseDedentMixin.__init__(self)
        self._indenting_statements = [u'case', u'default', u'protected', u'private', u'public']
        self._style_info.update(
            _block_comment_styles = [sci_constants.SCE_C_COMMENT,
                                     sci_constants.SCE_C_COMMENTDOC,
                                     sci_constants.SCE_C_COMMENTDOCKEYWORD,
                                     sci_constants.SCE_C_COMMENTDOCKEYWORDERROR]
            )
        self._setupIndentCheckSoftChar()
        self._fastCharData = \
            FastCharData(trigger_char=";",
                         style_list=(sci_constants.SCE_C_OPERATOR,),
                         skippable_chars_by_style={ sci_constants.SCE_C_OPERATOR : "])",},
                         for_check=True)
                                          
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(components.interfaces.ISciMoz.SCLEX_CPP)
            self._lexer.setKeywords(0, self._keywords)
            self._lexer.setProperty("lexer.cpp.track.preprocessor", "0")
            self._lexer.setProperty('fold.cpp.syntax.based', '1')
            self._lexer.supportsFolding = 1
        return self._lexer

    # Taken from "The C++ Programming Language" 3rd Edition (published in 1997)
    
    _keywords = ["and", "and_eq",  "asm", "auto", "bitand", "bitor", "bool", "break",
                 "case", "catch", "char", "class", "compl", "const", "const_cast",
                 "continue", "default", "delete", "do", "double", "dynamic_cast", "else", "enum",
                 "explicit", "export", "extern", "false", "float", "for", "friend", "goto",
                 "if", "inline", "int", "long", "mutable", "namespace", "new", "not", "not_eq", "operator",
                 "or", "or_eq", "private", "protected", "public", "register",
                 "reinterpret_cast", "return", "short", "signed", "sizeof", "static",
                 "static_cast", "struct", "switch", "template", "this", "throw", "true",
                 "try", "typedef", "typeid", "typename", "union", "unsigned", "using", "virtual", "void", "volatile",
                 "wchar_t", "while", "xor", "xor_eq"]
    _keywords_11 = ["alignas", "alignof", "decltype", "char16_t",
                    "char32_t", "constexpr", "noexcept", "nullptr",
                    "static_assert", "thread_local"]
    _keywords += _keywords_11
    _keywords.sort()

    # XXX uncomment these to integrate the info and linter classes
    # XXX these are disabled because more work is necessary to properly
    # support linting (ie. include paths, defines, etc.)
    
    #def get_interpreter(self):
    #    if self._interpreter is None:
    #        self._interpreter = components.classes["@activestate.com/koAppInfoEx?app=CPP;1"].getService()
    #    return self._interpreter

#---- components
class KoCPPInfoEx:
    _com_interfaces_ = [components.interfaces.koIAppInfoEx]
    _reg_clsid_ = "53b9b15c-052d-4534-9f5d-07c155e1f27d"
    _reg_contractid_ = "@activestate.com/koAppInfoEx?app=CPP;1"
    _reg_desc_ = "C/C++ Information"

    def __init__(self):
        # The specific installation path for which the other attributes
        # apply to. It may be required for this to be set for certain
        # attributes to be determined.
        # attribute wstring installationPath;
        self.installationPath = ''

        # The path to the executable for the interpreter e.g. "usr/bin/perl"
        # attribute wstring executablePath;
        self.executablePath = ''
        self._executables = []

        # True if user is licensed for the current version of this app.
        # (For an app that does not require a license this will always be
        # true.)
        # attribute boolean haveLicense;
        self.haveLicense = 1
        
        # The build number. (May be null if it is not applicable.)
        # attribute long buildNumber;
        self.buildNumber = 0

        # version (duh, null if don't know how to determine)
        # attribute string version;
        version = ''
        
        # path to local help file (null if none)
        # attribute wstring localHelpFile;
        self.localHelpFile = ''

        # Web URL to main help file (null if none)
        # attribute wstring webHelpURL;
        self.webHelpURL = ''
        self._userPath = koprocessutils.getUserEnv()["PATH"].split(os.pathsep)


    # Query for a list of found installations of this application.
    # void FindInstallationPaths(out PRUint32 count,
    #                           [retval,
    #                            array,
    #                            size_is(count)] out wstring strs);
    def FindInstallationPaths(self):
        if sys.platform.startswith('win'):
            exts = ['.exe']
        else:
            exts = None
        interpreters = ['cl','gcc','cc']
        self._executables = []
        installationPaths = None
        for interp in interpreters:
            self._executables += which.whichall(interp, exts=exts, path=self._userPath)
        if self._executables:
            installationPaths = [self.getInstallationPathFromBinary(p)\
                                   for p in self._executables]
        return installationPaths
    
    # Given the path to an interpreter binary, return the
    # path of the installation
    # wstring getInstallationPathFromBinary(in wstring binaryPath);
    def getInstallationPathFromBinary(self, binaryPath):
        if sys.platform.startswith("win"):
            return os.path.dirname(binaryPath)
        else:
            return os.path.dirname(os.path.dirname(binaryPath))
    
    def set_installationPath(self, path):
        self.installationPath = path
        self.executablePath = ''
    
    def get_executablePath(self):
        if not self.installationPath:
            if not self._executables:
                paths = self.FindInstallationPaths()
                if paths:
                    self.installationPath = paths[0]
            if not self._executables:
                return None
            self.executablePath = self._executables[0]
        return self.executablePath

class KoCPPCompileLinter:
    _com_interfaces_ = [components.interfaces.koILinter]
    _reg_desc_ = "Komodo CPP Linter"
    _reg_clsid_ = "{e9046284-6db1-4e17-8d28-4c5f0c688dd8}"
    _reg_contractid_ = "@activestate.com/koLinter?language=CPP;1"
    # Uncomment the categories once we properly support C/C++
    # http://bugs.activestate.com/show_bug.cgi?id=91250
    _reg_categories_ = [
         #("category-komodo-linter", 'CPP'),
         #("category-komodo-linter", 'C++'),
         ]

    def __init__(self):
        self.appInfoEx = components.classes["@activestate.com/koAppInfoEx?app=CPP;1"].\
                    getService(components.interfaces.koIAppInfoEx)

        self._lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"].\
            getService(components.interfaces.koILastErrorService)
        self._prefSvc = components.classes["@activestate.com/koPrefService;1"].\
            getService(components.interfaces.koIPrefService)
        
    def lint(self, request):
        text = request.content.encode(request.encoding.python_encoding_name)
        return self.lint_with_text(request, text)
    
    def lint_with_text(self, request, text):
        """Lint the given C/C++ file.
        
        Raise an exception and set an error on koLastErrorService if there
        is a problem.
        """
        
        cwd = request.cwd
        
        #print "----------------------------"
        #print "C++ Lint"
        #print text
        #print "----------------------------"
        cc = self.appInfoEx.executablePath
        if cc is None:
            raise Exception("Could not find a suitable C/C++ interpreter for linting.")

        if request.koDoc.file:
            ext = request.koDoc.file.ext
        else:
            ext = koCPPLanguage.defaultExtension
        
        # save buffer to a temporary file
        try:
            filename = tempfile.mktemp(suffix=ext)
            fout = open(filename, 'wb')
            fout.write(text)
            fout.close()
        except ex:
            raise Exception("Unable to save temporary file for C/C++ linting: %s", str(ex))

        if cc.startswith('cl') or cc.lower().endswith("\\cl.exe"):
            argv = [cc, '-c']
            isGCC = False
            # ms cl errors
            re_string = r'(?P<file>.+)?\((?P<line>\d+)\)\s:\s(?:(?P<type>.+)?\s(?P<number>C\d+)):\s(?P<message>.*)'
        else: # gcc or cc
            argv = [cc, '-c']
            isGCC = True
            # gcc errors
            re_string = r'(?P<file>[^:]+)?:(?P<line>\d+?)(?::(?P<column>\d+))?:\s(?P<type>.+)?:\s(?P<message>.*)'
            
        argv += [filename]
        _re = re.compile(re_string)
        p = None
        #print argv
        try:
            env = koprocessutils.getUserEnv()
            cwd = cwd or None
            # XXX gcc hangs if we read stdout, so we don't pipe stdout,
            # need to test this again since using subprocess and also
            # test this with msvc.
            p = process.ProcessOpen(argv, cwd=cwd, env=env, stdin=None)
            stdout, stderr = p.communicate()
            if isGCC:
                lineSource = stderr
            else:
                lineSource = stdout
            lines = lineSource.splitlines(1)
            #print lines
        finally:
            pass #os.unlink(filename)
        
        try:
            results = koLintResults()
            if lines:
                datalines = re.split('\r\n|\r|\n',text)
                numLines = len(datalines)
                result = None
                for line in lines:
                    #print line
                    if result and line[0] == ' ':
                        result.description += '\n'+line
                        continue

                    g = _re.match(line)
                    if not g:
                        continue
                    err = g.groupdict()
                    #print repr(err)
                    result = KoLintResult()
                    # XXX error in FILENAME at line XXX
                    result.lineStart = result.lineEnd = int(err['line'])
                    result.columnStart = 1
                    result.columnEnd = len(datalines[result.lineEnd-1]) + 1
                    if 'error' in err['type']:
                        result.severity = result.SEV_ERROR
                    elif 'warn' in err['type']:
                        result.severity = result.SEV_WARNING
                    else:
                        result.severity = result.SEV_ERROR

                    if 'number' in err:
                        result.description = "%s %s: %s" % (err['type'],err['number'],err['message'])
                    else:
                        result.description = "%s: %s" % (err['type'],err['message'])
                    results.addResult(result)
        except:
            errmsg = "Exception in C/C++ linting while parsing results"
            self._lastErrorSvc.setLastError(1, errmsg)
            log.exception(errmsg)
        #print "----------------------------"
        return results

