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
    defaultExtension = '.ep'
    searchURL = "http://mojolicio.us/perldoc"

    lang_from_udl_family = {'CSL': 'JavaScript', 'TPL': 'epMojo', 'M': 'HTML', 'CSS': 'CSS'}

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

    def get_linter(self):
        if not hasattr(self, "_linter"):
            self._linter = self._get_linter_from_lang(self.name)
        return self._linter

class KoEpMojoLinter(object):
    _com_interfaces_ = [components.interfaces.koILinter]
    _reg_desc_ = "epMojo Template Linter"
    _reg_clsid_ = "{3b69f94f-4fb6-47bb-a387-9d3ac372195a}"
    _reg_contractid_ = "@activestate.com/koLinter?language=epMojo;1"
    _reg_categories_ = [
        ("category-komodo-linter", 'epMojo'),
    ]


    def __init__(self):
        self._perl_linter = components.classes["@activestate.com/koLinter?language=Perl;1"].\
                            getService(components.interfaces.koILinter);
        
    def _extractPerlCode(self, text):
        # Lint only the Perl code
        if not text.endswith("\n"):
            text += "\n";
        newTextBlocks = []
        skip_ptn = re.compile(r'[^\r\n<%]+')
        leading_name = re.compile(r'\s+(\w+)')
        neededSubs = {}
        # Now save only the Perl code.
        c = None
        while text:
            m = skip_ptn.match(text)
            if m:
                amtToSkip = m.span(0)[1]
                newTextBlocks.append(amtToSkip * " ")
                text = text[amtToSkip:]
                prev_c = None
                continue
            prev_c = c
            c = text[0]
            if c in ('\r', '\n'):
                newTextBlocks.append(c)
                text = text[1:]
            elif c == '%' and prev_c in ('\n', None):
                if len(text) == 1:
                    break
                text = text[1:]
                while text[0] == '=':
                    text = text[1:]
                idx = text.find("\n")
                newText = text[:idx + 1]
                m = leading_name.match(newText)
                if m:
                    term = m.group(1)
                    if term not in neededSubs:
                        neededSubs[term] = None
                        newTextBlocks.append("sub %s; " % (term,))
                newTextBlocks.append(text[:idx + 1])
                text = text[idx + 1:]
                c = '\n'
            elif text.startswith("<%"):
                text = text[2:]
                endPos = text.find("%>")
                if endPos == -1:
                    endPos = len(text)
                    skipAmt = 0
                else:
                    skipAmt = 2
                if text.startswith("#"):
                    # Multi-line comment
                    eolsOnly = re.compile(r'[^\r\n]').subn(text[:endPos + 1  - skipAmt])
                    newTextBlocks.append(eolsOnly)
                else:
                    if text.startswith("="):
                        text = text[1:]
                        endPos -= 1
                        newTextBlocks.append("print ")
                    if text.startswith("="):
                        text = text[1:]
                        endPos -= 1
                    newTextBlocks.append(text[:endPos + 1 - skipAmt] + ";")
                text = text[endPos + 1:]
                c = '>'
            else:
                #print("No match at %s..." % text[:24])
                newTextBlocks.append(' ')
                text = text[1:]
        # end while
        return "".join(newTextBlocks)
        
    def lint(self, request):
        # Lint only the Perl code
        text = request.content.encode(request.encoding.python_encoding_name)
        newText = self._extractPerlCode(text)
        return self._perl_linter.lint_with_text(request, newText)
