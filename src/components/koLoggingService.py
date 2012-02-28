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

"""Komodo Logging system service"""

import logging

from xpcom import components


#---- mods to the Python logging system

class KoLogger(logging.Logger):
    _com_interfaces_ = [components.interfaces.koILogger]
    _reg_clsid_ = "{EE4DC45E-1BE7-4C3C-B521-1434FA1CF054}"
    _reg_contractid_ = "@activestate.com/koLogger;1"
    _reg_desc_ = "Komodo Logger"

logging.setLoggerClass(KoLogger)

# Fixup the root logger to use an XPCOM logger class.
logging.root = KoLogger("root", logging.WARNING)
logging.Logger.root = logging.root
#TODO: This replacement is orphaning all the already created loggers.
#      Cannot do this:
#           logging.Logger.manager.root = logging.root
#      because the existing loggers aren't XPCOM components.
#      Try to at least maintain as much of the levels as we can...
levels = {}
for key in logging.Logger.manager.loggerDict.keys():
    try:
        level = logging.Logger.manager.loggerDict[key].level
        if level != logging.NOTSET:
            levels[key] = level
    except Exception, e:
        pass
logging.Logger.manager = logging.Manager(logging.Logger.root)
for key, level in levels.items():
    logging.getLogger(key).setLevel(level)
del levels


#---- XPCOM logging service

class KoLoggingService(object):
    """A service from which JavaScript code can use the Python logging
    infrastructure.
    """
    _com_interfaces_ = [components.interfaces.koILoggingService]
    _reg_clsid_ = "{5DBBF27D-F084-432B-9422-9C9B4707452D}"
    _reg_contractid_ = "@activestate.com/koLoggingService;1"
    _reg_desc_ = "Komodo Logging system service"

    def __init__(self):
        hdlr = logging.StreamHandler()
        fmt = logging.Formatter("[%(asctime)s] [%(levelname)s] %(name)s: %(message)s")
        hdlr.setFormatter(fmt)
        logging.root.addHandler(hdlr)
        
    def getLogger(self, logger_name):
        return logging.getLogger(logger_name)
     
    def getLoggerNames(self):
        names = logging.Logger.manager.loggerDict.keys()
        names.sort()
        return names


