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

"""Base class for UDL-based language service classes.

See 'src/udl/...' for more info.
"""

import copy
import re
import os
from os.path import join, exists, basename, splitext
import logging
from glob import glob
from pprint import pprint

from xpcom import components
from xpcom.server import UnwrapObject
from koLanguageServiceBase import KoLanguageBase, KoLexerLanguageService, \
                                  KoCommenterLanguageService, sendStatusMessage, \
                                  koLangSvcStyleInfo

log = logging.getLogger("KoUDLLanguageBase")
#log.setLevel(logging.DEBUG)

ScintillaConstants = components.interfaces.ISciMoz

def udl_family_from_style(style):
    if (ScintillaConstants.SCE_UDL_M_DEFAULT <= style
          <= ScintillaConstants.SCE_UDL_M_UPPER_BOUND):
        return "M"
    elif (ScintillaConstants.SCE_UDL_CSS_DEFAULT <= style
          <= ScintillaConstants.SCE_UDL_CSS_UPPER_BOUND):
        return "CSS"
    elif (ScintillaConstants.SCE_UDL_CSL_DEFAULT <= style
          <= ScintillaConstants.SCE_UDL_CSL_UPPER_BOUND):
        return "CSL"
    elif (ScintillaConstants.SCE_UDL_SSL_DEFAULT <= style
          <= ScintillaConstants.SCE_UDL_SSL_UPPER_BOUND):
        return "SSL"
    elif (ScintillaConstants.SCE_UDL_TPL_DEFAULT <= style
          <= ScintillaConstants.SCE_UDL_TPL_UPPER_BOUND):
        return "TPL"
    else:
        raise ValueError("unknown UDL style: %r" % style)
        
_default_styles = (ScintillaConstants.SCE_UDL_M_DEFAULT,
                   ScintillaConstants.SCE_UDL_CSS_DEFAULT,
                   ScintillaConstants.SCE_UDL_CSL_DEFAULT,
                   ScintillaConstants.SCE_UDL_SSL_DEFAULT,
                   ScintillaConstants.SCE_UDL_TPL_DEFAULT);

# When a newline is typed at a transition point, with
# one family to the left of the newline, and the newline
# belonging to another family, this dict indicates which
# family to use.

# Uses are currently for auto-indenting.
# Given a family in the left style, index
# with the family on the right to determine
# which family wins.  "*" as an index indicates
# the default, "*" on the right indicates to use
# the right-hand family.

# Default outcome is to return the LHS family

_family_feud_outcomes = {
    'indent' :
    { "M" : { "CSS" : "CSS", # <style...><|><CR>  *bug 57688: problem here *
              "CSL" : "CSL", # <script...><|><CR> * bug 57688
              "SSL" : "M",  # Don't see where this happens -- TPL always
                            # separates markup and SSL
              "TPL" : "M",  # markup...<|><%
              },
      
      # For CSS and CSL, usually transitions can happen only
      # at an end-tag, and then we move into M, so always
      # accept the RHS.
      
      # Currently there is no transition from CSS or CSL (JS)
      # to the *end* -- you always need a tag, so the transition
      # to M is implicit.  However some languages support embedding
      # TPL or SSL code inside JS expressions, so we'll always let
      # that language win.

      # css code...<|></style>
      # js code...<|></script>
      # auto-indent in above two cases will be wrong, but there is
      # no way to do it correctly anyway.  Most people put the
      # style and script end-tags on their own line.
      "CSS" : { "*" : "*" },
      "CSL" : { "*" : "*" },
      
      # SSL: always return SSL
      # So we don't need any code here
      "SSL" : { # "TPL" : "SSL", # some code<|>%> -- stay in SSL
                "*" : "SSL",   # some code<|>??? -- stay in SSL
                },
      # TPL: always return TPL
      # We don't need any code here either
      "TPL" : { # "SSL" : "TPL", # <%<|>code -- go with TPL
                # "M" : "TPL",   # %><|><tag> -- stay with TPL
                "*" : "TPL",   # %>??? - can't happen
                },
      },
    }

_re_bad_filename_char = re.compile(r'([% 	\x80-\xff])')
def _lexudl_path_escape(m):
    return '%%%02X' % ord(m.group(1))
def _urlescape(s):
    """
    I do my own urlescape because the unescape is done in the C++ lexer
    in scintilla/src/LexUDL.cxx.  They need to match.
    """
    return _re_bad_filename_char.sub(_lexudl_path_escape, s)


class KoUDLLanguage(KoLanguageBase):
    lang_from_udl_family = {'CSL': '', 'TPL': '', 'M': '', 'CSS': '', 'SSL': ''}
    # Common sublanguages used in UDL languages go here.
    # First the define the base style objects, then specify
    # for commonly used languages.
    # Most SSL-based languages will need to define their own styles.

    # Note: there is no _lineup_open_styles in the style list.

    default_tpl_style_info = koLangSvcStyleInfo(
            _indent_styles = [ScintillaConstants.SCE_UDL_TPL_OPERATOR],
            _indent_open_styles = [ScintillaConstants.SCE_UDL_TPL_OPERATOR],
            _indent_open_opening_styles = [ScintillaConstants.SCE_UDL_TPL_OPERATOR],
            _indent_close_styles = [ScintillaConstants.SCE_UDL_TPL_OPERATOR],
            _lineup_close_styles = [ScintillaConstants.SCE_UDL_TPL_OPERATOR],
            _lineup_styles = [ScintillaConstants.SCE_UDL_TPL_OPERATOR],
            _comment_styles=[ScintillaConstants.SCE_UDL_TPL_COMMENT,
                             ScintillaConstants.SCE_UDL_TPL_COMMENTBLOCK],
            _block_comment_styles=[ScintillaConstants.SCE_UDL_TPL_COMMENT,
                                   ScintillaConstants.SCE_UDL_TPL_COMMENTBLOCK],
            _keyword_styles = [ScintillaConstants.SCE_UDL_TPL_WORD],
            _number_styles = [ScintillaConstants.SCE_UDL_TPL_NUMBER],
            _string_styles = [ScintillaConstants.SCE_UDL_TPL_STRING],
            _variable_styles = [ScintillaConstants.SCE_UDL_TPL_VARIABLE],
            _default_styles = [ScintillaConstants.SCE_UDL_TPL_DEFAULT]
            )
    default_ssl_style_info = koLangSvcStyleInfo(
            _indent_styles = [ScintillaConstants.SCE_UDL_SSL_OPERATOR],
            _indent_open_styles = [ScintillaConstants.SCE_UDL_SSL_OPERATOR],
            _indent_close_styles = [ScintillaConstants.SCE_UDL_SSL_OPERATOR],
            _lineup_close_styles = [ScintillaConstants.SCE_UDL_SSL_OPERATOR],
            _lineup_styles = [ScintillaConstants.SCE_UDL_SSL_OPERATOR],
            _comment_styles=[ScintillaConstants.SCE_UDL_SSL_COMMENT,
                             ScintillaConstants.SCE_UDL_SSL_COMMENTBLOCK],
            _block_comment_styles=[ScintillaConstants.SCE_UDL_SSL_COMMENT,
                                   ScintillaConstants.SCE_UDL_SSL_COMMENTBLOCK],
            _keyword_styles = [ScintillaConstants.SCE_UDL_SSL_WORD],
            _number_styles = [ScintillaConstants.SCE_UDL_SSL_NUMBER],
            _string_styles = [ScintillaConstants.SCE_UDL_SSL_STRING],
            _regex_styles = [ScintillaConstants.SCE_UDL_SSL_REGEX],
            _variable_styles = [ScintillaConstants.SCE_UDL_SSL_VARIABLE],
            _default_styles = [ScintillaConstants.SCE_UDL_SSL_DEFAULT],
            
            # These sets are used only by Ruby (as of 2006-10-27)
            _ignorable_styles = [ScintillaConstants.SCE_UDL_SSL_DEFAULT,
                                 ScintillaConstants.SCE_UDL_SSL_COMMENT,
                                 ScintillaConstants.SCE_UDL_SSL_COMMENTBLOCK,
                                 ],
            _multiline_styles = [ScintillaConstants.SCE_UDL_SSL_STRING]
            )
    default_csl_style_info = koLangSvcStyleInfo(
            _indent_styles = [ScintillaConstants.SCE_UDL_CSL_OPERATOR],
            _indent_open_styles = [ScintillaConstants.SCE_UDL_CSL_OPERATOR],
            _indent_close_styles = [ScintillaConstants.SCE_UDL_CSL_OPERATOR],
            _lineup_close_styles = [ScintillaConstants.SCE_UDL_CSL_OPERATOR],
            _lineup_styles = [ScintillaConstants.SCE_UDL_CSL_OPERATOR],
            _comment_styles=[ScintillaConstants.SCE_UDL_CSL_COMMENT,
                             ScintillaConstants.SCE_UDL_CSL_COMMENTBLOCK],
            _block_comment_styles=[ScintillaConstants.SCE_UDL_CSL_COMMENTBLOCK],
            _keyword_styles = [ScintillaConstants.SCE_UDL_CSL_WORD],
            _number_styles = [ScintillaConstants.SCE_UDL_CSL_NUMBER],
            _string_styles = [ScintillaConstants.SCE_UDL_CSL_STRING],
            _default_styles = [ScintillaConstants.SCE_UDL_CSL_DEFAULT]
            )
    default_css_style_info = koLangSvcStyleInfo(
            _indent_styles = [ScintillaConstants.SCE_UDL_CSS_OPERATOR],
            _indent_open_styles = [ScintillaConstants.SCE_UDL_CSS_OPERATOR],
            _indent_close_styles = [ScintillaConstants.SCE_UDL_CSS_OPERATOR],
            _lineup_close_styles = [ScintillaConstants.SCE_UDL_CSS_OPERATOR],
            _lineup_styles = [ScintillaConstants.SCE_UDL_CSS_OPERATOR],
            _comment_styles=[ScintillaConstants.SCE_UDL_CSS_COMMENT],
            _block_comment_styles=[ScintillaConstants.SCE_UDL_CSS_COMMENT],
            
            _keyword_styles = [ScintillaConstants.SCE_UDL_CSS_WORD],
            _string_styles = [ScintillaConstants.SCE_UDL_CSS_STRING],
            _number_styles = [ScintillaConstants.SCE_UDL_CSS_NUMBER],
            _default_styles = [ScintillaConstants.SCE_UDL_CSS_DEFAULT]
            )
    default_markup_style_info = koLangSvcStyleInfo(
               _indent_styles = [ScintillaConstants.SCE_UDL_M_STAGO,
                                 ScintillaConstants.SCE_UDL_M_STAGC,
                                 ScintillaConstants.SCE_UDL_M_EMP_TAGC,
                                 ScintillaConstants.SCE_UDL_M_ETAGO,
                                 ScintillaConstants.SCE_UDL_M_ETAGC,
                                 ],
               _indent_open_styles = [ScintillaConstants.SCE_UDL_M_STAGO],
               _indent_close_styles = [ScintillaConstants.SCE_UDL_M_ETAGC],
               _indent_open_opening_styles = [ScintillaConstants.SCE_UDL_M_STAGO],
               _comment_styles=[ScintillaConstants.SCE_UDL_M_COMMENT],
               _block_comment_styles = [ScintillaConstants.SCE_UDL_M_COMMENT],
               _string_styles = [ScintillaConstants.SCE_UDL_M_STRING],
               _default_styles = [ScintillaConstants.SCE_UDL_M_DEFAULT]
               )

    style_info_by_family = {"M" : default_markup_style_info,
                            "CSS" : default_css_style_info,
                            "CSL" : default_csl_style_info,
                            "SSL" : default_ssl_style_info,
                            "TPL" : default_tpl_style_info,
                            }

    supportsFolding = 1

    def __init__(self):
        # log.debug("creating a KoUDLLanguage(%s)[clsid %s], lang_from_udl_family=%r", self.name, self._reg_clsid_, self.lang_from_udl_family)
        if self.name:
            import styles
            styles.addNewUDLLanguage(self.name)
        self._lexresPathFromLexresLangName = None
        self._lexerFromLanguageName = {}
        self._style_info_from_udl_family = {}
        self._lang_svc_from_udl_family = {}
        KoLanguageBase.__init__(self)

    def getSubLanguages(self):
        return self.lang_from_udl_family.values()
    
    def getLanguageForFamily(self, family):
        return self.lang_from_udl_family.get(family, self.name)

    def isUDL(self):
        return True

    def _genLexerDirs(self):
        """Return all possible lexer resource directories (i.e. those ones
        that can include compiled UDL .lexres files).

        It yields directories that should "win" first.

        This doesn't filter out non-existant directories.
        """
        from directoryServiceUtils import getExtensionLexerDirs
        koDirs = components.classes["@activestate.com/koDirs;1"] \
            .getService(components.interfaces.koIDirs)

        if exists(join(koDirs.userDataDir, "lexers")):
            yield join(koDirs.userDataDir, "lexers")    # user
        for extensionLexerDir in getExtensionLexerDirs():
            yield extensionLexerDir                     # extensions
        if exists(join(koDirs.commonDataDir, "lexers")):
            yield join(koDirs.commonDataDir, "lexers")  # site/common
        if exists(join(koDirs.supportDir, "lexers")):
            yield join(koDirs.supportDir, "lexers")     # factory

    # One time call - to find the lexer resources.
    def _findLexerResources(self):
        self._lexresPathFromLexresLangName = {}
        for lexerDir in self._genLexerDirs():
            for lexresPath in glob(join(lexerDir, "*.lexres")):
                lexresLangName = splitext(basename(lexresPath))[0]
                self._lexresPathFromLexresLangName[lexresLangName] = lexresPath
        if log.isEnabledFor(logging.DEBUG):
            log.debug("lexer resources:")
            for item in self._lexresPathFromLexresLangName.items():
                log.debug("    %s -> %s", *item)

    # Handle situations where we're on the boundary 
    # with a default EOL on the right, and something
    # else on the left.  Sometimes we want the winning
    # family, sometimes just its position.

    # Actually we don't call _calc_family_winner yet.

    #def _calc_family_winner(lhs, rhs, lookup_type='indent'):
    #    assert lhs != rhs
    #    table = _family_feud_outcomes.get(lookup_type)
    #    if table is None:
    #        return rhs
    #    feud = table.get(lhs)
    #    if feud is None: return rhs
    #    winner = feud.get(rhs) or feud.get("*")
    #    if winner is None:
    #        return lhs
    #    elif winner == "*":
    #        return rhs
    #    return winner

    # This one returns -1 to look to the left, 0 for current pos
    
    # Precondition: assert lhs != rhs
    def _calc_family_winner_posn(lhs, rhs, lookup_type='indent'):
        table = _family_feud_outcomes.get(lookup_type)
        if table is None:
            return 0
        feud = table.get(lhs)
        if feud is None: return 0
        winner = feud.get(rhs) or feud.get("*")
        if winner is None:
            return -1
        elif winner == "*":
            return 0
        return winner == lhs and -1 or 0

    # Don't do family resolution on every character,
    # only for chars colored with the family's default style.
    # pos refers to the character just typed.

    def _get_meaningful_style(self, scimoz, pos):
        styleRight = scimoz.getStyleAt(pos)
        if pos == 0 or styleRight not in _default_styles:
            return styleRight
        styleLeft = scimoz.getStyleAt(pos-1)
        if styleRight == styleLeft:
            return styleRight
        lhs_family = udl_family_from_style(styleLeft)
        rhs_family = udl_family_from_style(styleRight)
        if lhs_family == rhs_family:
            return styleRight
        adj = self._calc_family_winner_posn(styleLeft, styleRight)
        if adj == 0:
            #log.debug("_get_meaningful_style - sticking with style %d", styleRight)
            return styleRight
        else:
            new_pos = pos + adj
            winningStyle = scimoz.getStyleAt(new_pos)
            #log.debug("_get_meaningful_style - ignore style %d, pos %d -- use %d@%d", styleRight, pos, winningStyle, new_pos)
            return winningStyle
            
        return winningStyle

    def get_lexer(self):
        if self._lexresPathFromLexresLangName is None:
            self._findLexerResources()

        languageName = self.name
        if languageName not in self._lexerFromLanguageName:
            lexer = KoLexerLanguageService()
            lexer.setLexer(components.interfaces.ISciMoz.SCLEX_UDL)
            try:
                lexresPath = self._lexresPathFromLexresLangName[self.lexresLangName]
            except KeyError:
                log.warn("no lexer resource was found for '%s' language "
                         "(no '%s.lexres' in lexers dirs)", languageName,
                         self.lexresLangName)
                lexer.supportsFolding = 0
                lexer.setKeywords(0, [])
            else:
                #XXX Use properties instead
                log.debug("loading lexres for '%s' (%s)", languageName,
                          lexresPath)
                lexer.supportsFolding = self.supportsFolding
                lexer.setKeywords(0, [_urlescape(lexresPath)])
            self._lexerFromLanguageName[languageName] = lexer

        #XXX Not sure if assignment to self._lexer is necessary.
        self._lexer = self._lexerFromLanguageName[languageName]
        return self._lexer
    
    # XXX quick hack to provide the most basic level of service
    def getDefaultService(self, lang_to_try, serviceInterface):
        # get a language service for this language if it exists
        registryService = components.classes['@activestate.com/koLanguageRegistryService;1'].\
            getService(components.interfaces.koILanguageRegistryService)
        for language in lang_to_try:
            # log.debug("get_linter(%s), trying udl language %s", self.name, language)
            if not language: continue
            if language == self.name:
                # We already checked self. If we try to check it again we'll
                # go into a recursive loop. Bug 81066.
                continue
            try:
                return registryService.getLanguage(language).\
                            getLanguageService(serviceInterface)
            except Exception, e:
                # continue to next language
                log.exception(e)
        return None

    def get_interpreter(self):
        if self._interpreter is None:
            lang_to_try = [self.lang_from_udl_family.get("M", None),
                           self.lang_from_udl_family.get("SSL", None)]
            self._interpreter = self.getDefaultService(lang_to_try, components.interfaces.koIAppInfoEx)
        return self._interpreter

    def get_commenter(self):
        if self._commenter is None:
            self._commenter = KoUDLCommenterLanguageService(self)
        return self._commenter

    #### Routines for setting up style-info and delegating
    #### calls to the language-service base class.

    def _getLangSvcAndStyleInfoFromScimoz(self, scimoz, use_previous=False):
        """ keyPressed events have scimoz.currentPos pointing to the right of the
        entered character, but when we're getting the underlying language service
        we want it for the character just typed, not the position between that
        character and whatever follows.  This is why the use_previous flag is
        there.
        """
        pos = scimoz.currentPos
        if use_previous:
            pos = scimoz.positionBefore(pos)
        doclen = scimoz.textLength
        if pos >= doclen:
            log.debug("pos:%d, doclen:%d", pos, doclen)
            pos = doclen - 1
        style = self._get_meaningful_style(scimoz, pos)
        #log.debug("_getLangSvcAndStyleInfoFromScimoz:style(%d) => %d", pos, style)
        return self.getLangSvcAndStyleInfoFromStyle(style)

    # Also called from koLanguageCommandHandler.p.py
    def getLangSvcAndStyleInfoFromStyle(self, style):
        family = udl_family_from_style(style)
        #log.debug("getLangSvcAndStyleInfoFromStyle: style %d=> family %r", style, family)
        lang_svc = self._getLangSvcFromFamily(family)
        #log.debug("lang_svc(%r, %s) => %s", getattr(self, 'name', '?'), family, lang_svc)
        if lang_svc:
            return (lang_svc, self.style_info_by_family[family])
        else:
            return (self, self._style_info)

    def _getLangSvcFromFamily(self, family):
        if family not in self._lang_svc_from_udl_family:
            language = self.lang_from_udl_family.get(family)
            if not language:
                log.debug("No language defined for family %s", family)
                return None
            #log.debug("UDL: found language %s for family %s", language, family)
            try:
                # get a language service for this language if it exists
                registryService = components.classes['@activestate.com/koLanguageRegistryService;1'].\
                    getService(components.interfaces.koILanguageRegistryService)
                langObj = UnwrapObject(registryService.getLanguage(language))
                self._lang_svc_from_udl_family[family] = langObj
            except KeyError, e:
                log.exception(e)
                self._lang_svc_from_udl_family[family] = None
        return self._lang_svc_from_udl_family[family]

    # The XPCOM interface got us here, but now we call the
    # Python only method obj._foo(args, styleInfo) instead of obj.foo(args)
    
    def computeIndent(self, scimoz, indentStyle, continueComments):
        if continueComments:
            return KoLanguageBase.computeIndent(self, scimoz, indentStyle, continueComments)
        (lang_svc_obj, style_info) = self._getLangSvcAndStyleInfoFromScimoz(scimoz)
        if lang_svc_obj == self:
            # Bug 90371: Avoid infinite recursion.  Always call towards the superclass.
            # Bug 93387: Call the superclass only if _getLangSvcAndStyleInfoFromScimoz
            #           gives the same language service as the composite UDL one.
            return KoLanguageBase._computeIndent(self, scimoz, indentStyle, continueComments, style_info)
        else:
            return lang_svc_obj._computeIndent(scimoz, indentStyle, continueComments, style_info)

    def getBraceIndentStyle(self, ch, style):
        (lang_svc_obj, style_info) = self.getLangSvcAndStyleInfoFromStyle(style)
        return lang_svc_obj._getBraceIndentStyle(ch, style, style_info)

    def guessIndentation(self, scimoz, tabWidth, defaultUsesTabs):
        """Use fold-level based indentation, since the first
        100 lines probably span more than one sub-language, and
        the standard guesser doesn't make allowances for switching in
        mid-stream.
        """
        return self.guessIndentationByFoldLevels(scimoz, tabWidth, defaultUsesTabs, minIndentLevel=1)

    def keyPressed(self, ch, scimoz):
        (lang_svc_obj, style_info) = self._getLangSvcAndStyleInfoFromScimoz(scimoz, use_previous=True)
        #log.debug("udl: sending keyPressed(%d, %r) to %r", ord(ch), style_info, lang_svc_obj)
        return lang_svc_obj._keyPressed(ch, scimoz, style_info)

    def supportsXMLIndentHere(self, scimoz, pos):
        if self.supportsSmartIndent == "XML":
            return self
        style = self._get_meaningful_style(scimoz, pos)
        subLangSvc = self.getLangSvcAndStyleInfoFromStyle(style)[0]
        if subLangSvc.supportsSmartIndent == "XML":
            return subLangSvc
        if pos == 0:
            return
        stylePrev = self._get_meaningful_style(scimoz, pos - 1)
        if stylePrev == style:
            return
        subLangSvc = self.getLangSvcAndStyleInfoFromStyle(stylePrev)[0]
        if subLangSvc.supportsSmartIndent == "XML":
            return subLangSvc

class KoUDLCommenterLanguageService(KoCommenterLanguageService):
    def __init__(self, langSvc):
        self.langSvc = langSvc
        self.commenter_from_udl_family = {}
        KoCommenterLanguageService.__init__(self, langSvc.commentDelimiterInfo)

    def getCommenterForFamily(self, scimoz):
        # get the current family section of the document, then defer
        # to the language service for that section, it it exists,
        # otherwise fallback to default commenting
        selStart = scimoz.selectionStart
        selEnd = scimoz.selectionEnd

        # Bug 88741: when we transition from Markup at the end of the line,
        # don't start the other family until the start of the next line.
        # Now if we're selecting from <script...>|[EOL]
        # to .... and try to comment it, act as if the commenting
        # starts at the start of the next line.
        selStart_Family = udl_family_from_style(scimoz.getStyleAt(selStart))
        selStartNextPos = scimoz.positionAfter(selStart)
        selStartNext_Family = udl_family_from_style(scimoz.getStyleAt(selStartNextPos))
        selEnd_Family = udl_family_from_style(scimoz.getStyleAt(selEnd))
        selEndPrevPos = scimoz.positionAfter(scimoz.positionBefore(selEnd))
        selEndPrev_Family = udl_family_from_style(scimoz.getStyleAt(selEndPrevPos))
        if (selEndPrev_Family != "M"
            and selStart_Family == "M"
            and selStartNext_Family == selEndPrev_Family):
            scimoz.selectionStart = selStartNextPos
            selStart = selStartNextPos
        else:
            # Watch out if we're selecting at the end of a line,
            # but the start of that line isn't in the same family.
            # If that's the case, move to the start of the next line.
            startLineNo = scimoz.lineFromPosition(selStart)
            endLinePos = scimoz.getLineEndPosition(startLineNo)
            if endLinePos == selStart:
                startLinePos = scimoz.positionFromLine(startLineNo)
                startLineFamily = udl_family_from_style(scimoz.getStyleAt(startLinePos))
                if (startLineFamily == "M"
                    and selStart_Family != "M"
                    and selStartNext_Family == selEndPrev_Family):
                    scimoz.selectionStart = selStartNextPos
                    selStart = selStartNextPos
            
        sections = [
            udl_family_from_style(scimoz.getStyleAt(selStart)),
            udl_family_from_style(scimoz.getStyleAt(selEnd-1))
                   ]
        if selStart == selEnd:
            startLine = scimoz.lineFromPosition(selStart)
            lineStart = scimoz.positionFromLine(startLine)
            lineEnd = scimoz.getLineEndPosition(startLine)

            sections.extend([
                udl_family_from_style(scimoz.getStyleAt(lineStart)),
                udl_family_from_style(scimoz.getStyleAt(lineEnd-1))
                            ])

        family = sections[0]
        for type in sections[1:]:
            if type != family:
                sendStatusMessage("Unable to comment across different sub languages")
                return

        if family not in self.commenter_from_udl_family:
            language = self.langSvc.lang_from_udl_family.get(family)
            if language == self.langSvc.name:
                self.commenter_from_udl_family[family] = self
            else:
                try:
                    # get a language service for this language if it exists
                    registryService = components.classes['@activestate.com/koLanguageRegistryService;1'].\
                        getService(components.interfaces.koILanguageRegistryService)
                    self.commenter_from_udl_family[family] = registryService.getLanguage(language).\
                                    getLanguageService(components.interfaces.koICommenterLanguageService)
                except Exception, e:
                    log.exception(e)
                    self.commenter_from_udl_family[family] = None
        return self.commenter_from_udl_family[family]
        
    def comment(self, scimoz):
        commenter = self.getCommenterForFamily(scimoz)
        if not commenter:
            return
        if commenter is self:
            KoCommenterLanguageService.comment(self, scimoz)
        else:
            commenter.comment(scimoz)

    def uncomment(self, scimoz):
        commenter = self.getCommenterForFamily(scimoz)
        if not commenter:
            return
        if commenter is self:
            KoCommenterLanguageService.uncomment(self, scimoz)
        else:
            commenter.uncomment(scimoz)
