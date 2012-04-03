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

class koMatlabLanguage(KoLanguageBase):
    name = "Matlab"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{913BAE69-8E17-4c91-B855-687F0A34CFF6}"
    _reg_categories_ = [("komodo-language", name)]

    defaultExtension = ".m.matlab"
    commentDelimiterInfo = { "line": [ "%" ]  }

    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(components.interfaces.ISciMoz.SCLEX_MATLAB)
            self._lexer.setKeywords(0, self._keywords)
        return self._lexer

    _keywords = """break case catch classdef continue else elseif end for
                function global if otherwise parfor persistent return
                spmd switch try while""".split()

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

    _keywords = """break case catch continue do else elseif end
                end_unwind_protect endfor endif endswitch endwhile
                for function endfunction global if otherwise persistent
                return switch try until unwind_protect unwind_protect_cleanup
                while""".split()
