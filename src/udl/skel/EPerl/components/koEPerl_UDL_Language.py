#!python
# Copyright (c) 2000-2011 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

# Komodo Eperl language service.

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

log = logging.getLogger("koEperlLanguage")
log.setLevel(logging.DEBUG)

def registerLanguage(registry):
    log.debug("Registering language Eperl")
    registry.registerLanguage(KoEperlLanguage())

class KoEperlLanguage(koHTMLLanguageBase):
    log.debug("**************** Define EPerl class")
    name = "EPerl"
    lexresLangName = "EPerl"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" % name
    _reg_clsid_ = "{ec34f812-d8c3-4b55-96b5-0601e659208a}"
    defaultExtension = '.ep'
    searchURL = "http://mojolicio.us/perldoc"

    lang_from_udl_family = {'CSL': 'JavaScript', 'TPL': 'EPerl', 'M': 'HTML', 'CSS': 'CSS'}

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
        log.debug("**************** Instantiate EPerl class")
        koHTMLLanguageBase.__init__(self)
        self.matchingSoftChars["`"] = ("`", self.softchar_accept_matching_backquote)
        self._style_info.update(
            _indent_styles = [components.interfaces.ISciMoz.SCE_UDL_TPL_OPERATOR]
            )
        self._indent_chars = u'{}'
        self._indent_open_chars = u'{'
        self._indent_close_chars = u'}'
