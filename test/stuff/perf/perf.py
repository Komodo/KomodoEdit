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

"""
    Komodo Performance Metric Suite

    Usage:

        bk perf [<options>...] [<perfs>...]

    Options:
        -v, --verbose   verbose output
        -q, --quiet     quiet output
        -h, --help      print this text and exit
        -x <perfname>, --exclude=<perfname>
                        Exclude the named perf from the set of perfs to be
                        run.  This can be used multiple times to specify
                        multiple exclusions.
        -l, --list      Just list the perf modules. Don't run them.

    Smoke Options:
        --smoke             Log perf results in Smoke.
        -s <server>, --server=<server>
                            Smoke server to use.
        --project-id=<id>   Smoke project id to use. Defaults to the
                            given Smoke server's project_id for
                            "komodo".
        --build-id=<id>     Smoke build id to use. Defaults to a "dev
                            build id" for the current machine and Komodo
                            "build tree" build.

    This will find all modules whose name is "perf_*" in the test and
    other directories, and run them.  Various command line options
    provide additional facilities.

    If non-option arguments are present, they are names for perfs to run.
    If no perf names are given, all perfs are run.

    Examples:
        bk perf             # run all metrics
        bk perf -x startup  # run all but the startup perf metric
"""

import os
import sys
import getopt
import glob
import time
import types
import tempfile
import pprint
import imp
import logging

import smokeclient #XXX consider only requiring this iff --smoke
import unitperf



#---- exceptions

class PerfError(Exception):
    pass



#---- globals

log = logging.getLogger("perf")

gPerfDirs = [
    # Add the relative path to each directory from which to gather
    # perf_* modules.
    os.curdir,
]



#---- smoke utility stuff

class SmokePerfRunner:
    """Unitperf PerfSuite runner to add results to a Smoke database.
    
    Usage is similar to unitperf.py's standard TextPerfRunner.

        runner = SmokePerfRunner(...)
        result = runner.run(<perf>)
        
    where <perf> is a PerfCase or PerfSuite instance. Output is printed
    for each perf as it is run and the results are added to the
    configured Smoke database.
    """
    def __init__(self, server=None, project_id=None, build_id=None,
                 machine_id=None):
        """Create a Smoke Unitperf runner.

        "server" is the smoke server to use. Fallsback to SMOKE_SERVER
            environment variable.
        "project_id" is the smoke project id to which the perfs apply.
            Falls back to SMOKE_PROJECTID environment variable.
        "build_id" is the id of the build on which perfs are being run.
            Falls back to SMOKE_BUILDID environment variable.
        "machine_id" is the id of the machine on which the perfs are
            being run. Falls back to SMOKE_MACHINEID environment
            variable, or the current machine.
        """
        self.server = server
        self.project_id = project_id
        self.build_id = build_id
        self.machine_id = machine_id

    def run(self, suite):
        # Run the perf suite.
        result = SmokePerfResult(server=self.server,
                                 project_id=self.project_id,
                                 build_id=self.build_id,
                                 machine_id=self.machine_id)
        start = time.time()
        suite(result)
        stop = time.time()
        elapsed = float(stop - start)

        # Print some summary results (similar to TextPerfRunner's
        # summary output).
        nperfs = result.perfsRun
        print "Ran %d perf%s in %.3fs."\
              % (nperfs, nperfs == 1 and "" or "s", elapsed)
        print
        return result
        

class _QuietSmokePerfResult(unitperf.PerfResult):
    """A PerfResult that adds data to a smoke server."""
    def __init__(self, server=None, project_id=None, build_id=None,
                 machine_id=None):
        unitperf.PerfResult.__init__(self)
        self.server = server
        self.project_id = project_id
        self.build_id = build_id
        self.machine_id = machine_id

    def startPerf(self, perf):
        unitperf.PerfResult.startPerf(self, perf)
        self.starttime = time.time()

    def addResult(self, perf, result, log=None):
        unitperf.PerfResult.addResult(self, perf, result)
        perfspec_id = self._getPerfSpecId(perf)
        smokeclient.addPerf(result=result,
                            log=log,
                            starttime=self.starttime,
                            perfspec_id=perfspec_id,
                            machine_id=self.machine_id,
                            build_id=self.build_id,
                            server=self.server)

    def _getPerfSpecId(self, perf):
        name = perf.id()
        try:
            perfspec_id = smokeclient.getPerfSpecId(
                name=name,
                project_id=self.project_id,
                server=self.server)
        except smokeclient.SmokeClientError, ex:
            perfspec_id = smokeclient.addPerfSpec(
                name=name,
                description=perf.shortDescription(),
                project_id=self.project_id,
                server=self.server)
        return perfspec_id
        

class SmokePerfResult(_QuietSmokePerfResult):
    """A PerfResult that adds data to a smoke server
    (_QuietSmokePerfResult) and prints progress data on stdout (this
    class).
    """
    def startPerf(self, perf):
        _QuietSmokePerfResult.startPerf(self, perf)
        sys.stdout.write(str(perf) + " ... ")
        sys.stdout.flush()

    def addResult(self, perf, result, log=None):
        _QuietSmokePerfResult.addResult(self, perf, result, log)
        sys.stdout.write("%s\n" % result)




#---- utility routines

def _getPerfs(dir):
    """Return a list of perf names in the given directory."""
    perfPyFiles = glob.glob(os.path.join(dir, "perf_*.py"))
    modules = [os.path.splitext(os.path.basename(f))[0]
               for f in perfPyFiles if f and f.endswith(".py")]

    packages = []
    for f in glob.glob(os.path.join(dir, "perf_*")):
        if os.path.isdir(f) and "." not in f:
            if os.path.isfile(os.path.join(dir, f, "__init__.py")):
                packages.append(os.path.basename(f))

    return modules + packages


def _setUp():
    pass


def _tearDown():
    pass


def perf(modules, excludes=[], justList=0,
         # Smoke options:
         useSmoke=0, server=None, project_id=None, build_id=None):
    log.debug("perf(modules=%r, excludes=%r, useSmoke=%r, "
              "server=%r, project_id=%r, build_id=%r)", modules,
              excludes, useSmoke, server, project_id, build_id)

    # Trim '.py' from use supplied arguments. They might have gotten
    # there via shell expansion.  Also, allow the user to optionally
    # drop the standard "perf_" prefix from given perf names.
    for i in range(len(modules)):
        if modules[i].endswith(".py"):
            modules[i] = modules[i][:-3]
        if not modules[i].startswith("perf_"):
            modules[i] = "perf_"+modules[i]
    for i in range(len(excludes)):
        if excludes[i].endswith(".py"):
            excludes[i] = excludes[i][:-3]
        if not excludes[i].startswith("perf_"):
            excludes[i] = "perf_"+excludes[i]

    # Find all available perfs.
    perfmap = {} # mapping of perf names to their directory
    for dir in gPerfDirs:
        for name in _getPerfs(dir):
            if name in perfmap:
                raise PerfError("perf name collision: perf '%s' existing "
                                "in both '%s' and '%s'", name,
                                perfmap[name], dir)
            perfmap[name] = dir
    
    # If user specified modules, then use only those.
    #XXX Perhaps should warn or error out if any or all of given perf
    #    names do not exist?
    if modules:
        for name in perfmap.keys():
            if name not in modules:
                del perfmap[name]

    # Drop specifically excluded modules.
    for name in excludes:
        if name in perfmap:
            del perfmap[name]

    if justList:
        pprint.pprint(perfmap)
        return

    # Aggregate the PerfSuite's from each module into one big one.
    suites = []
    for name, dir in perfmap.items():
        file, filename, desc = imp.find_module(name, [dir])
        try:
            module = imp.load_module(name, file, filename, desc)
        finally:
            if file:
                file.close()
        suite = getattr(module, "suite", None)
        if suite is not None:
            suites.append(suite())
        else:
            log.warn("module '%s' (in '%s') does not have a suite() method",
                     name, dir)
    suite = unitperf.PerfSuite(suites)

    # Run the suite.
    if useSmoke:
        runner = SmokePerfRunner(server=server, project_id=project_id,
                                 build_id=build_id)
    else:
        runner = unitperf.TextPerfRunner(sys.stdout)
    result = runner.run(suite)



#---- mainline

def main(argv):
    logging.basicConfig()
    log.setLevel(logging.INFO)

    # parse options
    try:
        opts, modules = getopt.getopt(argv[1:], "hvqx:ls:",
            ["help", "verbose", "quiet", "exclude=", "list",
             "smoke", "server=", "project-id=", "build-id="])
    except getopt.error, ex:
        log.error(str(ex))
        return 1
    excludes = []
    justList = 0
    useSmoke = 0
    server = None
    project_id = None
    build_id = None
    for opt, optarg in opts:
        if opt in ("-h", "--help"):
            print __doc__
            return 0
        elif opt in ("-v", "--verbose"):
            log.setLevel(logging.DEBUG)
        elif opt in ("-q", "--quiet"):
            log.setLevel(logging.WARN)
        elif opt in ("-x", "--exclude"):
            excludes += optarg.split(',')
        elif opt in ("-l", "--list"):
            justList = 1
        elif opt == "--smoke":
            useSmoke = 1
        elif opt in ("-s", "--server"):
            server = optarg
        elif opt == "--project-id":
            project_id = optarg
        elif opt == "--build-id":
            build_id = optarg

    # Try to determine reasonable defaults for Smoke options, if
    # necessary.
    if useSmoke:
        if project_id is None and "SMOKE_PROJECTID" not in os.environ:
            log.info("Falling back to Smoke's project id for 'komodo'.")
            project_id = smokeclient.getProjectId("komodo", server=server)
        if build_id is None and "SMOKE_BUILDID" not in os.environ:
            log.info("Falling back to a 'dev build id' for the local build.")
            versionTxt = os.path.join(os.path.dirname(__file__),
                                      os.pardir, "src", "version.txt")
            version = open(versionTxt, 'r').read()
            build_id = smokeclient.getDevBuildId("build-tree", version,
                                                 project_id=project_id,
                                                 server=server)

    _setUp()
    try:
        perf(modules, excludes=excludes, justList=justList,
             # Smoke options:
             useSmoke=useSmoke, server=server, project_id=project_id,
             build_id=build_id)
    finally:
        _tearDown()


if __name__ == "__main__":
    __file__ = sys.argv[0]
    sys.exit( main(sys.argv) )


