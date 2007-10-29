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

import sys, os, time
from xpcom import components, ServerException, COMException, nsError


#---- internal support routines

def _mkdir(newdir):
    """works the way a good mkdir should :)
        - already exists, silently complete
        - regular file in the way, raise an exception
        - parent directory(ies) does not exist, make them as well
    """
    if os.path.isdir(newdir):
        pass
    elif os.path.isfile(newdir):
        raise OSError("a file with the same name as the desired " \
                      "dir, '%s', already exists." % newdir)
    else:
        head, tail = os.path.split(newdir)
        if head and not os.path.isdir(head):
            _mkdir(head)
        #print "_mkdir %s" % repr(newdir)
        if tail:
            os.mkdir(newdir)


#---- components

class KoFileLoggingService:
    _com_interfaces_ = [components.interfaces.koIFileLoggingService]
    _reg_clsid_ = "07f746ed-3430-453f-9920-189a1aa69879"
    _reg_contractid_ = "@activestate.com/koFileLoggingService;1"
    _reg_desc_ = "File Logging Service"

    def __init__(self):
        koDirs = components.classes["@activestate.com/koDirs;1"]\
                 .getService(components.interfaces.koIDirs)
        self.logFileDir = os.path.join(koDirs.userDataDir, "log")
        self._infoSvc = components.classes["@activestate.com/koInfoService;1"]\
                        .getService(components.interfaces.koIInfoService)

    def GetLogFileName(self, category):
        """Each log call with a given category logs output to
        <appData>/log/<category>.txt."""
        return os.path.join(self.logFileDir, category+".txt")

    def _GetStampItems(self):
        return [
            time.strftime('%Y %b %d, %a, %H:%M:%S', time.localtime(time.time())),
            "%s %s" % (self._infoSvc.osSystem, self._infoSvc.osRelease),
            self._infoSvc.version,
            self._infoSvc.buildNumber,
            self._infoSvc.buildType,
            self._infoSvc.buildFlavour,
            self._infoSvc.mozBinDir,
            sys.prefix,
            ]
    
    def _GetStampItemNames(self):
        return ["Date-Time", "OS-System-Release",
                "Komodo-Version", "Komodo-Build-Number",
                "Komodo-Build-Type", "Komodo-Installer-Type",
                "Mozilla-Bin-Dir", "Python-Prefix"]

    def _PrepareLogFile(self, category):
        """Ensures that the log file (and its containing dir) exists.
        Also add a title bar.
        """
        if not os.path.exists(self.logFileDir):
            _mkdir(self.logFileDir)
        logFileName = self.GetLogFileName(category)
        if not os.path.exists(logFileName):
            fout = open(logFileName, "w")
            fout.write("""# This is a log file of Komodo measurements for
# category '%s'. Lines starting with '#' are comments
#
# A line format is:
#       <machine stamp>\t<category>\t<name>\t<measurements>
# where tokens are tab-delimited. Legend:
""" % category)
            fout.write("# %s\t%s\t<name>\t<measurements...>\n"\
                       % ('\t'.join(self._GetStampItemNames()), category))
            fout.close()

    def LogMeasurement(self, category, name, measurement):
        """Log a measurement set as one tab-delimited line in the log
        file associated with this category.
        """
        self._PrepareLogFile(category)
        tokens = self._GetStampItems() + [category, name, measurement]
        logFileName = self.GetLogFileName(category)
        fout = open(logFileName, "a")
        fout.write("\t".join(tokens) + "\n")
        fout.close()

    def LogMeasurementSet(self, category, name, measurements):
        """Log a measurement set as one tab-delimited line in the log
        file associated with this category.
        """
        self._PrepareLogFile(category)
        tokens = self._GetStampItems() + [category, name] + measurements
        logFileName = self.GetLogFileName(category)
        fout = open(logFileName, "a")
        fout.write("\t".join(tokens) + "\n")
        fout.close()
    


#---- self-test code

if __name__ == "__main__":
    fileLoggingSvc = components.classes["@activestate.com/koFileLoggingService;1"]\
                     .getService(components.interfaces.koIFileLoggingService)
    fileLoggingSvc.LogMeasurement("timing", "startup", "42")
    fileLoggingSvc.LogMeasurementSet("timing", "file-open", ["42", "43"])
    os.system('type "%s"' % fileLoggingSvc.GetLogFileName("timing"))
