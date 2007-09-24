#!/usr/bin/env python
# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

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

