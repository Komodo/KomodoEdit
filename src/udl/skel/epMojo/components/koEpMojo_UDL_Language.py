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
                            getService(components.interfaces.koILinter)
        self._html_linter = components.classes["@activestate.com/koLinter?language=HTML;1"].\
                            getService(components.interfaces.koILinter)
        
    epMatcher = re.compile(r'''(
                                (?:<%(?:.|[\r\n])*?%>)   # Anything in <%...%>
                                |(?:^%.*)                # % to eol is one-line of Perl
                                |(?:\r?\n)               # Newline
                                |(?:(?:<(?!%)|[^<\n]+)+) # Most other non-Perl
                                |.)''',                  # Catchall
                                re.MULTILINE|re.VERBOSE)
    _leading_name = re.compile(r'\s+(\w+)')
    def _extractPerlPart(self, text):
        parts = self.epMatcher.findall(text)
        if not parts:
            return "", text
        i = 0
        lim = len(parts)
        perlTextParts = []
        htmlTextParts = []
        eols = ("\n", "\r\n")
        neededSubs = {}
        while i < lim:
            part = parts[i]
            if part in eols:
                perlTextParts.append(part)
                htmlTextParts.append(part)
            elif part.startswith("<%"):
                # Watch out for block comments
                perlTextParts.append(self._fixTemplateMarkup(part))
                htmlTextParts.append(self._spaceOutNonNewlines(part))
            elif part.startswith("%") and (i == 0 or parts[i - 1].endswith("\n")):
                part = part[1:]
                m = self._leading_name.match(part)
                if m:
                    term = m.group(1)
                    if term not in neededSubs:
                        neededSubs[term] = None
                        perlTextParts.append("sub %s; " % (term,))
                perlTextParts.append(' ' + part + ";")
                htmlTextParts.append(' ' + self._spaceOutNonNewlines(part))
            else:
                perlTextParts.append(self._spaceOutNonNewlines(part))
                htmlTextParts.append(part)
            i += 1
        return "".join(perlTextParts), "".join(htmlTextParts)
        
    _nonNewlineMatcher = re.compile(r'[^\r\n]')
    def _spaceOutNonNewlines(self, markup):
        return self._nonNewlineMatcher.sub(' ', markup)

    _markupMatcher = re.compile(r'\A<%(#|={0,2})(.*?)(=?)(?:%>)?\Z', re.DOTALL)
    def _fixTemplateMarkup(self, markup):
        m = self._markupMatcher.match(markup)
        if not m:
            return markup
        finalText = '  '
        leadingControlText = m.group(1)
        payload = m.group(2)
        trailingControlText = m.group(3)
        if leadingControlText == '#':
            finalText += '#' + payload.replace("\n", "\n#")
        elif leadingControlText.startswith("="):
            finalText += "print " + payload + ";"
        else:
            finalText += payload + ";"
        return finalText
        
    def lint(self, request):
        # Lint only the Perl code
        text = request.content.encode(request.encoding.python_encoding_name)
        perlText, htmlText = self._extractPerlPart(text)
        if perlText.strip():
            log.debug("Go perl lint {%s}", perlText)
            lintResults1 = self._resetLines(self._perl_linter.lint_with_text(request, perlText),
                                            text)
        else:
            lintResults1 = None
        if htmlText.strip():
            lintResults2 = self._html_linter.lint_with_text(request, htmlText)
        else:
            lintResults2 = None
        if lintResults1 is None or lintResults1.getNumResults() == 0:
            return lintResults2
        elif lintResults2 is None or lintResults2.getNumResults() == 0:
            return lintResults1
        else:
            #return UnwrapObject(lintResults1).addResults(UnwrapObject(lintResults2))
            return lintResults1.addResults(lintResults2)

    def _resetLines(self, lintResults, text):
        lines = text.splitlines()
        fixedResults = koLintResults()
        for res in lintResults.getResults():
            try:
                targetLine = lines[res.lineEnd - 1]
            except IndexError:
                log.exception("can't index %d lines at %d", len(lines), res.lineEnd - 1)
                pass # Keep the original lintResult
            else:
                if res.columnEnd > len(targetLine):
                    res.columnEnd = len(targetLine)
            fixedResults.addResult(res)
        return fixedResults
