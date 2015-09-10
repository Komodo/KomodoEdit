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

"""Handles schemes (i.e. font/color association with particular languages)
in Komodo.
"""

import copy
import pprint
import os
import logging
import re
import sys
import math

from xpcom import components, nsError, ServerException, COMException
from xpcom.server import WrapObject, UnwrapObject

from styles import StateMap, CommonStates, IndicatorNameMap
from schemebase import SchemeBase, SchemeServiceBase


#---- constants
# Keep in sync with markers.js
MARKNUM_BOOKMARK = 6



#---- globals

log = logging.getLogger('koScintillaSchemeService')
#log.setLevel(logging.DEBUG)

# These are initialized by _initializeStyleInfo().
ScimozStyleNo2CommonName = {}
ScimozStyleNo2SpecificName = {}
IndicatorName2ScimozNo = {}
ValidStyles = {}
_re_udl_style_name = re.compile(r'SCE_UDL_([^_]+)')
_re_color_parts = re.compile(r'(..)')
_no_background_colors = {
    'PHP' : ['PHP'],
    'HTML' : ['HTML'],
}


#---- scheme handling classes

class Scheme(SchemeBase):
    _com_interfaces_ = [components.interfaces.koIScintillaScheme]
    _reg_clsid_ = "{569B18D0-DCD8-490D-AB44-1B66EEAFBCFA}"
    _reg_contractid_ = "@activestate.com/koScintillaScheme;1"
    _reg_desc_ = "Scintilla Scheme object"

    ext = '.ksf'

    def __init__(self):
        pass

    def init(self, fname, userDefined, unsaved=0):
        """
        @param fname {str} Either the full path to a scheme file, or a scheme name (see unsaved)
        @param userDefined {bool} False if it's a Komodo-defined scheme
        @param unsaved {bool} True: fname is the name of a scheme, False: fname is a full path
        @returns {bool} True iff the object initialized successfully
        """
        SchemeBase.__init__(self, fname, userDefined, unsaved)
        namespace = {}
        if not unsaved:
            namespace = self._execfile(fname)
            if not namespace:
                return False
            import json
        self._loadSchemeSettings(namespace, upgradeSettings=(not unsaved))
        return True

    _current_scheme_version = 15

    def _execfile(self, fname):
        try:
            fpath = os.path.dirname(fname)
            sys.path.append(fpath)

            namespace = {}
            execfile(fname, namespace)

            sys.path.remove(fpath)

            if namespace.get("exports"):
                return namespace["exports"]

            return namespace
        except SyntaxError:
            log.exception("Syntax Error loading scheme %s:", fname)
            return False
        except Exception, ex:
            log.exception("Error loading scheme %s:", fname)
            return False

    def _loadSchemeSettings(self, namespace, upgradeSettings=True):
        self._commonStyles = namespace.get('CommonStyles', {})
        self._languageStyles = namespace.get('LanguageStyles', {})
        self._miscLanguageSettings = namespace.get('MiscLanguageSettings', {})
        self._colors = namespace.get('Colors', {})
        self._booleans = namespace.get('Booleans', {})
        self._indicators = namespace.get('Indicators', {})
        self.defaultStyle = {}

        version = namespace.get('Version', 1)
        # Scheme upgrade handling.
        if upgradeSettings and version < self._current_scheme_version:
            orig_version = version
            if version == 1:  # Upgrade to v2.
                if "fold markers" not in self._commonStyles:
                    self._commonStyles["fold markers"] = {}
                if "foldMarginColor" not in self._colors:
                    # None is this case means to use the default Scintilla
                    # color, which uses a system color "ThreeDFace". See
                    # bug 81867.
                    self._colors["foldMarginColor"] = None
                version += 1

            if version == 2:  # Upgrade to v3.
                # Add indicator scheme settings.
                self._indicators = {
                    'linter_error': {
                        'style' : 1,
                        'color': 0x0000ff, # color format is BGR
                        'alpha': 100,
                        'draw_underneath' : True,
                    },
                    'linter_warning': {
                        'style' : 1,
                        'color': 0x008000, # color format is BGR
                        'alpha': 100,
                        'draw_underneath' : True,
                    },
                    'soft_characters': {
                        'style' : 6,
                        'color': 0x003399, # color format is BGR
                        'alpha': 100,
                        'draw_underneath' : False,
                    },
                    'tabstop_current': {
                        'style' : 7,
                        'color': 0x3333ff, # color format is BGR
                        'alpha': 100,
                        'draw_underneath' : True,
                    },
                    'tabstop_pending': {
                        'style' : 6,
                        'color': 0xff9999, # color format is BGR
                        'alpha': 100,
                        'draw_underneath' : True,
                    },
                    'find_highlighting': {
                        'style' : 7,
                        'color': 0x10f0ff, # color format is BGR
                        'alpha': 100,
                        'draw_underneath' : True,
                    },
                    'tag_matching': {
                        'style' : 7,
                        'color': 0x0080ff, # color format is BGR
                        'alpha': 100,
                        'draw_underneath' : True,
                    },
                }
                version += 1

            if version == 3:  # Upgrade to v4.
                if 'whitespaceColor' not in self._colors:
                    self._colors['whitespaceColor'] = self._defaultForeColor()
                version += 1

            if version == 4:
                pythonStyles = self._languageStyles.get("Python", {})
                if "Python" not in self._languageStyles:
                    self._languageStyles["Python"] = pythonStyles
                if "keywords2" not in pythonStyles:
                    if self._hasLightColoredBackground():
                        # Use a darker fg style.
                        pythonStyles["keywords2"] = { 'fore': 878529 }
                    else:
                        # Use the lighter fg style.
                        pythonStyles["keywords2"] = { 'fore': 15989931 }
                version += 1

            if version == 5:
                # this version only appeared in Komodo IDE
                version += 1

            if version == 6:
                # Migrate "Bitstream Vera Sans Mono" to "DejaVu Sans Mono"
                # (but only if the user doesn't have that font)
                # XXX: nsIFontEnumerator crashes komodo under bk test.
                if (sys.platform.startswith("linux") and
                    "koITestService" not in components.interfaces.keys()):
                    if not hasattr(Scheme, "__has_bitstream_vera_sans_mono"):
                        fontenum = components.classes["@mozilla.org/gfx/fontenumerator;1"]\
                                             .getService(components.interfaces.nsIFontEnumerator)
                        setattr(Scheme, "__has_bitstream_vera_sans_mono",
                                "Bitstream Vera Sans Mono" in fontenum.EnumerateAllFonts())
                    if not getattr(Scheme, "__has_bitstream_vera_sans_mono", False):
                        def check_item(item):
                            if not isinstance(item, dict):
                                return
                            if item.get("face", None) == "Bitstream Vera Sans Mono":
                                item["face"] = "DejaVu Sans Mono"
                            for value in item.values():
                                check_item(value)
                        for language in self._languageStyles.values() + [self._commonStyles]:
                            check_item(language)
                version += 1

            if version == 7:
                if self.writeable:
                    # update the CoffeeScript scheme based on C++ for
                    # user-defined schemes.
                    if "CoffeeScript" not in self._languageStyles:
                        self._languageStyles["CoffeeScript"] = self._languageStyles.get("C++", {}).copy()
                    else:
                        # The user must have defined some CoffeeScript styles.  Use C++ as a base, and then
                        # update it based on those settings.
                        tmp_styles = self._languageStyles.get("C++", {}).copy()
                        tmp_styles.update(self._languageStyles["CoffeeScript"])
                        self._languageStyles["CoffeeScript"] = tmp_styles
                version += 1

            if version == 8:
                if self.writeable:
                    self._indicators['multiple_caret_area'] = self._indicators['tabstop_pending'].copy()
                version += 1
                
            if version == 9:
                languages = ["Perl", "Ruby"]
                for language in languages:
                    styles = self._languageStyles.get(language, {})
                    if language not in self._languageStyles:
                        self._languageStyles[language] = styles
                    if "data sections" not in styles:
                        for nameType in ["comments", "strings", "regex", "default_fixed",]:
                            if nameType in self._commonStyles:
                                styles["data sections"] = self._commonStyles[nameType]
                                break
                        else:
                            log.warn("No style for [%s/data sections]", language)
                version += 1
                
            if version == 10:
                if "CSS" in self._languageStyles:
                    styles = self._languageStyles["CSS"]
                    if "identifiers" in styles:
                        self._languageStyles["CSS"]["variables"] = self._languageStyles["CSS"]["identifiers"]
                if "identifiers" in self._commonStyles:
                    self._commonStyles["variables"] = self._commonStyles["identifiers"]
                version += 1
                
            if version == 11:
                # Update Indicators['linter_{error,warning}']['style']
                for indic in ['linter_error', 'linter_warning']:
                    if indic in self._indicators:
                        linter_block = self._indicators[indic]
                        # 1:  scimoz.INDIC_SQUIGGLE
                        # 13: scimoz.INDIC_SQUIGGLEPIXMAP
                        if 'style' not in linter_block or \
                                linter_block['style'] == 1:
                            linter_block['style'] = 13
                version += 1
                
            if version == 12:
                # Add Colors changeMarginInserted and changeMarginDeleted
                # Colors have to be in RGB (?)
                # As opposed to being in BGR in the ksf files.
                newColors = { 'changeMarginInserted':0xa6dca3, # muted green
                              'changeMarginDeleted': 0xe75754, # muted red
                              'changeMarginReplaced': 0x62d3e8, # muted yellow
                              }
                for name in newColors:
                    if name not in self._colors:
                        self._colors[name] = newColors[name]
                version += 1
                    
            if version == 14:
                if 'multiple_caret_area' in self._indicators:
                    del self._indicators['multiple_caret_area']
                version += 1

            try:
                self.save()
                log.warn("Upgraded scheme %r from version %d to %d.",
                         self.name, orig_version, self._current_scheme_version)
            except EnvironmentError, ex:
                log.warn("Unable to save scheme upgrade for %r, error: %r",
                         self.name, ex)

    def revert(self):
        namespace = self._execfile(self.fname)
        if namespace:
            self._loadSchemeSettings(namespace)
            self.isDirty = 0

    def set_useSelFore(self, useSelFore):
        self._booleans['useSelFore'] = useSelFore
        self.isDirty = 1
    def get_useSelFore(self):
        return self._booleans['useSelFore']
    def set_preferFixed(self, preferFixed):
        self._booleans['preferFixed'] = preferFixed
        self.isDirty = 1
    def get_preferFixed(self):
        return self._booleans['preferFixed']
    def set_caretLineVisible(self, caretLineVisible):
        self._booleans['caretLineVisible'] = caretLineVisible
        self.isDirty = 1
    def get_caretLineVisible(self):
        return self._booleans['caretLineVisible']

    def clone(self, newname):
        clone = KoScintillaSchemeService._makeScheme(newname, 1, 1)
        if clone is None:
            _viewsBundle = components.classes["@mozilla.org/intl/stringbundle;1"].\
                           getService(components.interfaces.nsIStringBundleService).\
                           createBundle("chrome://komodo/locale/views.properties")
            raise SchemeCreationException(_viewsBundle.formatStringFromName(
                                          "schemeFileNotCloned.template",
                                          [newname]))
        clone._commonStyles = copy.deepcopy(self._commonStyles)
        clone._languageStyles = copy.deepcopy(self._languageStyles)
        clone._miscLanguageSettings = copy.deepcopy(self._miscLanguageSettings)
        clone._colors = copy.deepcopy(self._colors)
        clone._booleans = copy.deepcopy(self._booleans)
        clone._indicators = copy.deepcopy(self._indicators)
        schemeService = components.classes['@activestate.com/koScintillaSchemeService;1'].getService()
        schemeService.addScheme(clone)
        return clone

    def serialize(self):
        version = "Version = " + pprint.pformat(self._current_scheme_version)
        booleans = "Booleans = " + pprint.pformat(self._booleans)
        commonStyles = "CommonStyles = " + pprint.pformat(self._commonStyles)
        languageStyles = "LanguageStyles = " + pprint.pformat(self._languageStyles)
        miscLanguageSettings = "MiscLanguageSettings = " + pprint.pformat(self._miscLanguageSettings)
        colors = "Colors = " + pprint.pformat(self._colors)
        indicators = "Indicators = " + pprint.pformat(self._indicators)
        parts = [version, booleans, commonStyles, languageStyles, miscLanguageSettings, colors, indicators]
        s = '\n\n'.join(parts)
        return s

    def saveAs(self, name):
        if name == "":
            name = "__unnamed__"
        fname = os.path.join(self._userSchemeDir, name + self.ext)
        if os.path.exists(fname):
            log.error("File %r already exists" % fname)
            return
        schemeService = components.classes['@activestate.com/koScintillaSchemeService;1'].getService()
        if self.name == '__unnamed__': # we want to forget about the unnamed one.
            schemeService.removeScheme(self)
        self.name = name
        self.fname = fname
        self.save()
        schemeService.addScheme(self)

    def save(self):
        log.info("Doing save of %r", self.fname)
        if not self.writeable:
            log.error("Scheme %s is not writeable", self.name)
            return
        f = open(self.fname, 'wt')
        f.write(self.serialize())
        f.close()
        self.unsaved = 0
        observerSvc = components.classes["@mozilla.org/observer-service;1"].\
                getService(components.interfaces.nsIObserverService);
        observerSvc.notifyObservers(self,'scheme-changed',self.name);
        
    def remove(self):
        log.warn("Removing scheme " + self.name)
        schemeService = components.classes['@activestate.com/koScintillaSchemeService;1'].getService()
        if os.path.exists(self.fname):
            os.remove(self.fname)
        schemeService = components.classes['@activestate.com/koScintillaSchemeService;1'].getService()
        schemeService.removeScheme(self)

    def getColor(self, colorName):
        assert colorName in self._colors
        scincolor = self._colors[colorName]
        mozcolor = scincolor2mozcolor(scincolor)
        log.debug("asked for %r, returning %r", colorName, mozcolor)
        return mozcolor

    def setColor(self, colorName, mozcolor):
        assert colorName in self._colors
        color = mozcolor2scincolor(mozcolor)
        log.debug("setting %r=%r", colorName, color)
        self._colors[colorName] = color
        self.isDirty = 1

    def getScintillaColor(self, colorName):
        assert colorName in self._colors
        scincolor = self._colors[colorName]
        log.debug("asked for scin color %r, returning %r", colorName, scincolor)
        return scincolor

    def setFore(self, language, style, mozcolor):
        self._set(language, style, mozcolor2scincolor(mozcolor), 'fore')
        
    def _set(self, language, style, value, attribute):
        log.info("_set(%r, %r, %r, %r)", language, style, value, attribute)
        #log.debug("before set, value = %r", self._appliedData[style])
        if language == '': # common styles
            style = self._fixstyle(style)
            if style not in self._commonStyles:
                self._commonStyles[style] = {}
            self._commonStyles[style][attribute] = value
        else:
            if language not in self._languageStyles:
                self._languageStyles[language] = {}
            if style not in self._languageStyles[language]:
                self._languageStyles[language][style] = {}
            self._languageStyles[language][style][attribute] = value
        self.isDirty = 1

    def setBack(self, language, style, mozcolor):
        self._set(language, style, mozcolor2scincolor(mozcolor), 'back')
        
    def setSubLanguageDefaultBackgroundColor(self, language, mozcolor):
        if not language:
            return
        style = 'compound_document_defaults'
        self._set(language, style, mozcolor2scincolor(mozcolor), 'back')

    def getSubLanguageDefaultBackgroundColor(self, language, useFixed=1):
        try:
            backgroundColor = self._languageStyles[language]\
                                  ['compound_document_defaults']['back']
            if backgroundColor is not None:
                return scincolor2mozcolor(backgroundColor)
        except KeyError:
            pass
        return self.getBack(language, 'default')

    def setGlobalSubLanguageBackgroundEnabled(self, language, val):
        if not language:
            return
        self._miscLanguageSettings.setdefault(language, {})['globalSubLanguageBackgroundEnabled'] = val
        self.isDirty = 1

    def getGlobalSubLanguageBackgroundEnabled(self, subLanguageName, docLanguageName=None):
        if docLanguageName in _no_background_colors \
                and subLanguageName in _no_background_colors[docLanguageName]:
            return False
        try:
            return self._miscLanguageSettings[subLanguageName]['globalSubLanguageBackgroundEnabled']
        except KeyError:
            return False

    def setBold(self, language, style, bold):
        self._set(language, style, bold, 'bold')
    
    def setItalic(self, language, style, italic):
        self._set(language, style, italic, 'italic')
    
    def setFont(self, style, font):
        self._set('', style, font, 'face')

    def setLineSpacing(self, style, spacing):
        self._set('', style, spacing, 'lineSpacing')

    def setFaceType(self, language, style, useFixed):
        self._set(language, style, useFixed, 'useFixed')
    
    def setSize(self, language, style, size):
        self._set(language, style, size, 'size')
        
    def setIndicator(self, indic_name, style, mozcolor, alpha, draw_underneath):
        self._indicators[indic_name] = {
            'style' : style,
            'color': mozcolor2scincolor(mozcolor),
            'alpha': alpha,
            'draw_underneath' : draw_underneath,
        }
        self.isDirty = 1

    def _fixstyle(self, style):
        if style == 'default':
            if self._booleans['preferFixed']:
                style = 'default_fixed'
            else:
                style = 'default_proportional'
        return style

    def _getAspectFromStyleBlocks(self, style, attribute):
        if style in self._commonStyles:
            styleBlock = self._commonStyles[style]
        else:
            fallbackstyle = self._getFallbackStyle(style)
            try:
                styleBlock = self._commonStyles[fallbackstyle]
            except KeyError:
                log.exception("No key: self._commonStyles[fallbackstyle=%r], style=%r, attribute=%r", fallbackstyle, style, attribute)
                raise
        return styleBlock.get(attribute, self.defaultStyle.get(attribute))

    def _getAspectFromAppliedData(self, style, attribute):
        aspect = None
        if style in self._appliedData:
            aspect = self._appliedData[style].get(attribute)
        if aspect is None:
            aspect = self._getAspectFromStyleBlocks(style, attribute)
        return aspect

    def _getAspect(self, language, style, attribute):
        if not language:
            return self._getAspectFromStyleBlocks(style, attribute)
        else:
            # Don't go to appliedData yet -- it only gets updated when
            # we call applyScheme
            aspect = self._languageStyles.get(language, {}).get(style, {}).get(attribute, None)
            if aspect is not None:
                return aspect
            return self._getAspectFromAppliedData(style, attribute)

    def getFore(self, language, style):
        #print language, style
        #style = self._fixstyle(style)
        scincolor = self._getAspect(language, style, 'fore')
        #print "asked for fore of ", language, style, "got", scincolor
        return scincolor2mozcolor(scincolor)

    def getCommon(self, style, key):
        color = None
        if style in self._commonStyles:
             color = self._commonStyles[style].get(key, None)

        if color:
            return  scincolor2mozcolor(color)
        else:
            return ""
        
    def getBack(self, language, style):
        #style = self._fixstyle(style)
        scincolor = self._getAspect(language, style, 'back')
        return scincolor2mozcolor(scincolor)

    def getBold(self, language, style):
        #style = self._fixstyle(style)
        bold = self._getAspect(language, style, 'bold')
        #print "getBold(%r,%r) --> %r" % (language, style, bold)
        return bold

    def getItalic(self, language, style):
        #style = self._fixstyle(style)
        italic = self._getAspect(language, style, 'italic')
        #pprint.pprint(self._appliedData)
        #print "getItalic(%r,%r) --> %r" % (language, style, italic)
        #pprint.pprint(self._appliedData)
        return italic

    def getFont(self, style, fontstack = False):
        #style = self._fixstyle(style)
        # this returns a real font label
        font = self._getAspectFromAppliedData(style, 'face')

        if fontstack:
            return font
        else:
            return self._getFontEffective(font)

    # Parses the font stack and returns the first font that is installed on the
    # current system
    # Example font stack: '"Source Code Pro", Consolas, Inconsolata, Monospace'
    def _getFontEffective(self, fontStack):
        if not fontStack:
            return

        # Parse the CSS font stack
        fontStack = fontStack.split(",")
        for i in range(len(fontStack)):
            fontStack[i] = re.sub(r'^[\'"\s]*|[\'"\s]*$', '', fontStack[i])

        # Get all available fonts
        enumerator = components.classes["@mozilla.org/gfx/fontenumerator;1"].createInstance()
        enumerator = enumerator.QueryInterface(components.interfaces.nsIFontEnumerator)
        fonts = set(enumerator.EnumerateAllFonts())

        # Check if any fonts in the font stack match the ones on the system
        # and return the first one that does
        for fontName in fontStack:
            if fontName in fonts:
                return fontName

        # Fall back on last font in fontstack
        return fontStack[-1]

    def getLineSpacing(self, style):
        val = self._getAspectFromAppliedData(style, 'lineSpacing')
        if val is None:
            log.debug("Style does not have lineSpacing, returning 0")
            return 0
        return val

    def _getFallbackStyle(self, style):
        if style.endswith('_fixed'):
            return 'default_fixed'
        elif style.endswith('_proportional'):
            return 'default_proportional'
        else:
            log.error("asked for style %r, don't know what to do", style)
    
    def getFaceType(self, language, style):
        #style = self._fixstyle(style)
        # this returns true for 'fixed' or false for 'proportional'
        return self._getAspectFromAppliedData(style, 'useFixed')
    
    def getSize(self, language, style):
        #style = self._fixstyle(style)
        size = self._getAspect(language, style, 'size')
        return size
        
    def getIndicator(self, indic_name):
        indic_dict = self._indicators.get(indic_name)
        if indic_dict is None:
            log.warn("getIndicator:: no indicator for name %r", indic_name)
            return (0, scincolor2mozcolor(0), 0, False)
        return (
            indic_dict.get('style', 0),
            scincolor2mozcolor(indic_dict.get('color', 0)),
            indic_dict.get('alpha', 100),
            indic_dict.get('draw_underneath', False),
        )

    def resetStyle(self, language, style):
        #pprint.pprint(self._languageStyles)
        log.info("doing resetStyle: %r, %r", language, style)
        if not language:
            # this is called by the resetEncoding pathway
            if style in self._commonStyles:
                self._commonStyles[style] = {}
        else:
            if style in self._languageStyles[language]:
                log.info("deleting from languageStyle")
                self._languageStyles[language][style] = {}
            log.debug(repr(self._languageStyles))
        self.isDirty = 1

    def applyScheme(self, scimoz, language, encoding, alternateType):
        registryService = components.classes['@activestate.com/koLanguageRegistryService;1'].\
            getService(components.interfaces.koILanguageRegistryService)
        languageObj = registryService.getLanguage(language)
        # Don't worry about document-specific lexers.
        if languageObj:
            lexer = languageObj.getLanguageService(components.interfaces.koILexerLanguageService)
            lexer.setCurrent(scimoz)
        self.currentLanguage = language
        self.currentEncoding = encoding
        
        self._appliedData = {}
        setters = {
            'fore': scimoz.styleSetFore,
            'back': scimoz.styleSetBack,
            'bold': scimoz.styleSetBold,
            'italic': scimoz.styleSetItalic,
            'size': scimoz.styleSetSize,
            'eolfilled': scimoz.styleSetEOLFilled,
            'hotspot': scimoz.styleSetHotSpot,
        }

        # These are special style elements that are not based upon
        # the default style, i.e. non-editor styles.
        stylesThatDontUseDefault = [
            'linenumbers',
            'fold markers',
        ]

        # This function needs to do two somewhat complementary things:
        # - Build the self._appliedData dictionary which describes
        #   the _full_ set of styling information for the current language.
        # - Do the minimal number of scimoz styling calls for all of the
        #   styling calls.
        
        # We're going to need to refer to the fixed default and the proportional
        # default, so we build those up too.
        fixed_font_fallback_style_name = 'default_fixed'
        prop_font_fallback_style_name = 'default_proportional'
        fixed_font_style_name = encoding+'_fixed'
        prop_font_style_name = encoding+'_proportional'

        if self.currentLanguage in self._languageStyles:
            currentLanguageStyles = self._languageStyles[self.currentLanguage]
        else:
            currentLanguageStyles = copy.deepcopy(self._commonStyles)
        fixedStyle = self._commonStyles[fixed_font_fallback_style_name].copy()
        if fixed_font_style_name in self._commonStyles:
            fixedStyle.update(self._commonStyles[fixed_font_style_name])
        propStyle = self._commonStyles[prop_font_fallback_style_name].copy()
        if prop_font_style_name in self._commonStyles:
            propStyle.update(self._commonStyles[prop_font_style_name])

        fixedStyle['face'] = self._getFontEffective(fixedStyle['face'])
        propStyle['face'] = self._getFontEffective(propStyle['face'])

        useFixed = self._booleans['preferFixed']
        if alternateType: useFixed = not useFixed
        if ('default' in currentLanguageStyles and
           'useFixed' in currentLanguageStyles['default']):
            useFixed = currentLanguageStyles['default']['useFixed']
        if useFixed:
            defaultStyle = fixedStyle
        else:
            defaultStyle = propStyle
        if 'default' in currentLanguageStyles:
            defaultStyle.update(currentLanguageStyles['default'])

        self._appliedData['default'] = defaultStyle
        self.defaultStyle = defaultStyle
        for aspect, setter in setters.items():
            value = defaultStyle[aspect]
            setter(scimoz.STYLE_DEFAULT, value)
        if sys.platform.startswith('win'):
            scimoz.styleSetFont(scimoz.STYLE_DEFAULT,defaultStyle['face'])
        else:
            font = self._buildFontSpec(defaultStyle['face'], encoding)
            scimoz.styleSetFont(scimoz.STYLE_DEFAULT, font)

        spacing = float(defaultStyle.get("lineSpacing", 0))

        extraDescent = int(math.ceil(spacing / 2))
        extraAscent = int(math.floor(spacing / 2))

        scimoz.extraDescent = extraDescent
        scimoz.extraAscent = extraAscent

        scimoz.styleClearAll() # now all styles are the same
        defaultUseFixed = useFixed
        langStyles = GetLanguageStyles(language)
        if langStyles:
            for (scimoz_no, scimoz_name, common_name) in langStyles:
                # first deal with which default style should be used.
                commonStyle = self._commonStyles.get(common_name, {})
                specificStyle = currentLanguageStyles.get(common_name, {})
                useFixed = specificStyle.get('useFixed',
                                             commonStyle.get('useFixed',
                                                             defaultUseFixed))
                if useFixed:
                    style = fixedStyle.copy()
                else:
                    style = propStyle.copy()
                style.update(commonStyle)
                # Hack for bug 71202 regarding linenumber background style
                # used in derived schemes. If the scheme does not explicitly
                # define a line numbers background color, then we set the
                # color value to None, which means the default Scintilla
                # coloring will be used. Also added a check for black schemes,
                # as we want these derived black schemes to use a better color
                # than the scintilla default (which is usually a light color).
                if common_name == "linenumbers" and "back" not in commonStyle \
                   and style["back"] != 0:
                    style["back"] = None
                style.update(specificStyle)

                # UDL: Grab nested sublanguages
                # If a language is made up of sub-languages L1 ... L4,
                # get the specific language info for languages L1 through L4,
                # and use those.  This is where the sub-language-specific
                # background color gets used.
                UDLBackgroundColor = None
                # scimoz_name could be same as scimoz_no (bug 84019)
                m = _re_udl_style_name.match(str(scimoz_name))
                if m:
                    family = m.group(1)
                    try:
                        subLanguageName = languageObj.getLanguageForFamily(family)
                        if subLanguageName is None and family == "TPL":
                            # Map TPL -- the template stuff -- to the SSL component
                            family = "SSL"
                            subLanguageName = languageObj.getLanguageForFamily(family)
                        defaultSubLanguageStyles = subLanguageName and self._languageStyles.get(subLanguageName)
                        if defaultSubLanguageStyles is not None:
                            if self.getGlobalSubLanguageBackgroundEnabled(subLanguageName, language):
                                UDLBackgroundColor = defaultSubLanguageStyles.get('compound_document_defaults', {}).get('back')
                            if subLanguageName != language:
                                style.update(defaultSubLanguageStyles.get(common_name, {}))
                    except:
                        log.exception("Failed to get sub-language for family %s from language %s ", family, language)

                style['face'] = self._getFontEffective(style['face'])

                self._appliedData[common_name] = style
                if useFixed != defaultUseFixed:
                    if not sys.platform.startswith('win'):
                        font = self._buildFontSpec(style['face'], encoding)
                    else:
                        font = style['face']
                    scimoz.styleSetFont(scimoz_no, font)
                #print "common_name = ", common_name,
                #pprint.pprint(style)
                if style['face'] != defaultStyle['face']:
                    if not sys.platform.startswith('win'):
                        font = self._buildFontSpec(style['face'], encoding)
                    else:
                        font = style['face']
                    scimoz.styleSetFont(scimoz_no, font)
                defaultStyleIsNotApplicable = common_name in stylesThatDontUseDefault
                for aspect, setter in setters.items():
                    value = style[aspect]
                    if (value is not None
                        and (defaultStyleIsNotApplicable
                             or value != defaultStyle[aspect])):
                        setter(scimoz_no, value)

                if UDLBackgroundColor is not None:
                    scimoz.styleSetBack(scimoz_no, UDLBackgroundColor)
                    # Use EOL filled to ensure the background color continues
                    # for the full width of the line - bug 86167.
                    scimoz.styleSetEOLFilled(scimoz_no, True)

        # Now do the other colors, such as cursor color
        scimoz.caretFore = self._colors['caretFore']
        scimoz.setSelBack(1, self._colors['selBack'])
        scimoz.setSelFore(self._booleans['useSelFore'], self._colors['selFore'])
        scimoz.caretLineBack = self._colors['caretLineBack']
        scimoz.caretLineVisible = self._booleans['caretLineVisible']
        scimoz.setHotspotActiveUnderline(0)
        scimoz.edgeColour = self._colors['edgeColor']
        scimoz.markerSetFore(MARKNUM_BOOKMARK,
                             self._colors["bookmarkColor"])
        scimoz.markerSetBack(MARKNUM_BOOKMARK,
                             self._colors["bookmarkColor"])
        
        # Fold margin and fold marker colors.
        foldStyle = defaultStyle.copy()
        foldStyle.update(self._commonStyles.get("fold markers", {}))
        foldStyle.update(currentLanguageStyles.get("fold markers", {}))
        # Remember the applied style.
        self._appliedData["fold markers"] = foldStyle
        foreColor = foldStyle.get("fore", None)
        backColor = foldStyle.get("back", None)
        if foreColor is not None or backColor is not None:
            foldBitMask = scimoz.SC_MASK_FOLDERS
            for i in range(scimoz.MARKER_MAX+1):
                if foldBitMask & (1 << i):
                    # Scintilla swaps the fore and back colors for margins, so
                    # when calling markerSetFore(), it actually sets the
                    # background color of the marker.
                    if backColor is not None:
                        scimoz.markerSetFore(i, backColor)
                    if foreColor is not None:
                        scimoz.markerSetBack(i, foreColor)
            # Also need to set the fold margin color, for where there are no
            # fold symbols drawn.
        foldmargin_color = self._colors.get("foldMarginColor")
        if foldmargin_color is not None:
            scimoz.setFoldMarginColour(True, foldmargin_color)
            scimoz.setFoldMarginHiColour(True, foldmargin_color)
        else:
            scimoz.setFoldMarginColour(False, 0)
            scimoz.setFoldMarginHiColour(False, 0)

        whitespace_color = self._colors.get("whitespaceColor")
        if whitespace_color is not None:
            scimoz.setWhitespaceFore(True, whitespace_color)
        else:
            scimoz.setWhitespaceFore(False, 0)

        # Indicators: UDL transition (internal only)
        DECORATOR_UDL_FAMILY_TRANSITION = components.interfaces.koILintResult.DECORATOR_UDL_FAMILY_TRANSITION
        scimoz.indicSetStyle(DECORATOR_UDL_FAMILY_TRANSITION, scimoz.INDIC_HIDDEN)
        ## For debugging, to show the UDL family transitions:
        #scimoz.indicSetStyle(components.interfaces.koILintResult.DECORATOR_UDL_FAMILY_TRANSITION,
        #                     scimoz.INDIC_ROUNDBOX)
        #scimoz.indicSetFore(DECORATOR_UDL_FAMILY_TRANSITION, mozcolor2scincolor("#008000"))

        # Indicators: Tabstops (internal ones)
        DECORATOR_TABSTOP_TSZW = components.interfaces.koILintResult.DECORATOR_TABSTOP_TSZW
        DECORATOR_TABSTOP_TSCZW = components.interfaces.koILintResult.DECORATOR_TABSTOP_TSCZW
        DECORATOR_TABSTOP_TS1 = components.interfaces.koILintResult.DECORATOR_TABSTOP_TS1
        DECORATOR_TABSTOP_TS5 = components.interfaces.koILintResult.DECORATOR_TABSTOP_TS5
        for i in range(DECORATOR_TABSTOP_TSZW, DECORATOR_TABSTOP_TS5 + 1):
            scimoz.indicSetUnder(i, True) # draw under
            scimoz.indicSetStyle(i, scimoz.INDIC_BOX)
            scimoz.indicSetFore(i, mozcolor2scincolor("#9999ff"))
        scimoz.indicSetStyle(DECORATOR_TABSTOP_TSCZW, scimoz.INDIC_HIDDEN)

        # Indicators: Preferenced indicators (find highlight, tab matching, ...)
        indicator_setters = {
            'style' :           scimoz.indicSetStyle,
            'color' :           scimoz.indicSetFore,
            'alpha' :           scimoz.indicSetAlpha,
            'outline_alpha' :   scimoz.indicSetOutlineAlpha,
            'draw_underneath' : scimoz.indicSetUnder,
        }
        for indic_name in self._indicators:
            indic_no = IndicatorName2ScimozNo.get(indic_name)
            if not indic_no:
                log.warn("applyScheme:: no indicator for name %r", indic_name)
                continue
            if "alpha" in self._indicators[indic_name]:
                self._indicators[indic_name]["outline_alpha"] = self._indicators[indic_name]["alpha"]
            for key, value in self._indicators[indic_name].items():
                setter = indicator_setters.get(key)
                if setter is None:
                    log.warn("applyScheme:: no indicator setter for %r", key)
                    continue
                if indic_no == DECORATOR_TABSTOP_TS1:
                    # Pending tabstops - update all of them (1 through 5)
                    for i in range(DECORATOR_TABSTOP_TS1, DECORATOR_TABSTOP_TS5+1):
                        setter(i, value)
                else:
                    setter(indic_no, value)
        
        # Set annotation styles for linter based on lint indicator colors.
        cikoILR = components.interfaces.koILintResult
        scimoz.releaseAllExtendedStyles()
        scimoz.annotationStyleOffset = scimoz.allocateExtendedStyles(2)
        scimoz.styleSetFore(scimoz.annotationStyleOffset + cikoILR.ANNOTATION_ERROR,
                            scimoz.indicGetFore(cikoILR.DECORATOR_ERROR))
        scimoz.styleSetItalic(scimoz.annotationStyleOffset + cikoILR.ANNOTATION_ERROR, True);
        scimoz.styleSetFore(scimoz.annotationStyleOffset + cikoILR.ANNOTATION_WARNING,
                            scimoz.indicGetFore(cikoILR.DECORATOR_WARNING))
        scimoz.styleSetItalic(scimoz.annotationStyleOffset + cikoILR.ANNOTATION_WARNING, True);

        #XXX Note: we used to apply some style prefs for the foreground of
        #    some of our markers here. This was limited in scope (only some
        #    markers and only the foreground). With the new debugger stuff
        #    (more markers, newer better colors), this was just getting in
        #    the way. Need to revisit this at some point.

    def getCommonName(self, language, styleno):
        if (styleno, language) in ScimozStyleNo2CommonName:
            name = ScimozStyleNo2CommonName[(styleno, language)]
            if name == 'default': name = '' # default is not in the list.
        else:
            name = ''
        return name
    def getSpecificName(self, language, styleno):
        if (styleno, language) in ScimozStyleNo2SpecificName:
            return ScimozStyleNo2SpecificName[(styleno, language)]
        return ''

    def _partsFromMozColor(self, mozColor):
        mozColor = mozColor[1:]
        pieces = [int(x, 16) for x in _re_color_parts.split(mozColor) if x]
        return pieces

    def _scinColorFromParts(self, parts):
        return ((parts[2] * 256) + parts[1]) * 256 + parts[0]

    def _calcAdjuster(self, defaultBGParts, highlightedBGParts):
        return [x - y for (x, y) in zip(defaultBGParts, highlightedBGParts)]

    def _applyAdjuster(self, adjuster, color):
        # Try subtracting the difference: assume highlight is darker
        parts = [x - y for (x, y) in zip(color, adjuster)]
        if not [p for p in parts if p < 0 or p > 255]:
            return parts
        # Try adding the difference: move the other way (brighter in a light scheme)
        parts = [x + y for (x, y) in zip(color, adjuster)]
        if not [p for p in parts if p < 0 or p > 255]:
            return parts
        # Don't adjust.
        return color

    def _isLightScintillaColor(self, scincolor):
        rgb = [scincolor & 0xFF,
               (scincolor >> 8) & 0xFF,
               (scincolor >> 16) & 0xFF]
        return len([x for x in rgb if x >= 128]) >= 2
    def _isDarkScintillaColor(self, scincolor):
        return not self._isLightScintillaColor(scincolor)

    def _defaultForeColor(self):
        defaultForeColor = None
        useFixed = self._booleans.get('preferFixed', True)
        if useFixed:
            names = ['default_fixed', 'default_proportional', 'default']
        else:
            names = ['default_proportional', 'default_fixed', 'default']
        for name in names:
            if name in self._commonStyles:
                defaultForeColor = self._commonStyles[name].get('fore')
                if defaultForeColor is not None:
                    break
        if defaultForeColor is None:
            log.warn("Unable to find a default foreground color in scheme %r",
                     self.name)
            defaultForeColor = 0x000000 # fallback - black
        return defaultForeColor

    def _defaultBackColor(self):
        defaultBackColor = None # fallback - white
        useFixed = self._booleans.get('preferFixed', True)
        if useFixed:
            names = ['default_fixed', 'default_proportional', 'default']
        else:
            names = ['default_proportional', 'default_fixed', 'default']
        for name in names:
            if name in self._commonStyles:
                defaultBackColor = self._commonStyles[name].get('back')
                if defaultBackColor is not None:
                    break
        if defaultBackColor is None:
            log.warn("Unable to find a default background color in scheme %r",
                     self.name)
            defaultBackColor = 0xFFFFFF # fallback - white
        return defaultBackColor

    def _hasLightColoredBackground(self):
        """Light refers to the background color of the scheme."""
        return self._isDarkScintillaColor(self._defaultForeColor())
    def _hasDarkColoredBackground(self):
        return not self._hasLightColoredBackground()

    @property
    def isDarkBackground(self):
        return self._hasDarkColoredBackground()

    @property
    def backgroundColor(self):
        return scincolor2mozcolor(self._defaultBackColor())

    @property
    def foregroundColor(self):
        return scincolor2mozcolor(self._defaultForeColor())

    def getHighlightColorInfo(self, languageObj):
        """
        This function also serves as a gatekeeper.
        Return [] to indicate there is no info:
        
        1. If this scheme doesn't highlight the current line, return []
        
        2. If the current language isn't UDL-based, return []
        
        3. If it is, but none of its sublanguages define their own color,
        return [].
        
        Otherwise return an array of "<familyName>:<color value>"
        where familyName is one of "M", "CSS", "CSL", "SSL", etc.,
        and the color value is the decimal representation of the
        RGB color.
        """

        if not self.get_caretLineVisible():
            return []
        languageObj = UnwrapObject(languageObj)
        if not languageObj.isUDL():
            return []
        subLanguageNames = languageObj.getSubLanguages()
        if len(subLanguageNames) <= 1:
            return []
        # Check to see if any of the sublanguages define their own bg color
        usesBackgroundColors = False
        for subLanguageName in subLanguageNames:
            if self.getGlobalSubLanguageBackgroundEnabled(subLanguageName, languageObj.name):
                usesBackgroundColors = True
                break
        if not usesBackgroundColors:
            return []
        colorInfo = []
        familyNames = ("M", "CSS", "CSL", "SSL", "TPL")
        defaultBGColor = self.getBack(languageObj.name, 'default')
        defaultBGParts = self._partsFromMozColor(defaultBGColor)
        highlightedBGColor = self.getColor('caretLineBack')
        highlightedBGParts = self._partsFromMozColor(highlightedBGColor)
        adjuster = self._calcAdjuster(defaultBGParts, highlightedBGParts)
        for familyName in familyNames:
            subLanguageName = languageObj.getLanguageForFamily(familyName)
            if subLanguageName:
                if self.getGlobalSubLanguageBackgroundEnabled(subLanguageName, languageObj.name,):
                    bgColor = self.getSubLanguageDefaultBackgroundColor(subLanguageName)
                else:
                    bgColor = defaultBGColor
                bgColorParts = self._partsFromMozColor(bgColor)
                fixedBGColor = self._applyAdjuster(adjuster, bgColorParts)
            else:
                fixedBGColor = highlightedBGColor
            colorInfo.append("%s:%d" % (familyName,
                                        self._scinColorFromParts(fixedBGColor)))
        return colorInfo
    
    def _buildFontSpec(self, font, encoding_name):
# #if PLATFORM == 'win' or PLATFORM == 'darwin'
        return font
# #else
        # PANGO font name support
        return "!"+font
# #endif

class SchemeCreationException(Exception):
    pass

class KoScintillaSchemeService(SchemeServiceBase):
    _com_interfaces_ = [components.interfaces.koIScintillaSchemeService]
    _reg_clsid_ = "{469B18D0-DCD8-490D-AB44-1B66EEAFBCFE}"
    _reg_contractid_ = "@activestate.com/koScintillaSchemeService;1"
    _reg_desc_ = "Service used to access, manage and create scintilla 'schemes'"
    screenToCSS = 1.3 # scaling between screen fonts and 'appropriate' CSS fonts

    ext = '.ksf'

    def __init__(self):
        SchemeServiceBase.__init__(self)
        self.lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"].\
                                getService(components.interfaces.koILastErrorService)

        _initializeStyleInfo()

        currentScheme = self._globalPrefs.getStringPref('editor-scheme')
        if currentScheme not in self._scheme_details:
            log.error("The scheme specified in prefs (%s) is unknown -- reverting to default", currentScheme)
            self._globalPrefs.setStringPref('editor-scheme', 'Default')

    @classmethod
    def _makeScheme(cls, fname, userDefined, unsaved=0):
        """Factory method for creating an initialized scheme object

        @param fname {str} Either the full path to a scheme file, or a scheme name (see unsaved)
        @param userDefined {bool} False if it's a Komodo-defined scheme
        @param unsaved {bool} True: fname is the name of a scheme, False: fname is a full path
        @returns an initialized Scheme object
        """
        aScheme = Scheme()
        if aScheme.init(fname, userDefined, unsaved):
            return aScheme
        return None


    def getCommonStyles(self):
        names = CommonStates[:]
        names.sort()
        names.remove('default')  # that's what the first panel is about
        return names

    def getLanguageStyles(self, language):
        names = StateMap[language].keys()
        names.sort()
        return names
    
    def getIndicatorNames(self):
        return sorted(IndicatorNameMap)

    def getIndicatorNoForName(self, indic_name):
        return IndicatorName2ScimozNo.get(indic_name, -1)

    def purgeUnsavedSchemes(self):
        for scheme in list(self._schemes.values()):
            if scheme.unsaved:
                self.removeScheme(scheme)

    def createCSS(self, language, scheme, forceColor):
        css = []
        # get default colors
        # XXX -- need to deal with encodings.
        scheme = UnwrapObject(scheme)
        if forceColor:
            useColor = 1
        else:
            useColor = self._globalPrefs.getBooleanPref('print_useColor')
        fixed_face = scheme.getFont('default_fixed')
        prop_face = scheme.getFont('default_proportional')
        defaultUseFixed = scheme.get_preferFixed()
        if defaultUseFixed:
            default_face = fixed_face
            default_name = 'default'
        else:
            default_face = prop_face
            default_name = 'default'
        default_color = scheme.getFore(language, default_name)
        default_background = scheme.getBack(language, default_name)
        default_size = scheme.getSize(language, default_name)*self.screenToCSS
        default_bold = scheme.getBold(language, default_name)
        default_italic = scheme.getItalic(language, default_name)
        if default_bold:
            weight = 'bold'
        else:
            weight = 'normal'
        if default_italic:
            style = 'italic'
        else:
            style = 'normal'
        defaultStyle = """span {
    font-family: %(default_face)s;
    color: %(default_color)s;
    background-color: %(default_background)s;
    font-size: %(default_size)spx;
    font-weight: %(weight)s;
    font-style: %(style)s;
}\n\n""" % locals()
        defaultStyle = """body.default {
    font-family: %(default_face)s;
    color: %(default_color)s;
    background-color: %(default_background)s;
    font-size: %(default_size)spx;
    font-weight: %(weight)s;
    font-style: %(style)s;
}\n\n""" % locals()
        css.append(defaultStyle)
        stylesDealtWith = {}
        langStyles = GetLanguageStyles(language)
        if langStyles:
            for (scimoz_no, scimoz_name, common_name) in langStyles:
                if common_name in stylesDealtWith: continue
                stylesDealtWith[common_name] = 1
                style = ['span.%s {\n' % common_name.replace(' ', '_') ]
                color = scheme.getFore(language, common_name)
                background = scheme.getBack(language, common_name)
                size = scheme.getSize(language, common_name)*self.screenToCSS
                bold = scheme.getBold(language, common_name)
                italic = scheme.getItalic(language, common_name)
                useFixed = scheme.getFaceType(language, common_name)
                if useFixed != defaultUseFixed:
                    if useFixed:
                        style.append('    font-family: ' + fixed_face +';\n')
                    else:
                        style.append('    font-family: ' + prop_face +';\n')
                if useColor and color != default_color:
                    style.append('    color: ' + color + ';\n')
                if size != default_size:
                    style.append('    font-size: ' + str(size) + 'px;\n')
                if not useColor:
                    # make black and white printing use bold for keywords
                    # and italic for comments
                    if common_name == 'keywords':
                        bold = not default_bold
                    elif common_name == 'comments' or common_name == 'strings':
                        italic = not default_italic
                if bold != default_bold:
                    if bold:
                        style.append('    font-weight: bold;\n')
                    else:
                        style.append('    font-weight: normal;\n')
                if italic != default_italic:
                    if italic:
                        style.append('    font-style: italic;\n')
                    else:
                        style.append('    font-style: normal;\n')
                style.append('}\n\n');
                css.append(''.join(style))
        return ''.join(css)
    
    def convertToHTMLFile(self, scimoz, title, language, style_bits, encoding,
                          fname, selectionOnly, forceColor):
        cp = scimoz.currentPos
        an = scimoz.anchor
        fvl = scimoz.firstVisibleLine
        xoffset = scimoz.xOffset

        schemeName = self._globalPrefs.getStringPref('editor-scheme')
        self.screenToCSS = self._globalPrefs.getDoublePref('print_scalingRatio')
        scheme = self.getScheme(schemeName)
        scheme.applyScheme(scimoz, language, encoding, 0);
        self._htmlStyleTags = {}
        from cStringIO import StringIO
        html = StringIO()
        # Encoding has to be utf-8, as scimoz uses utf-8 and we use scimoz's
        # getStyledText method to retrieve the bytes.
        encoding = "UTF-8"
        html.write('<?xml version="1.0" encoding="%s"?>\n' % encoding)
        html.write('''<!DOCTYPE html\n
     PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
    ''')
        # First we make a CSS stylesheet for the particular language.  This can
        # most efficiently be done simply by looking at the current scimoz's styles.
        
        css = self.createCSS(language, scheme, forceColor)
        # Added <meta charset=> to properly set the encoding - bug 65298.
        html.write('''<head>
    <meta http-equiv="Content-Type" content="text/html; charset=%s" />
    <title>%s</title>
    <style type="text/css">
    %s
    </style>
    </head>
    ''' % (encoding, title, css))
        html.write("<body class=\"default\"><p>\n")
        _globalPrefs = components.classes["@activestate.com/koPrefService;1"].\
                       getService(components.interfaces.koIPrefService).prefs
        useLineNos = _globalPrefs.getBooleanPref('print_showLineNos')
        maxLineLength = _globalPrefs.getLongPref('print_lineLength')
        # Sanity check
        if maxLineLength < 0:
            log.warn("Found a negative pref for print_lineLength = %d", maxLineLength)
            maxLineLength = 0
        scimoz.colourise(0, scimoz.textLength)
        textlength = scimoz.textLength
        if selectionOnly:
            lineNo = scimoz.lineFromPosition(scimoz.selectionStart)
        else:
            lineNo = 0
        while 1:
            lineStart = scimoz.positionFromLine(lineNo)
            lineNo += 1
            lineEnd = min(textlength, scimoz.positionFromLine(lineNo))
            self._addLogicalLine(html, scimoz, lineStart, lineEnd, language, lineNo,
                                 useLineNos, style_bits, maxLineLength,
                                 selectionOnly)
            if lineEnd == textlength: break
            if selectionOnly and lineEnd > scimoz.selectionEnd:
                break
        html.write('</p></body></html>\n')
        scimoz.currentPos = cp
        scimoz.anchor = an
        scimoz.lineScroll(0, fvl-scimoz.firstVisibleLine)
        scimoz.xOffset = xoffset
        text = html.getvalue()
        text = text.replace('\r', '\n')
        text = text.replace('\n\n', '\n')
        try:
            f = open(fname, 'wb')
            f.write(text)
            f.close()
        except Exception, ex:
            errmsg = str(ex)
            self.lastErrorSvc.setLastError(nsError.NS_ERROR_FAILURE,
                                           errmsg)
            raise ServerException(nsError.NS_ERROR_FAILURE, errmsg)
            
    _invalidSchemeCharacterSet = re.compile('[^\w\d\-_=+,. @#$%,]')
    def schemeNameIsValid(self, candidateName):
        return not self._invalidSchemeCharacterSet.search(candidateName)
        
    def loadSchemeFromURI(self, uri, schemeBaseName):
        """ Save the incoming URI in the userDataDir/schemes/,
        and have Komodo use the new/updated scheme.
        
        @param uri {str} the URI to open
        @returns {wstring} name of new scheme.  Throws an exception on failure.
        """
        fileSvc = components.classes["@activestate.com/koFileService;1"].\
                  getService(components.interfaces.koIFileService)
        _viewsBundle = components.classes["@mozilla.org/intl/stringbundle;1"].\
                       getService(components.interfaces.nsIStringBundleService).\
                       createBundle("chrome://komodo/locale/views.properties")
           
        schemeName = os.path.splitext(schemeBaseName)[0]
        if not self.schemeNameIsValid(schemeName):
            raise ServerException(nsError.NS_ERROR_INVALID_ARG,
                                  _viewsBundle.formatStringFromName(
                                      "schemeNameHasInvalidCharacters.template",
                                      [schemeBaseName]))
            
        koFileExSrc = fileSvc.getFileFromURI(uri);
        if not koFileExSrc:
            log.error("Failed to get file object for " + uri)
            raise ServerException(nsError.NS_ERROR_INVALID_ARG,
                                  _viewsBundle.formatStringFromName(
                                      "cantFindSchemeFile.template",
                                      [uri]))
        
        koFileExSrc.open('r')
        data = koFileExSrc.readfile()
        koFileExSrc.close()

        if koFileExSrc.scheme != 'file':
            dangerous_keywords = []
            for word in ['import', 'eval', 'exec', 'execfile', 'open']:
                if re.compile(r'\b' + word + r'\b').search(data):
                    dangerous_keywords.append(word)
            if dangerous_keywords:
                msg = _viewsBundle.formatStringFromName(
                    "schemeFileContainsDangerousWords.template",
                    [uri, 
                     (len(dangerous_keywords) > 1 and "s" or ""),
                     "'" + "', '".join(dangerous_keywords) + "'"])
                raise ServerException(nsError.NS_ERROR_INVALID_ARG, msg)
        
        targetPath = os.path.join(self._userSchemeDir, schemeBaseName + '.ksf')
        fd = open(targetPath, "w")
        fd.write(data)
        fd.close()
        
        newScheme = self._makeScheme(targetPath, True, unsaved=0)
        if newScheme is None:
            raise SchemeCreationException(_viewsBundle.formatStringFromName(
                                          "schemeFileNotCreatedFromFile.template",
                                          [targetPath]))
        self.addScheme(newScheme)
        return newScheme.name

    def activateScheme(self, newSchemeName):
        globalPrefs = components.classes["@activestate.com/koPrefService;1"].\
                            getService(components.interfaces.koIPrefService).prefs
        oldSchemeName = globalPrefs.getStringPref('editor-scheme')
        # Even if oldScheme == newScheme, go through this:
        globalPrefs.setStringPref('editor-scheme', newSchemeName)
        observerSvc = components.classes["@mozilla.org/observer-service;1"].\
                getService(components.interfaces.nsIObserverService)
        observerSvc.notifyObservers(self, 'scheme-changed', newSchemeName)
        return oldSchemeName

    def _addLogicalLinesWithTab(self, html, scimoz, lineStart, lineEnd,
                                language, lineNo, useLineNos,
                                style_bits, maxLineLength,
                                selectionOnly):
        if useLineNos:
            lineNoStr = '%4d    ' % lineNo
            prefixLen = len(lineNoStr)
            lineNoStr = lineNoStr.replace(' ', '&nbsp;')
            #lineNoStr = '%4d' % lineNo
            #prefixLen = len(lineNoStr) + 4
            #lineNoStr += '&nbsp;' * 4
            html.write('<br /><span class="linenumbers">%s</span>' % lineNoStr)
        else:
            prefixLen = 0
            html.write('<br />')
        actualLineLength = scimoz.getColumn(lineEnd)
        # Precondition: maxLineLength > 0
        maxLineLength -= prefixLen
        if maxLineLength <= 0:
            # This is silly -- they've specified a max line-width
            #    of 1 through 8, but we have a consistent story for it:
            # Do more or less what they requested,
            # and spit out one character per line.
            log.warn("Maximum line-width of %d is less-than the line-number region of %d",
                     maxLineLength, prefixLen)
            maxLineLength = 1
        if selectionOnly:
            start = max(scimoz.selectionStart, lineStart)
            end = min(lineEnd, scimoz.selectionEnd)
            if start > lineStart:
                leadingWS = ' ' * scimoz.getColumn(start)
            else:
                leadingWS = ''
        else:
            start = lineStart
            end = lineEnd
            leadingWS = ''
        currColumn = 0
        buff = scimoz.getStyledText(start, end)
        origText = leadingWS + "".join(buff[0::2])
        origStyles = [0] * len(leadingWS) + [ord(c) for c in buff[1::2]]
        textExpanded = []
        stylesExpanded = []
        tabWidth = scimoz.tabWidth
        while origText:
            tabIdx = origText.find("\t")
            if tabIdx == -1:
                textExpanded.append(origText)
                stylesExpanded += origStyles
                break
            part = origText[:tabIdx]
            textExpanded.append(part)
            currColumn += len(part)
            part = origStyles[:tabIdx]
            stylesExpanded += part
            
            part = " " * (tabWidth - (currColumn % tabWidth))
            textExpanded.append(part)
            tabStyle = origStyles[tabIdx]
            stylesExpanded += [tabStyle] * len(part)
            currColumn += len(part)

            origText   = origText[tabIdx + 1:]
            origStyles = origStyles[tabIdx + 1:]
            
        textWithoutTabs   = "".join(textExpanded)
        stylesWithoutTabs = stylesExpanded

        while textWithoutTabs:
            textSegment = textWithoutTabs[:maxLineLength]
            stylesSegment = stylesWithoutTabs[:maxLineLength]
            textWithoutTabs = textWithoutTabs[maxLineLength:]
            stylesWithoutTabs = stylesWithoutTabs[maxLineLength:]
            self._addPhysicalLineWithoutTabs(html, scimoz,
                                             textSegment,
                                             stylesSegment,
                                             language, lineNo,
                                             useLineNos, style_bits)
            if (textWithoutTabs):
                html.write('<br />')
                if useLineNos:
                    spacer = '&nbsp;'*8
                    html.write('<span class="linenumbers">' + spacer + '</span>')

    def _addLogicalLine(self, html, scimoz, lineStart, lineEnd, language,
                        lineNo, useLineNos, style_bits, maxLineLength,
                        selectionOnly):
        if (maxLineLength != 0
            and '\t' in scimoz.getTextRange(lineStart, lineEnd)):
            self._addLogicalLinesWithTab(html, scimoz, lineStart, lineEnd,
                                         language, lineNo,
                                         useLineNos, style_bits, maxLineLength,
                                         selectionOnly)
            return
        if useLineNos:
            lineNoStr = '%4d    ' % lineNo
            prefixLen = len(lineNoStr)
            lineNoStr = lineNoStr.replace(' ', '&nbsp;')
            html.write('<br /><span class="linenumbers">%s</span>' % lineNoStr)
        else:
            prefixLen = 0
            html.write('<br />')
        if maxLineLength == 0:
            maxLineLength = lineEnd - lineStart
        else:
            maxLineLength -= prefixLen
            if maxLineLength <= 0:
                # This is silly -- they've specified a max line-width
                #    of 1 through 8, but we have a consistent story for it:
                # Do more or less what they requested,
                # and spit out one character per line.
                log.warn("Maximum line-width of %d is less-than the line-number region of %d",
                         maxLineLength, prefixLen)
                maxLineLength = 1
        numlines, leftover = divmod(lineEnd - lineStart, maxLineLength)
        if leftover:
            numlines += 1
        for physline in range(numlines):
            start = lineStart + maxLineLength * physline
            end = min(lineEnd, start + maxLineLength)
            if selectionOnly:
                if end < scimoz.selectionStart:
                    continue
                start = max(scimoz.selectionStart, start)
                end = min(scimoz.selectionEnd, end)
                if start >= scimoz.selectionEnd:
                    return
            if start == end:
                continue
            self._addPhysicalLine(html, scimoz,
                                  start, end,
                                  language, lineNo,
                                  useLineNos, style_bits)
            if (lineEnd != end):
                html.write('<br />')
                if useLineNos:
                    spacer = '&nbsp;'*8
                    html.write('<span class="linenumbers">' + spacer + '</span>')
            if selectionOnly and end > scimoz.selectionEnd:
                return

    def _addPhysicalLine(self, html, scimoz, lineStart, lineEnd,
                         language, lineNo, useLineNos, style_bits):
        buff = scimoz.getStyledText(lineStart, lineEnd)
        regions = []
        mask = 0
        currentStyle = 0
        for bit in range(0, style_bits):
            mask |= 2**bit
        TXT, STY = 0, 1
        # Build a bunch of styled 'regions'
        for i in range(1, len(buff), 2):
            c = buff[i-1]
            s = ord(buff[i]) & mask
            if s != currentStyle or len(regions)==0:
                regions.append([[c], s])
                currentStyle = s
            else:
                # XXX this will probably cause problems on Mac files, but...
                if c != "\r": # ignore \r's, they just mess up printing.
                    regions[len(regions)-1][TXT].append(c)
        for i in regions:
            styles = self.getStyleTags(language, i[STY])
            content = "".join(i[TXT])
            if content in ["\r","\r\n","\n"]:
                html.write(content)
                continue
            content = content.expandtabs(scimoz.tabWidth)
            content = content.replace('&', '&amp;')
            content = content.replace(' ', '&nbsp;')
            content = content.replace('<', '&lt;')
            content = content.replace('>', '&gt;')
            # replace leading whitespace with non-breaking spaces
            line = styles[0] + content + styles[1]
            html.write(line)

    def _addPhysicalLineWithoutTabs(self, html, scimoz, 
                                    textWithoutTabs,
                                    stylesWithoutTabs,
                                    language, lineNo, useLineNos, style_bits):
        regions = []
        mask = 0
        currentStyle = 0
        for bit in range(0, style_bits):
            mask |= 2**bit
        # Build a bunch of styled 'regions'
        currentString = textWithoutTabs[0]
        currentStyle = stylesWithoutTabs[0] & mask
        for i in range(1, len(stylesWithoutTabs)):
            c = textWithoutTabs[i]
            if c == '\r':
                # This causes problems when printing, so skip
                continue
            s = stylesWithoutTabs[i] & mask
            if s != currentStyle:
                regions.append((currentString, currentStyle))
                currentStyle = s
                currentString = c
            else:
                currentString += c
        regions.append((currentString, currentStyle))
        for region in regions:
            content = region[0]
            if content in ["\r","\r\n","\n"]:
                html.write(content)
                continue
            content = content.replace('&', '&amp;')
            content = content.replace(' ', '&nbsp;')
            content = content.replace('<', '&lt;')
            content = content.replace('>', '&gt;')
            # replace leading whitespace with non-breaking spaces
            styles = self.getStyleTags(language, region[1])
            line = styles[0] + content + styles[1]
            html.write(line)

    def getStyleTags(self, language, styleNumber):
        """ Returns a tuple containing the open and close HTML tags"""
        if self._htmlStyleTags.has_key(styleNumber):
            return self._htmlStyleTags[styleNumber]
        language = str(language)
        if (styleNumber, language) in ScimozStyleNo2CommonName:
            stylename = ScimozStyleNo2CommonName[(styleNumber, language)]
        elif (styleNumber, language) in ScimozStyleNo2SpecificName:
            stylename = ScimozStyleNo2SpecificName[(styleNumber, language)]
        else:
            log.warn("No style information for style number %s for language %s", styleNumber, language)
            stylename = 'default'
        opener = '<span class="%s">' % stylename.replace(' ', '_')
        closer = '</span>'
        self._htmlStyleTags[styleNumber] = (opener, closer)
        return (opener, closer)



#---- internal support routines

def _initializeLanguageStyles(languageName):
    log.info("initializing style info for %s", languageName)
    languageStyles = []
    ISciMoz = components.interfaces.ISciMoz
    for common_name, scimoz_names in StateMap[languageName].items():
        for scimoz_name in scimoz_names:
            if isinstance(scimoz_name, str):
                scimoz_no = getattr(ISciMoz, scimoz_name)
            else:
                scimoz_no = int(scimoz_name) # should be noop
            key = (scimoz_no, languageName)
            if common_name in CommonStates:
                ScimozStyleNo2CommonName[key] = common_name
            ScimozStyleNo2SpecificName[key] = common_name
            languageStyles.append((scimoz_no, scimoz_name, common_name)) 
    ValidStyles[languageName] = languageStyles
    return languageStyles

def GetLanguageStyles(languageName):
    return ValidStyles.get(languageName) or _initializeLanguageStyles(languageName)

def _initializeStyleInfo():
    """Initialize the global style info variables."""
    log.debug("initializing style info...")
    koILintResult = components.interfaces.koILintResult
    for indic_name, component_name in IndicatorNameMap.items():
        indic_no = getattr(koILintResult, component_name, None)
        if indic_no is None:
            log.warn("applyScheme:: no koILintResult value for %r", component_name)
            continue
        IndicatorName2ScimozNo[indic_name] = indic_no

def scincolor2mozcolor(scincolor):
    # scincolor is an integer
    try:
        hexscin = '%06x' % scincolor
    except TypeError:
        log.warn("scincolor was %r", scincolor)
        hexscin = '000000'
    moz = hexscin[4:] + hexscin[2:4] + hexscin[:2]
    return '#' + moz

def mozcolor2scincolor(mozcolor):
    rgb = mozcolor[1:]
    r,g,b = int(rgb[:2], 16), int(rgb[2:4], 16), int(rgb[4:], 16)
    color = r+g*256+b*256*256
    return color

def microescape(c):
    if c == '<': return '&lt;'
    if c == '>': return '&gt;'
    if c == '&': return '&amp;'
    return c
