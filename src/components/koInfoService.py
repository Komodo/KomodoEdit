#!python
# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

# Provide general (read-only) information about a Komodo build/installation
#
# This is accomplished by reading komodo-info.txt, distributed with
# a Komodo build/installation.

import sys
import os
import re
import time
from xpcom import components, nsError, ServerException, COMException
import logging

log = logging.getLogger("koInfoService")

# Defines not in the nsI IDL.
PROXY_SYNC    = 0x0001  # acts just like a function call.
PROXY_ASYNC   = 0x0002  # fire and forget.  This will return immediately and
                        # you will lose all return information.
PROXY_ALWAYS  = 0x0004  # ignore check to see if the eventQ is on the same
                        # thread as the caller, and alway return a proxied
                        # object.

class KoInfoService:
    _com_interfaces_ = [components.interfaces.koIInfoService]
    _reg_clsid_ = "{EB22F329-1D99-427a-B0E1-19DFF13AFBF7}"
    _reg_contractid_ = "@activestate.com/koInfoService;1"
    _reg_desc_ = "Komodo Information Service"

    def _getInfo(self, infoURL):
        log.debug("Getting Komodo information from '%s'.\n", infoURL)
        import xpcom.file
        fin = xpcom.file.URIFile(infoURL)
        datumRe = re.compile("^(?P<name>\w+)=(?P<value>.*)$")
        info = {}
        for line in fin.readlines():
            line = line.strip()
            datumMatch = datumRe.search(line)
            if datumMatch:
                info[datumMatch.group("name")] = datumMatch.group("value")
            else:
                log.error("Bogus data line, '%s', in Komodo information "\
                          "file, '%s'.\n", line, infoURL)
                raise ServerException(nsError.NS_ERROR_UNEXPECTED)
        return info

    def __init__(self):
        self.platform = sys.platform
        self.isWindows = sys.platform.startswith("win")
        # XXX bug 33823
        # when building with gtk2, platform.py functions fail preventing
        # komodo startup.  os.uname should work fine on *nix platforms.
        if sys.platform.startswith("win"):
            import platform
            self.osSystem = platform.system()
            self.osRelease = platform.release()
            self.osVersion = platform.version()
        else:
            self.osSystem,node,self.osRelease,self.osVersion,machine = os.uname()
        
        infoURL = "chrome://komodo/content/resources/komodo-info.txt"
        info = self._getInfo(infoURL)
        self.version = info["version"]
        self.buildNumber = info["buildNumber"]
        self.buildASCTime = info["buildASCTime"]
        self.buildPlatform = info["buildPlatform"]
        self.mozBinDir = info["mozBinDir"]
        self.buildType = info["buildType"]
        self.buildFlavour = info["buildFlavour"]
        self.productType = info["productType"]
        self.prettyProductType = info["prettyProductType"]
        # We are in non-interactive mode if KOMODO_NONINTERACTIVE is set
        # and non-zero.
        KOMODO_NONINTERACTIVE = os.environ.get("KOMODO_NONINTERACTIVE")
        self.nonInteractiveMode = 0
        if KOMODO_NONINTERACTIVE:
            try:
                KOMODO_NONINTERACTIVE = int(KOMODO_NONINTERACTIVE)
            except ValueError:
                pass
            if KOMODO_NONINTERACTIVE:
                self.nonInteractiveMode = 1

if __name__ == "__main__":
    info = components.classes['@activestate.com/koInfoService;1'].\
        getService(components.interfaces.koIInfoService)
    print "platform: %r" % info.platform
    print "osSystem: %r" % info.osSystem
    print "osRelease: %r" % info.osRelease
    print "osVersion: %r" % info.osVersion
    print "version: %r" % info.version
    print "buildNumber: %r" % info.buildNumber
    print "buildASCTime: %r" % info.buildASCTime
    print "mozBinDir: %r" % info.mozBinDir
    print "buildType: %r" % info.buildType
    print "buildFlavour: %r" % info.buildFlavour
    print "productType: %r" % info.productType
    print "nonInteractiveMode: %r" % info.nonInteractiveMode
