#!python
# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

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


