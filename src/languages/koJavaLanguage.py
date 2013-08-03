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

class koJavaLanguage(KoLanguageBase, KoLanguageBaseDedentMixin):
    name = "Java"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{A5907F34-F7CC-40ec-898A-551CBAA0557B}"
    _reg_categories_ = [("komodo-language", name)]

    accessKey = 'a'
    defaultExtension = ".java"
    extraFileAssociations = ['*.groovy']

    commentDelimiterInfo = {
        "line": [ "//" ],
        "block": [ ("/*", "*/") ],
        "markup": "*",
    }
    sample = """import java.awt.*;
import java.util.*;

// This is a comment
public class Showtime extends Frame implements Runnable {
    Button quitBtn;
    Label  timeLbl;
    Thread tthread;
 
    public Showtime() {
        super(\"Java Showtime\");
        setLayout(new FlowLayout());
        quitBtn = new Button(\"Quit\");
        timeLbl = new Label((new Date()).toString());
        add(quitBtn);   add(timeLbl);
        pack();
        show();
        tthread = new Thread(this);
        tthread.run();
    }
 
    public boolean action(Event evt, Object what) {
        if (evt.target == quitBtn) {
                tthread.stop();
                System.exit(0);
        }
        return super.action(evt,what);
    }
 
    public void run() {
        while(true) {
                try { Thread.sleep(10000); } 
                catch (Exception e) { }
                timeLbl.setText((new Date()).toString());
        }
    }

    public static void main(String [] argv) {
        Showtime st = new Showtime();
    }
}
"""
    _dedenting_statements = [u'throw', u'return', u'break', u'continue']
    _indenting_statements = [u'case']
    supportsSmartIndent = "brace"

    def __init__(self):
        KoLanguageBase.__init__(self)
        KoLanguageBaseDedentMixin.__init__(self)
        self._style_info.update(
            _block_comment_styles = [sci_constants.SCE_C_COMMENT,
                                     sci_constants.SCE_C_COMMENTDOC,
                                     sci_constants.SCE_C_COMMENTDOCKEYWORD,
                                     sci_constants.SCE_C_COMMENTDOCKEYWORDERROR]
            )
        self._setupIndentCheckSoftChar()
        self._fastCharData = \
            FastCharData(trigger_char=";",
                         style_list=(sci_constants.SCE_C_OPERATOR, ),
                         skippable_chars_by_style={ sci_constants.SCE_C_OPERATOR : "])", },
                         for_check=True)

    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(components.interfaces.ISciMoz.SCLEX_CPP)
            self._lexer.setKeywords(0, self._keywords)
            self._lexer.setProperty('fold.cpp.syntax.based', '1')
            self._lexer.supportsFolding = 1
        return self._lexer


    _keywords = ["abstract", "boolean", "break", "byte", "case",
                 "catch", "char", "class", "const", "continue", "default", "do",
                 "double", "else", "extends", "final", "finally", "float", "for",
                 "future", "generic", "goto", "if", "implements", "import",
                 "inner", "instanceof", "int", "interface", "long", "native",
                 "new", "null", "operator", "outer", "package", "private",
                 "protected", "public", "rest", "return", "short", "static",
                 "super", "switch", "synchronized", "this", "throw", "throws",
                 "transient", "try", "var", "void", "volatile", "while"]
