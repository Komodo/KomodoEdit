#!/usr/bin/env python
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

from xpcom import components



#---- component implementation

class KoMacroService:
    _com_interfaces_ = [components.interfaces.koIMacroService]
    _reg_clsid_ = "D6126643-84DC-4DDE-9101-C4BF9B40F588"
    _reg_contractid_ = "@activestate.com/koMacroService;1"
    _reg_desc_ = "Service for running Macros"

    def __init__(self):
        # ensure that the koPartService is listening
        koPartSvc = components.classes["@activestate.com/koPartService;1"]\
            .getService(components.interfaces.koIPartService)
        self._observerSvc = components.classes["@mozilla.org/observer-service;1"]\
            .getService(components.interfaces.nsIObserverService)

    @components.ProxyToMainThreadAsync
    def runString(self, language, code):
        self._observerSvc.notifyObservers(self, language + '_macro', code)

    def runFile(self, language, filename):
        code = open(filename).read()
        self.runString(language, code)

