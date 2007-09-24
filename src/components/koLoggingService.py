#!/usr/bin/env python
# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

"""Komodo Logging system service"""

import os
import types
import logging

from xpcom import components, nsError, ServerException, COMException, server
from xpcom._xpcom import PROXY_SYNC, PROXY_ALWAYS, PROXY_ASYNC, getProxyForObject

#---- mods to the Python logging system

class KoLogger(logging.Logger):
    _com_interfaces_ = [components.interfaces.koILogger]
    _reg_clsid_ = "{EE4DC45E-1BE7-4C3C-B521-1434FA1CF054}"
    _reg_contractid_ = "@activestate.com/koLogger;1"
    _reg_desc_ = "Komodo Logger"
    
# fixup the root logger to use an XPCOM logger class
logging.root = KoLogger("root", logging.WARNING)
logging.Logger.root = logging.root
logging.Logger.manager = logging.Manager(logging.Logger.root)

logging.setLoggerClass(KoLogger)

#---- XPCOM logging service

class KoLoggingService:
    """A service from which JavaScript code can use the Python logging
    infrastructure.
    """
    _com_interfaces_ = [components.interfaces.koILoggingService]
    _reg_clsid_ = "{5DBBF27D-F084-432B-9422-9C9B4707452D}"
    _reg_contractid_ = "@activestate.com/koLoggingService;1"
    _reg_desc_ = "Komodo Logging system service"

    def __init__(self):
        hdlr = logging.StreamHandler()
        fmt = logging.Formatter("%(levelname)s: %(name)s: %(message)s")
        hdlr.setFormatter(fmt)
        logging.root.addHandler(hdlr)
        
    def getLogger(self, logger_name):
        return logging.getLogger(logger_name)
     
    def getLoggerNames(self):
        names = logging.Logger.manager.loggerDict.keys()
        names.sort()
        return names


