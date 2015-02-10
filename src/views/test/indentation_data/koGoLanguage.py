#!/usr/bin/env python

"""Go-specific Language Services implementations."""

import logging

from xpcom import components
from koLanguageServiceBase import KoLanguageBase, FastCharData, KoLanguageBaseDedentMixin

log = logging.getLogger('koGoLanguage')
#log.setLevel(logging.DEBUG)

sci_constants = components.interfaces.ISciMoz

class koGoLanguage(KoLanguageBase, KoLanguageBaseDedentMixin):
    name = "Go"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{2d6ed8b6-f079-441a-8b5a-10ef781cb989}"
    _reg_categories_ = [("komodo-language", name)]
    _com_interfaces_ = KoLanguageBase._com_interfaces_ + \
                       [components.interfaces.koIInterpolationCallback]

    modeNames = ['go']
    primary = 1
    internal = 0
    accessKey = 'g'
    defaultExtension = ".go"
    commentDelimiterInfo = {
        "line": [ "//" ],
        "block": [ ("/*", "*/") ],
        "markup": "*",
    }
    _dedenting_statements = [u'goto', u'return', u'break', u'continue']
    
    namedBlockRE = "^[ \t]*?(func\s+(?:\(.*?\)\s*)?\w|package\s+\w)"
    namedBlockDescription = 'Go functions, methods and packages'
    supportsSmartIndent = "brace"
    # The following sample contains embedded tabs because that's the Go way.
    sample = r"""\
package commands

import (
	"encoding/json"
)
type Filters []string
func (f *Filters) String() string {
	a := "a string"
	b := 'c' // a char
	c := 43 // a num
	return fmt.Sprint(*f)
}
/* Block comment
on these two lines */
    """

    def __init__(self):
        KoLanguageBase.__init__(self)
        self._style_info.update(
            _block_comment_styles = [sci_constants.SCE_C_COMMENT,
                                     sci_constants.SCE_C_COMMENTDOC,
                                     sci_constants.SCE_C_COMMENTDOCKEYWORD,
                                     sci_constants.SCE_C_COMMENTDOCKEYWORDERROR],
            _variable_styles = [components.interfaces.ISciMoz.SCE_C_IDENTIFIER]
            )
        self._setupIndentCheckSoftChar()
        self._fastCharData = \
            FastCharData(trigger_char=";",
                         style_list=(sci_constants.SCE_C_OPERATOR,),
                         skippable_chars_by_style={ sci_constants.SCE_C_OPERATOR : "])",},
                         for_check=True)
        # And add the new default prefs if they don't exist
        globalPrefs = components.classes["@activestate.com/koPrefService;1"]\
                          .getService(components.interfaces.koIPrefService).prefs
        # Chunk adding prefs based on which ones they were added with.
        if not globalPrefs.hasPref("gocodeDefaultLocation"):
            globalPrefs.setStringPref("gocodeDefaultLocation", "")
        if not globalPrefs.hasPref("godefDefaultLocation"):
            globalPrefs.setStringPref("godefDefaultLocation", "")
        if not globalPrefs.hasPref("golangDefaultLocation"):
            globalPrefs.setStringPref("golangDefaultLocation", "")
            globalPrefs.setStringPref("Go/newEncoding", "utf-8")
            globalPrefs.setLongPref("Go/indentWidth", 8)
            globalPrefs.setBooleanPref("Go/useTabs", True)
