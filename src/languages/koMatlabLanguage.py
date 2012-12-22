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
from koLanguageServiceBase import KoLexerLanguageService

sci_constants = components.interfaces.ISciMoz

class koMatlabLanguage(KoLanguageKeywordBase):
    name = "Matlab"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{913BAE69-8E17-4c91-B855-687F0A34CFF6}"
    _reg_categories_ = [("komodo-language", name)]

    defaultExtension = ".m.matlab"
    extraFileAssociations = ['*.m', '*.matlab']
    commentDelimiterInfo = { "line": [ "%", "#" ]  }
    supportsSmartIndent = "keyword"
    # See comment in koLuaLanguage.py for why some keywords are in both
    # _indenting_statements and _keyword_dedenting_keywords
    _indenting_statements = ['function', 'if', 'for', 'parfor',
                             'while', 'else', 'do',
                             'elseif',
                             'switch', 'case', 'otherwise']
    _dedenting_statements = ['break', 'continue', 'return', 'error']
    _keyword_dedenting_keywords = ['end', 'else', 'elseif',
                                   'case', 'otherwise', 'until']

    _keywords = """break case catch classdef continue else elseif end error for
                function global if otherwise parfor persistent return
                spmd switch try while""".split()
    sciLexer = components.interfaces.ISciMoz.SCLEX_MATLAB

    def __init__(self):
        KoLanguageKeywordBase.__init__(self)
        self._style_info.update(
            _block_comment_styles = [sci_constants.SCE_MATLAB_COMMENT,],
            _indent_styles = [sci_constants.SCE_MATLAB_OPERATOR],
            _variable_styles = [sci_constants.SCE_MATLAB_IDENTIFIER],
            _lineup_close_styles = [sci_constants.SCE_MATLAB_OPERATOR],
            _lineup_styles = [sci_constants.SCE_MATLAB_OPERATOR],
            _keyword_styles = [sci_constants.SCE_MATLAB_KEYWORD],
            _default_styles = [sci_constants.SCE_MATLAB_DEFAULT],
            _ignorable_styles = [sci_constants.SCE_MATLAB_COMMENT,
                                 sci_constants.SCE_MATLAB_NUMBER],
            )

    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(self.sciLexer)
            self._lexer.setKeywords(0, self._keywords)
            self._lexer.supportsFolding = 1
        return self._lexer

    # matches:
    # function [output] = name(input)
    # classdef name < super
    # %% cell title
    namedBlockDescription = 'Matlab functions and classes'
    namedBlockRE = r'(?:\b(?:function|classdef)\s+\w+|^\s*%%\s+\w+.*)'
    searchURL = "http://www.mathworks.com/help/search/doc/en/?qdoc=%W"

    sample = r"""function b = acyclic(adj_mat, directed)
% ACYCLIC Returns true iff the graph has no (directed) cycles.
% b = acyclic(adj_mat, directed)

adj_mat = double(adj_mat);
if nargin < 2, directed = 1; end

!echo this is a matlab command
if directed
  R = reachability_graph(adj_mat);
  b = ~any(diag(R)==1);
else
  [d, pre, post, cycle] = dfs(adj_mat,[],directed);
  b = ~cycle;    
end
"""


class koOctaveLanguage(koMatlabLanguage):
    name = "Octave"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{d738c609-0897-4dbe-bfd4-d7037deb0ed2}"
    _reg_categories_ = [("komodo-language", name)]

    defaultExtension = ".m"
    commentDelimiterInfo = { "line": [ "#", "%" ]  }

    _keywords = """break case catch continue else elseif end
                   endif endfor endwhile endfunction endparfor
               error end_try_catch
                end_unwind_protect endfor endif endswitch endwhile
                for function global if otherwise persistent
                return switch try until unwind_protect unwind_protect_cleanup
                while""".split()
    sciLexer = components.interfaces.ISciMoz.SCLEX_OCTAVE

    def __init__(self):
        koMatlabLanguage.__init__(self)
        # Don't use += or you'll continue to work with the parent class's
        # arrays.
        self._indenting_statements = (self._indenting_statements
                                      + ['try', 'catch', 'unwind_protect',
                                         'unwind_protect_cleanup',])
        self._dedenting_statements = (self._dedenting_statements
                                      + ['unwind_protect_cleanup',])
        self._keyword_dedenting_keywords = (self._keyword_dedenting_keywords
                                            + ['catch',
                                               'end_try_catch',
                                               'end_unwind_protect',
                                               'endfor',
                                               'endfunction',
                                               'endif',
                                               'endparfor',
                                               'endswitch',
                                               'endwhile',
                                               'unwind_protect_cleanup',
                                               ])
