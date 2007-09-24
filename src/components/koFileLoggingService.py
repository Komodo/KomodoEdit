#!/usr/bin/env python
# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

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
