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

import re, os
from xpcom import components, ServerException
import logging
from koLintResult import runGenericLinter
import process

from koLanguageKeywordBase import KoLanguageKeywordBase
from koLanguageServiceBase import KoLexerLanguageService
import scimozindent

log = logging.getLogger("koLuaLanguage")
#log.setLevel(logging.DEBUG)

sci_constants = components.interfaces.ISciMoz

class koLuaLanguage(KoLanguageKeywordBase):
    name = "Lua"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{D3C94E8B-B75C-4fa4-BC4D-986F68ACD33C}"
    _reg_categories_ = [("komodo-language", name)]

    defaultExtension = ".lua"
    commentDelimiterInfo = {
        "line": [ "--" ],
        "block": [ ("--[[", "]]") ],
    }
    supportsSmartIndent = "keyword"
    _indenting_statements = ['function', 'if', 'for', 'repeat', 'while', 'else',
                             'elseif', 'do']
    _dedenting_statements = ['break', 'return', 'error']
    # These trigger a dedent when entered, but then count +1
    # This might be better than putting 'else' in both
    # _indenting_statements and _keyword_dedenting_keywords
    _keyword_dedenting_keywords = ['end', 'else', 'elseif', 'until']
    
    sample = """require "lfs"

function dirtree(dir)
  assert(dir and dir ~= "", "directory parameter is missing or empty")
  if string.sub(dir, -1) == "/" then
    dir=string.sub(dir, 1, -2)
  end

  local diriters = {lfs.dir(dir)}
  local dirs = {dir}

  return function()
    repeat 
      local entry = diriters[#diriters]()
      if entry then 
        if entry ~= "." and entry ~= ".." then 
          local filename = table.concat(dirs, "/").."/"..entry
          local attr = lfs.attributes(filename)
          if attr.mode == "directory" then 
            table.insert(dirs, entry)
            table.insert(diriters, lfs.dir(filename))
          end
          return filename, attr
        end
      else
        table.remove(dirs)
        table.remove(diriters)
      end
    until #diriters==0
  end
end
    """

    def __init__(self):
        KoLanguageKeywordBase.__init__(self)
        self._style_info.update(
            _block_comment_styles = [sci_constants.SCE_LUA_COMMENTLINE,
                                     sci_constants.SCE_LUA_COMMENTDOC],
            _indent_styles = [sci_constants.SCE_LUA_OPERATOR],
            _variable_styles = [sci_constants.SCE_LUA_IDENTIFIER],
            _lineup_close_styles = [sci_constants.SCE_LUA_OPERATOR],
            _lineup_styles = [sci_constants.SCE_LUA_OPERATOR],
            _keyword_styles = [sci_constants.SCE_LUA_WORD,
                               sci_constants.SCE_LUA_WORD2,
                               sci_constants.SCE_LUA_WORD3,
                               sci_constants.SCE_LUA_WORD4,
                               sci_constants.SCE_LUA_WORD5,
                               sci_constants.SCE_LUA_WORD6,
                               sci_constants.SCE_LUA_WORD7,
                               sci_constants.SCE_LUA_WORD8,
                               ],
            _default_styles = [sci_constants.SCE_LUA_DEFAULT],
            _ignorable_styles = [sci_constants.SCE_LUA_COMMENT,
                                 sci_constants.SCE_LUA_COMMENTLINE,
                                 sci_constants.SCE_LUA_COMMENTDOC,
                                 sci_constants.SCE_LUA_NUMBER],
            )

    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(components.interfaces.ISciMoz.SCLEX_LUA)
            self._lexer.setKeywords(0, self._keywords)
            self._lexer.setKeywords(1, self._keywords1)
            self._lexer.supportsFolding = 1
        return self._lexer

    # Reserved words.
    _keywords = ["and", "break", "do", "else", "elseif", "end", "false", "for", "function",
                 "goto", "if", "in", "local", "nil", "not", "or", "repeat", "return", "then",
                 "true", "until", "while"]
    # Global functions and constants, and libraries.
    _keywords1 = ["assert", "collectgarbage", "dofile", "error", "getmetatable", "ipairs",
                  "load", "loadfile", "next", "pairs", "pcall", "print", "rawequal", "rawget",
                  "rawset", "require", "select", "setmetatable", "tonumber", "tostring", "type",
                  "xpcall", "_G", "_VERSION",
                  # New in Lua 5.2.
                  "rawlen", "_ENV",
                  # Deprecated in 5.2.
                  "getfenv", "loadstring", "module", "setfenv", "unpack"
                  
                  "string", "string.byte", "string.char", "string.dump", "string.find",
                  "string.format", "string.gmatch", "string.gsub", "string.len", "string.lower",
                  "string.match", "string.rep", "string.reverse", "string.sub", "string.upper",
                  # New in Lua 5.3.
                  "string.pack", "string.packsize", "string.unpack",

                  "table", "table.concat", "table.insert", "table.remove", "table.sort",
                  # New in 5.2.
                  "table.pack", "table.unpack",
                  # New in in 5.3.
                  "table.move",

                  "math", "math.abs", "math.acos", "math.asin", "math.atan", "math.ceil",
                  "math.cos", "math.deg", "math.exp", "math.floor", "math.fmod", "math.huge",
                  "math.log", "math.max", "math.min", "math.modf", "math.pi", "math.rad",
                  "math.random", "math.randomseed", "math.sin", "math.sqrt", "math.tan",
                  # New in 5.3.
                  "math.maxinteger", "math.mininteger", "math.tointeger", "math.type",
                  "math.ult",

                  "coroutine", "coroutine.create", "coroutine.resume", "coroutine.running",
                  "coroutine.status", "coroutine.wrap", "coroutine.yield",
                  # New in Lua 5.3.
                  "coroutine.isyieldable",

                  "package", "package.cpath", "package.loaded", "package.loadlib",
                  "package.path", "package.preload",
                  # New in 5.2.
                  "package.config", "package.searchers", "package.searchpath",

                  "utf8", "utf8.char", "utf8.charpattern", "utf8.codepoint", "utf8.codes",
                  "utf8.len", "utf8.offset",

                  "io", "io.close", "io.flush", "io.input", "io.lines", "io.open", "io.output",
                  "io.popen", "io.read", "io.stderr", "io.stdin", "io.stdout", "io.tmpfile",
                  "io.type", "io.write",

                  "os", "os.clock", "os.date", "os.difftime", "os.execute", "os.exit",
                  "os.getenv", "os.remove", "os.rename", "os.setlocale", "os.time",
                  "os.tmpname",

                  "debug", "debug.debug", "debug.gethook", "debug.getinfo", "debug.getlocal",
                  "debug.getmetatable", "debug.getregistry", "debug.getupvalue",
                  "debug.sethook", "debug.setlocal", "debug.setmetatable", "debug.setupvalue",
                  "debug.traceback",
                  # New in Lua 5.2.
                  "debug.getuservalue", "debug.setuservalue", "debug.upvalueid",
                  "debug.upvaluejoin"]
    
    #XXX: Override _indentingOrDedentingStatement looking for things like
    #   return function ...
    

    # Override:
    # Handle return ... function differently

    def computeIndent(self, scimoz, indentStyle, continueComments):
        if continueComments:
            return KoLanguageKeywordBase.computeIndent(self, scimoz, indentStyle, continueComments)
        calculatedData = self.getTokenDataForComputeIndent(scimoz, self._style_info)
        indent = self._computeIndent(scimoz, indentStyle, continueComments, self._style_info, calculatedData)
        if indent is not None:
            return indent
        return KoLanguageKeywordBase.computeIndent(self, scimoz, indentStyle, continueComments, calculatedData=calculatedData)

    def _computeIndent(self, scimoz, indentStyle, continueComments, style_info,
                       calculatedData):
        non_ws_tokens = calculatedData['non_ws_tokens']
        if not self._lookingAtReturnFunction(non_ws_tokens, style_info):
            return None
        tok0 = calculatedData['tokens'][0]
        if tok0.style in style_info._default_styles:
            currWSLen = len(tok0.text.expandtabs(scimoz.tabWidth))
            newWSLen = currWSLen + scimoz.indent
        else:
            newWSLen = scimoz.indent
        return scimozindent.makeIndentFromWidth(scimoz, newWSLen)

    def _lookingAtReturnFunction(self, non_ws_tokens, style_info):
        return (len(non_ws_tokens) >= 2
                and non_ws_tokens[0].style in style_info._keyword_styles
                and non_ws_tokens[0].text == "return"
                and non_ws_tokens[1].style in style_info._keyword_styles
                and non_ws_tokens[1].text == "function")

class KoLuaLinter(object):
    _com_interfaces_ = [components.interfaces.koILinter]
    _reg_clsid_ = "{8892d2ab-a76c-4512-a02f-a0b31b4ee124}"
    _reg_contractid_ = "@activestate.com/koLinter?language=Lua;1"
    _reg_categories_ = [
         ("category-komodo-linter", 'Lua'),
         ]
    
    def __init__(self):
        import which
        try:
            self._luac = which.which("luac")
            self._cmd_start = [self._luac, "-p"]
        except which.WhichError:
            self._luac = None
    
    def lint(self, request):
        if self._luac is None:
            return
        text = request.content.encode(request.encoding.python_encoding_name)
        return self.lint_with_text_aux(request, text)
        
    def lint_with_text(self, request, text):
        """This routine exists only if someone uses Lua in a multi-lang document
        """
        if self._luac is None:
            return
        return self.lint_with_text_aux(request, text)
    
    _ptn_err = re.compile(r'.*?:.*?:(\d+)\s*:\s*(.*)')
    def lint_with_text_aux(self, request, text):
        cwd = request.cwd or None
        extension = ".lua"
        return runGenericLinter(text, extension, self._cmd_start,
                                [self._ptn_err], [],
                                cwd=cwd, useStderr=True)
        
    
