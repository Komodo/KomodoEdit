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

"""Language package for Tcl"""

from xpcom import components, ServerException
from xpcom.server import WrapObject, UnwrapObject
from koLanguageServiceBase import *
import os, re

import logging


log = logging.getLogger("TclLanguage")

class koTclLanguage(KoLanguageBase):
    name = "Tcl"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{491A0CE5-7180-425b-A27A-9EA36BCBA50F}"
    _reg_categories_ = [("komodo-language", name)]

    accessKey = 't'
    shebangPatterns = [
        re.compile(ur'\A#!.*tclsh.*$', re.IGNORECASE | re.MULTILINE),
        re.compile(ur'\A#!.*wish.*$', re.IGNORECASE | re.MULTILINE),
        re.compile(ur'\A#!.*expect.*$', re.IGNORECASE | re.MULTILINE),
        # As suggested here: http://www.tcl.tk/man/tcl8.4/UserCmd/tclsh.htm
        # Make sure we properly catch shebang lines like this:
        #   #!/bin/sh
        #   # the next line restarts using tclsh \
        #   exec tclsh "$0" "$@"
        re.compile(ur'\A#!.*^exec [^\r\n|\n|\r]*?tclsh', re.IGNORECASE | re.MULTILINE | re.DOTALL),
        re.compile(ur'\A#!.*^exec [^\r\n|\n|\r]*?wish', re.IGNORECASE | re.MULTILINE | re.DOTALL),
        re.compile(ur'\A#!.*^exec [^\r\n|\n|\r]*?expect', re.IGNORECASE | re.MULTILINE | re.DOTALL),
    ]
    primary = 1
    namedBlockRE = "^[ \t;]*(proc|class|method)\s+[\w:]+(.*\{\n)?"
    namedBlockDescription = 'Tcl procedures and [incr Tcl] classes'
    defaultExtension = ".tcl"

    # XXX read from config somewhere, download from ActiveState?
    downloadURL = 'http://www.ActiveState.com/Products/ActiveTcl'
    commentDelimiterInfo = { "line": [ "#" ]  }
    variableIndicators = '$'
    supportsSmartIndent = "brace"
    _dedenting_statements = [u'error', u'return', u'break', u'continue']

    sample = """proc loadFile { } {
    # a simple comment
    global f
    global f2
    global fileToOpen
    global fileOpened
    if [file exists $fileToOpen] {
        $f2.text delete 1.0 end
        set ff [open $fileToOpen]
        while {![eof $ff]} {
            $f2.text insert end [read $ff 1000]
        }
        close $ff
        set fileOpened $fileToOpen
    } else {
        $f.entry insert end " does not exist"
    }
}
"""

    styleStdin = components.interfaces.ISciMoz.SCE_TCL_STDIN
    styleStdout = components.interfaces.ISciMoz.SCE_TCL_STDOUT
    styleStderr = components.interfaces.ISciMoz.SCE_TCL_STDERR

    def __init__(self):
        KoLanguageBase.__init__(self)
        del self.matchingSoftChars["'"]

    def getVariableStyles(self):
        # Bug 95389 - support variable highlighting for Tcl regardless of
        # whether a variable def'n or use is clicked.
        return self._style_info._variable_styles + [components.interfaces.ISciMoz.SCE_TCL_IDENTIFIER]
    
    def get_lexer(self):
        if self._lexer is None:
            from codeintel2 import lang_tcl
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(components.interfaces.ISciMoz.SCLEX_TCL)
            keywords = lang_tcl.keywords
            try:
                version = components.classes["@activestate.com/koAppInfoEx?app=Tcl;1"].createInstance().version.split(".", 2)
                versionNum = tuple([int(x) for x in version])
                if versionNum >= (8, 6):
                    keywords = sorted(keywords + lang_tcl.v8_6_keywords)
            except:
                log.exception("Couldn't get the version")
            self._lexer.setKeywords(0, keywords)
            self._lexer.supportsFolding = 1
        return self._lexer

    def get_completer(self):
        if self._completer is None:
            self._completer = components.classes["@activestate.com/koTclCompletionLanguageService;1"].getService(components.interfaces.koICompletionLanguageService)
        return self._completer
    
    def softchar_accept_matching_double_quote(self, scimoz, pos, style_info, candidate):
        if pos == 0:
            return candidate
        prevPos = scimoz.positionBefore(pos)
        if scimoz.getStyleAt(prevPos) == scimoz.SCE_TCL_DEFAULT:
            return candidate
        return None


