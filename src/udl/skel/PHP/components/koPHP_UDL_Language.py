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

"""Language package for PHP"""

import os
import re
import logging

import process
import koprocessutils

from koLanguageServiceBase import *
from koUDLLanguageBase import KoUDLLanguage
from xpcom import components, ServerException
import xpcom.server

sci_constants = components.interfaces.ISciMoz



def registerLanguage(registry):
    registry.registerLanguage(KoPHPLanguage())
    

class KoPHPLanguage(KoUDLLanguage, KoLanguageBaseDedentMixin):
    name = "PHP"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{F472CC39-0902-4d92-8A5B-7DD0F612F119}"
    _reg_categories_ = [("komodo-language", name)]
    _com_interfaces_ = [components.interfaces.koILanguage,
                        components.interfaces.nsIObserver]

    lexresLangName = "PHP"
    lang_from_udl_family = {'CSL': 'JavaScript', 'M': 'HTML', 'CSS': 'CSS',
                            'SSL': 'PHP'}

    accessKey = 'h'
    primary = 1
    shebangPatterns = [
        re.compile(ur'\A#!.*php.*$', re.IGNORECASE | re.MULTILINE),
    ]
    namedBlockRE = r'^(.*?function\s+[&]*?\s*[\w_]*)|(^.*?(?<=\s)(?:class|interface)\s+[\w_]*)'
    namedBlockDescription = 'PHP functions and classes'
    defaultExtension = ".php"
    variableIndicators = '$'
    downloadURL = 'http://php.net/'
    commentDelimiterInfo = {
        "line": [ "//", "#" ],
        "block": [ ("/*", "*/") ],
        "markup": "*",
    }
    _dedenting_statements = [u'throw', u'return', u'break', u'continue']
    supportsSmartIndent = "brace"
    sample = """<?php
class foo {
    // a comment
    var $a;
    var $b;
    function display() {
        echo "This is class foo";
        echo "a = ".$this->a."";
        echo "b = {$this->b}";
    }
    function mul() {
        return $this->a*$this->b;
    }
};

$foo1 = new foo;
$foo1->a = 2;
$foo1->b = 5;
$foo1->display();
echo $foo1->mul()."";
?>"""    
        
    def __init__(self):
        KoUDLLanguage.__init__(self)
        KoLanguageBaseDedentMixin.__init__(self)
        
        # get the comment prefs and set that, then observe for pref changes
        self.__prefs = components.classes["@activestate.com/koPrefService;1"].\
            getService(components.interfaces.koIPrefService).prefs
        self.commentDelimiterInfo['line'] = self.__prefs.getStringPref("phpCommentStyle").split(",")

        self._observer = xpcom.server.WrapObject(self,
                                      components.interfaces.nsIObserver)
        self.__prefs.prefObserverService.addObserver(self._observer, "phpCommentStyle", 0)
        self._setupIndentCheckSoftChar()
        self._fastCharData = \
            FastCharData(trigger_char=";",
                         style_list=(sci_constants.SCE_UDL_SSL_OPERATOR,),
                         skippable_chars_by_style={ sci_constants.SCE_UDL_SSL_OPERATOR : "])",},
                         
                         for_check=True)
    
    def observe(self, subject, topic, data):
        if topic == "phpCommentStyle":
            self.commentDelimiterInfo['line'] = self.__prefs.getStringPref("phpCommentStyle").split(",")
            self._commenter = None
	else:
	    KoUDLLanguage.observe(self, subject, topic, data)

    def get_interpreter(self):
        if self._interpreter is None:
            self._interpreter = components.classes["@activestate.com/koAppInfoEx?app=PHP;1"].getService()
        return self._interpreter

