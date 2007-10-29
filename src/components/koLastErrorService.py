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

# The implementation of the Komodo LastError service.

import threading
from xpcom import components
import logging
log = logging.getLogger('lastErrorService')
#log.setLevel(logging.INFO)

#---- PyXPCOM component implementation

class KoLastErrorService:
    _com_interfaces_ = components.interfaces.koILastErrorService
    _reg_desc_ = "Last Error Service"
    _reg_clsid_ = "{7FA46F12-BB76-4960-BE71-F59422A6AA17}"
    _reg_contractid_ = "@activestate.com/koLastErrorService;1"

    def __init__(self):
        # Dictionary of last errors for each thread.
        # - this is lazily filled out
        # - an "error" is a tuple: (<error code>, <error message>)
        self._errors = {}

    def setLastError(self, code, message):
        name = threading.currentThread().getName()
        if code or message:
            log.info("set last error for thread %s: %r, %r",
                     name, code, message)
        self._errors[name] = (code, message)

    def getLastError(self):
        name = threading.currentThread().getName()
        code, message = self._errors.get(name, (0, ''))
        log.info("get last error for thread %s: %r, %r",
                 name, code, message)
        return code, message

    def getLastErrorCode(self):
        return self.getLastError()[0]
    def getLastErrorMessage(self):
        return self.getLastError()[1]


