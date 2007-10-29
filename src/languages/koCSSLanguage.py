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

import sciutils

from koLanguageServiceBase import *
sci_constants = components.interfaces.ISciMoz

def registerLanguage(registery):
    registery.registerLanguage(koCSSLanguage())
    
class koCSSLanguage(KoLanguageBase):
    name = "CSS"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "52594294-AF26-414A-9D66-C2B47EF9F015"

    supportsSmartIndent = "brace"
    primary = 1
    defaultExtension = ".css"
    commentDelimiterInfo = {
        "block": [ ("/*", "*/") ],
        "markup": "*",
    }

    searchURL = "http://www.google.com/search?q=site%3Ahttp%3A%2F%2Fwww.w3schools.com%2Fcss+%W"
    
    def __init__(self):
        KoLanguageBase.__init__(self)
        self._style_info.update(
            _indent_styles = [sci_constants.SCE_CSS_OPERATOR],
            _indent_open_styles = [sci_constants.SCE_CSS_OPERATOR],
            _indent_close_styles = [sci_constants.SCE_CSS_OPERATOR],
            _lineup_styles = [sci_constants.SCE_CSS_OPERATOR, sci_constants.SCE_CSS_TAG],
            _lineup_close_styles = [sci_constants.SCE_CSS_OPERATOR],
            _block_comment_styles = [sci_constants.SCE_CSS_COMMENT]
            )

    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(components.interfaces.ISciMoz.SCLEX_CSS)
            self._lexer.setKeywords(0, self._keywords)
            self._lexer.supportsFolding = 1
        return self._lexer

    # Taken from http://mailman.lyra.org/pipermail/scintilla-interest/2002-December/002009.html
    _keywords = [
"ascent",
"azimuth",
"background word-spacing",
"background-attachment",
"background-color",
"background-image",
"background-position",
"background-repeat",
"baseline centerline",
"bbox",
"border",
"border-bottom",
"border-bottom-color",
"border-bottom-style",
"border-bottom-width",
"border-collapse",
"border-color",
"border-color",
"border-left",
"border-left-color",
"border-left-style",
"border-left-width",
"border-right",
"border-right-color",
"border-right-style",
"border-right-width",
"border-spacing",
"border-style",
"border-style",
"border-top",
"border-top-color",
"border-top-style",
"border-width",
"bottom",
"cap-height",
"caption-side",
"clear",
"color",
"counter-increment",
"counter-reset",
"cue",
"cue-after",
"cue-before",
"cursor",
"definition-src",
"descent",
"direction unicode-bidi",
"elevation",
"empty-cells",
"float",
"font",
"font-family",
"font-size",
"font-size-adjust",
"font-stretch",
"font-style",
"font-variant",
"font-weight",
"height",
"left",
"letter-spacing",
"line-height",
"margin",
"margin-bottom",
"margin-left",
"margin-right",
"margin-top",
"marker-offset",
"marks",
"mathline",
"max-height",
"max-width",
"min-height",
"min-width",
"outline",
"outline-color",
"outline-style",
"outline-width",
"overflow clip",
"padding border-top-width",
"padding-bottom",
"padding-left",
"padding-right",
"padding-top",
"page orphans",
"page-break-after",
"page-break-before",
"page-break-inside",
"pause",
"pause-after",
"pause-before",
"pitch",
"pitch-range",
"play-during",
"quotes",
"richness",
"size",
"slope",
"speak",
"speak-header",
"speak-numeral",
"speak-punctuation",
"speech-rate",
"src","panose-1",
"stemh",
"stemv",
"stress",
"table-layout",
"text-align",
"text-decoration",
"text-indent",
"text-shadow",
"text-transform",
"top right",
"topline",
"unicode-range",
"units-per-em",
"vertical-align",
"visibility content",
"voice-family",
"volume",
"widows",
"width",
"widths",
"x-height",
"z-index",
    ]

    def test_scimoz(self, scimoz):
        # Test the auto-indenter
        CSSAutoIndentTestCase.cssObj = self
        testCases = [CSSAutoIndentTestCase]
        sciutils.runSciMozTests(testCases, scimoz)
        
class CSSAutoIndentTestCase(sciutils.SciMozTestCase):
    """Test suite for koCSSLanguage."""

    cssObj = None

    def test_WeLive(self):
        self.assertEqual(1, 1)

    def _do_test_buffer_indent(self, buffer, exp_ind):
        self._setupSciMoz(buffer, "CSS")
        new_ind = self.cssObj.computeIndent(self.scimoz, 'smart', True, self._style_info)
        if not new_ind and exp_ind == '': new_ind = ''
        self.assertEqual(exp_ind, new_ind)

    # Test boundary-conditions on comments at end of buffer

    def test_ai_1(self):
        self._do_test_buffer_indent("/*\n *\n *", " *")
        self._do_test_buffer_indent("/*\n *\n **", " **")

    def test_ai_2(self):
        self._do_test_buffer_indent("/*\n *\n */", "")

    def test_ai_3(self):
        # Put a space after the /, so we aren't at the end anymore
        self._do_test_buffer_indent("/*\n *\n */ ", "")

    def test_ai_4(self):
        # Put a newline after the indent
        self._do_test_buffer_indent("/*\n *\n */\n", "")

    def test_ai_5(self):
        # Verify open-brace indents
        self._do_test_buffer_indent("{", ' ' * self.scimoz.indent)
