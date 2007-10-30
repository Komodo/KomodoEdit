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

"""Komodo performance metrics gather via the timeline mechanism.

Here is how the timeline "perfs" work:
1. Komodo is started with the appropriate environment to activate the
   timeline logging.
2. A macro is run in that Komodo to do whatever tasks are being timed,
   like, say openning a file and closing it 100 times.
3. Komodo is closed.
4. The timeline log is processed by each of the perf_*() methods to
   extra the specific bit of information desired.

Each perf_*() method is structured like this:
    def perf_*(self):
        "description of this perf"
        timeline = _getTimeline()
        # extract datum from timeline...
        return result   # or: return {"result": result, "log": log}
"""

import os
import sys
import tempfile
import logging
import time

from perf import PerfError
import unitperf
import kocommandments as kc
import which
import process
import ptimeline


#---- globals

log = logging.getLogger("perf.timeline")

# Python and JavaScript macros to run when Komodo starts.
# The Python macro is run first.
pymacro = """
import kocommandments as kc
import tempfile
fname = tempfile.mktemp() + '.py'
f = open(fname, 'w')
f.write('#')
f.close()
kc.issue(r'open\t%s' % fname)
fname = tempfile.mktemp() + '.pl'
f = open(fname, 'w')
f.write('#')
f.close()
kc.issue(r'open\t%s' % fname)
"""

jsmacro = None



#---- timeline log gathering and parsing tools

__timelineRecords = None  # timeline log cache
def _getTimelineRecords():
    global __timelineRecords
    if __timelineRecords is not None:
        return __timelineRecords

    log.debug("start Komodo Jaguar")
    argv = [which.which("komodo"),
            "-j"]   # run Jaguar
    if log.isEnabledFor(logging.DEBUG):
        argv.append("-v")
    env = dict(os.environ) # get a copy
    env["NS_TIMELINE_ENABLE"] = "1"
    doNotDeleteLog = "NS_TIMELINE_LOG_FILE" in os.environ
    timelineLog = os.environ.get("NS_TIMELINE_LOG_FILE",
                                 tempfile.mktemp())
    log.debug("timeline log file: '%s'", timelineLog)

    env["NS_TIMELINE_LOG_FILE"] = timelineLog
    env["KOMODO_NONINTERACTIVE"] = "1"
    #env["KO_TIMELINE_PYXPCOM"] = "1"
    #env["KO_TIMELINE_SCIMOZ"] = "1"
    #env["KO_TIMELINE_PYOS"] = "1"

    try:
        p = process.Process(argv, env=env)
        time.sleep(1) # give it time to "announce" that it is starting up

        # Run macros.
        if pymacro is not None:
            log.debug("running Python macro")
            kc.issue("macro", ["--language", "python", repr(pymacro)])
        if jsmacro is not None:
            log.debug("running JavaScript macro")
            kc.issue("macro", ["--language", "javascript", repr(jsmacro)])
        
        #XXX How to synchronize??? Wait until 'quit' gets through?
        #    But .wait() doesn't work because it waits for komodo.exe
        #    and not mozilla.exe.
        kc.issue("quit")
        p.wait()
        time.sleep(15)

        __timelineRecords = ptimeline.parse(timelineLog)
        return __timelineRecords

    finally:
        if (not doNotDeleteLog
            and os.path.exists(timelineLog)
            and not log.isEnabledFor(logging.DEBUG)):
            try:
                os.remove(timelineLog)
            except OSError, ex:
                log.warn("Could not remove timeline log file, '%s': %s",
                         timelineLog, ex)
    


#---- perf cases

class TimelinePerfCase(unitperf.PerfCase):
    def perf_startup(self):
        """how long does Komodo take to startup"""
        records = _getTimelineRecords()
        # Looking for a line like this:
        #   00010.828 (002548b0):   startup complete
        marker = "startup complete"
        counter = ptimeline.count(marker, records)
        loglines = [str(r) for r in counter["records"]]
        if counter["count"] != 1:
            raise PerfError("There was more than '%s' marker in the "
                            "timeline:\n\t%s"
                            % (marker, '\n\t'.join(loglines)))
        startup_time = counter["records"][0].event_time
        return startup_time, '\n'.join(loglines)

    def perf_firstfileopen(self):
        """how long does it take to open the first file"""
        return self._getDeltaMarker('opening file', 'file opened', 0)
    
    def perf_secondfileopen(self):
        """how long does it take to open the second file"""
        return self._getDeltaMarker('opening file', 'file opened', 1)

    def _getDeltaMarker(self, startMarker, stopMarker, index):
        records = _getTimelineRecords()
        # Looking for a line like this:
        #   00010.828 (002548b0):   <startMarker>
        #   00011.828 (002548b0):   <stopMarker>
        # and returns the difference (in this case 1.0)
        counter = ptimeline.count(startMarker, records)
        loglines = [str(r) for r in counter["records"]]
        if not counter["count"]:
            raise PerfError("There were no '%s' markers in the "
                            "timeline:\n\t%s"
                            % (startMarker, '\n\t'.join(loglines)))
        start = counter["records"][index].event_time
        counter = ptimeline.count(stopMarker, records)
        loglines = [str(r) for r in counter["records"]]
        if not counter["count"]:
            raise PerfError("There were no '%s' markers in the "
                            "timeline:\n\t%s"
                            % (stopMarker, '\n\t'.join(loglines)))
        end = counter["records"][index].event_time
        return end-start, '\n'.join(loglines)

def suite():
    # If you have one PerfCase...
    return unitperf.makeSuite(TimelinePerfCase)

def perf_main():
    runner = unitperf.TextPerfRunner()
    runner.run(suite())

if __name__ == "__main__":
    perf_main()

