#!python
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

# Komodo epMojo language service.

import logging
import os, sys, re
from os.path import join, dirname, exists
import tempfile
import process
import koprocessutils

from xpcom import components, nsError, ServerException
from xpcom.server import UnwrapObject, WrapObject

from koXMLLanguageBase import koHTMLLanguageBase

from koLintResult import KoLintResult
from koLintResults import koLintResults

import scimozindent

log = logging.getLogger("koEpMojoLanguage")
#log.setLevel(logging.DEBUG)

def registerLanguage(registry):
    log.debug("Registering language epMojo")
    registry.registerLanguage(koEpMojoLanguage())

class koEpMojoLanguage(koHTMLLanguageBase):
    name = "epMojo"
    lexresLangName = "epMojo"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" % name
    _reg_clsid_ = "{ec34f812-d8c3-4b55-96b5-0601e659208a}"
    _reg_categories_ = [("komodo-language", name)]
    defaultExtension = '.ep'
    searchURL = "http://mojolicio.us/perldoc"

    lang_from_udl_family = {'CSL': 'JavaScript', 'TPL': 'epMojo', 'M': 'HTML', 'CSS': 'CSS', 'SSL': 'Perl'}

    sample = """
<!doctype html><html>
  <head><title>Simple</title></head>
  <body>Time: <%= localtime(time) %></body>
</html>
% Perl line
Inline perl:   <% Inline Perl %>, and continue...
<a href="<%= $css . "?q=$action" %>">where do you want to go?</a>
%= Perl expression line, replaced with result
%== Perl expression line, replaced with XML escaped result
%# Comment line, useful for debugging
<% my $block = begin %>
<% my $name = shift; =%>
    Hello <%= $name %>.
<% end %>
<%= $block->('Baerbel') %>
<%= $block->('Wolfgang') %>
"""

    def __init__(self):
        koHTMLLanguageBase.__init__(self)
        self.matchingSoftChars["`"] = ("`", self.softchar_accept_matching_backquote)
        self._style_info.update(
            _indent_styles = [components.interfaces.ISciMoz.SCE_UDL_TPL_OPERATOR]
            )
        self._indent_chars = u'{}'
        self._indent_open_chars = u'{'
        self._indent_close_chars = u'}'

class KoEpMojoLinter(object):
    _com_interfaces_ = [components.interfaces.koILinter]
    _reg_desc_ = "epMojo Template Linter"
    _reg_clsid_ = "{3b69f94f-4fb6-47bb-a387-9d3ac372195a}"
    _reg_contractid_ = "@activestate.com/koLinter?language=epMojo;1"
    _reg_categories_ = [
        ("category-komodo-linter", 'epMojo'),
    ]


    def __init__(self):
        self._koLintService = components.classes["@activestate.com/koLintService;1"].getService(components.interfaces.koILintService)
        self._html_linter = UnwrapObject(self._koLintService.getLinterForLanguage("HTML"))

    _tplPatterns = ("epMojo", re.compile('<%='), re.compile(r'%>\s*\Z', re.DOTALL))
    def lint(self, request):
        return self._html_linter.lint(request, TPLInfo=self._tplPatterns)

    def lint_with_text(self, request, text):
        # With revised html_linter template processing, the html linter will
        # pull out Perl parts and dispatch them to the perl linter, so there's
        # nothing to do here.
        return None
