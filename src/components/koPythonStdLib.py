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

"""
A place for light PyXPCOM interfaces to parts of Python's std library.
"""

import time
import shutil
import glob
from xpcom import components, nsError, ServerException, COMException

class KoTime:
    _com_interfaces_ = [components.interfaces.koITime]
    _reg_clsid_ = "{1CE2CCB1-83E0-4144-9187-32EA597BFC6D}"
    _reg_contractid_ = "@activestate.com/koTime;1"
    _reg_desc_ = "Parts of the Python Standard Library's time module"

    def asctime(self, timetuple):
        return time.asctime(timetuple)
    def localtime(self, secs):
        return time.localtime(secs)
    def time(self):
        return time.time()
    def strftime(self, format, timetuple):
        return time.strftime(format, timetuple)

class KoShUtil:
    _com_interfaces_ = [components.interfaces.koIShUtil]
    _reg_clsid_ = "{524CDBC0-0026-4502-9E1F-CB183473CD88}"
    _reg_contractid_ = "@activestate.com/koShUtil;1"
    _reg_desc_ = "Most of the Python Standard Library's shutil module"

    def __init__(self):
        global lastErrorSvc
        lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"]\
               .getService(components.interfaces.koILastErrorService)

    def copyfile(self, src, dst):
        try:
            shutil.copyfile(src, dst)
        except Exception, ex:
            lastErrorSvc.setLastError(0, str(ex))
            raise ServerException(nsError.NS_ERROR_INVALID_ARG, str(ex))
    def copymode(self, src, dst):
        try:
            shutil.copymode(src, dst)
        except Exception, ex:
            lastErrorSvc.setLastError(0, str(ex))
            raise ServerException(nsError.NS_ERROR_INVALID_ARG, str(ex))
    def copystat(self, src, dst):
        try:
            shutil.copystat(src, dst)
        except Exception, ex:
            lastErrorSvc.setLastError(0, str(ex))
            raise ServerException(nsError.NS_ERROR_INVALID_ARG, str(ex))
    def copy(self, src, dst):
        try:
            shutil.copy(src, dst)
        except Exception, ex:
            lastErrorSvc.setLastError(0, str(ex))
            raise ServerException(nsError.NS_ERROR_INVALID_ARG, str(ex))
    def copy2(self, src, dst):
        try:
            shutil.copy2(src, dst)
        except Exception, ex:
            lastErrorSvc.setLastError(0, str(ex))
            raise ServerException(nsError.NS_ERROR_INVALID_ARG, str(ex))
    def copytree(self, src, dst, symlinks):
        try:
            shutil.copytree(src, dst, symlinks)
        except Exception, ex:
            lastErrorSvc.setLastError(0, str(ex))
            raise ServerException(nsError.NS_ERROR_INVALID_ARG, str(ex))
    def rmtree(self, path, ignore_errors):
        try:
            shutil.rmtree(path, ignore_errors)
        except Exception, ex:
            lastErrorSvc.setLastError(0, str(ex))
            raise ServerException(nsError.NS_ERROR_INVALID_ARG, str(ex))

class KoGlob:
    _com_interfaces_ = [components.interfaces.koIGlob]
    _reg_clsid_ = "{FFB7AD74-3F67-46A0-A53D-A685D58EC040}"
    _reg_contractid_ = "@activestate.com/koGlob;1"
    _reg_desc_ = "Parts of the Python Standard Library's glob module"

    def glob(self, expression):
        return glob.glob(expression)

