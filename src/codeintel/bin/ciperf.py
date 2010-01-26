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
    ciperf - helper for measuring Code Intel performance

    Usage:
        ciperl --suite                              # run perf suite
        ciperf -l                                   # list perf functions
        ciperf -t [OPTIONS] PERF-FUNCTION-NAMES...  # time perf function
        ciperf -c [OPTIONS] PERF-FUNCTION-NAMES...  # coverage test
        ciperf -r [OPTIONS] PERF-FUNCTION-NAMES...  # just run perf func

    Options:
        -h, --help              print this help and exit
        -V, --version           print version and exit
        -v, --verbose           verbose output

        -f <cidb path>
            Specify a CodeIntel DB to work with. By default the codeintel.db
            in your locally configured Komodo dev build is used.
            
        -n, --number <num>
            Number of times to run the perf functions when in timing mode
            (-t option). If not specified an "appropriate" number of times
            is automatically determined.

    Mode Options:
        -S, --suite             run the baseline performance suite
        -l, --list              list available performance functions
        -t, --timeit            (default mode) Time the given perf function.
        -r, --run               Just run the given perf function.
        -c, --coverage          Dump coverage information on perf function.
    
    Examples:
        # Run the baseline CodeIntel performance suite
        ciperf --suite

        # get verbose information on available tests
        ciperf -lv

        # Time a "typical" quick Perl editing session.
        ciperf -f perf.db -r setup_komodo_perl_user
        ciperf -f perf.db -t komodo_perl_user
"""

import os
import sys
import re
import time
import glob
import getopt
import pprint
import operator
import logging
import imp
import socket
import timeit

import codeintel
from codeintel.scheduler import PRIORITY_OPEN
from codeintel import ScanRequest, CodeIntelError
from codeintel.common import getHostname, getPlatform
import threading


class Error(Exception):
    pass


#---- globals

_version_ = (0, 1, 0)
log = logging.getLogger("ciperf")
g_corpus_dir = os.path.join(os.path.dirname(__file__), "test", "perf_corpus")


#---- performance routines

def perf_cidb_size(dbpath):
    """Scan current Perl lib into a new CIDB and dump size information.
    
    The CIDB path selected with the "-f" option is ignored. Run this test
    with:
        ciperf -n 1 -r cidb_size
    """
    if sys.platform == "win32":
        clock = time.clock # time.clock is best on Windows
    else:
        clock = time.time  # time.time is best on non-Win platforms

    results = []
    dbpath = "perf_cidb_size.db"
    if os.path.exists(dbpath):
        os.remove(dbpath)
        time.sleep(1)

    import which
    perl = which.which("perl")
    perllib = os.path.join(os.path.dirname(os.path.dirname(perl)), "lib")

    mgr = codeintel.Manager()
    mgr.initialize(dbpath)
    starttime = time.time()
    try:
        print "load directory '%s'" % perllib
        mgr.batchUpdateRequest("directory", perllib, "Perl")
        mgr.batchUpdateStart()
        mgr.batchUpdateWait()
        errors = mgr.batchUpdateGetErrors()
    finally:
        mgr.finalize()
    endtime = time.time()
    results.append( {"dname": perllib,
                     "seconds": endtime-starttime,
                     "dbsize": os.stat(dbpath).st_size} )
    print "Results:"
    for res in results:
        print res["dname"]+':'
        seconds = res["seconds"]
        h,m,s = seconds/3600.0, seconds/60.0, seconds%60.0
        print "\tTime: %02dh%02dm%02.1fs" % (h,m,s)
        print "\tSize: %.2f KB" % (res["dbsize"]/1024.0)


def perf_setup_perl_completion(dbpath):
    """Setup for perl_completion().
    
    This will ensure that your CIDB has the Perl files that
    "perl_completion" requires.
    """
    import which
    import codeintel
    from codeintel.scheduler import PRIORITY_OPEN
    from codeintel import ScanRequest, CodeIntelError

    # Upgrade CIDB, if required, and initialize.
    # This should ensure that python.cix and perl.cix are loaded.
    mgr = codeintel.Manager(coreLanguages=["Python", "Perl"])
    state, details = mgr.getCIDBUpgradeInfo(dbpath)
    if state == codeintel.CIDB_UPGRADE_NECESSARY:
        mgr.upgradeCIDB(dbpath)
    elif state == codeintel.CIDB_UPGRADE_NOT_POSSIBLE:
        raise Error("CIDB is not upgradable: %r" % dbpath)
    mgr.initialize(dbpath)

    try:
        # Scan in a test Perl script.
        script = os.path.join(g_corpus_dir, "GET.pl") # Gisle's GET Perl script
        r = ScanRequest(script, "Perl", PRIORITY_OPEN)
        mgr.addRequest(r)
        # let scheduler finish its scans
        time.sleep(2)
        while mgr._scheduler and mgr._scheduler.getNumRequests():
            time.sleep(1)
    finally:
        mgr.finalize()
    
def perf_perl_completion(dbpath):
    """Get some Perl completions.
    
    To run this time test:
        ciperf -f perf.db -r setup_perl_completion
        ciperf -f perf.db -t perl_completion
    """
    import which
    import codeintel
    mgr = codeintel.Manager(coreLanguages=["Python", "Perl"])
    mgr.initialize(dbpath)
    try:
        # Gisle's GET Perl script (a good real-world example)
        # - lets "edit" on line 309, after the $ua var is set.
        script = os.path.join(g_corpus_dir, "GET.pl") # Gisle's GET Perl script
        line = 313
        content = open(script, 'r').read()
        
        if 0:
            #completions = mgr.getCallTips("Perl", script, line, "chmod", content=content)
            #completions = mgr.getCallTips("Perl", script, line, "LWP", content=content)
            #completions = mgr.getMembers("Perl", script, line, "LWP", content=content)
            #completions = mgr.getMembers("Perl", script, line, "LWP::UserAgent", content=content)
            #completions = mgr.getCallTips("Perl", script, line, "$ua.mirror", content=content)
            completions = mgr.getMembers("Perl", script, line, "$ua", content=content)
            #completions = mgr.getCallTips("Perl", script, line, "$ua", content=content)
        else:
            for i in range(5):
                # Do a few Perl completions in this file.
                completions = mgr.getCallTips("Perl", script, line, "chmod", content=content)
                completions = mgr.getCallTips("Perl", script, line, "LWP", content=content)
                completions = mgr.getMembers("Perl", script, line, "LWP", content=content)
                completions = mgr.getMembers("Perl", script, line, "LWP::UserAgent", content=content)
                completions = mgr.getCallTips("Perl", script, line, "$ua.mirror", content=content)
                completions = mgr.getMembers("Perl", script, line, "$ua", content=content)
                completions = mgr.getCallTips("Perl", script, line, "$ua", content=content)
    finally:
        mgr.finalize()
    
def perf_perl_scan(dbpath):
    """Time scanning and loading a "real world" Perl script into the CIDB.
    
    To run this time test:
        ciperf -f perf.db -t perl_scan
    """
    import which
    import codeintel
    import threading
    
    # Gisle's HTTP Perl scripts (good real-world examples) plus some
    # Perl 5.8 stdlib modules.
    scripts = glob.glob(os.path.join(g_corpus_dir, "*.pl"))
    scripts += glob.glob(os.path.join(g_corpus_dir, "*.pm"))
    if not scripts:
        raise Error("no scripts found for 'perf_perl_scan'")
    
    finished = threading.Event()

    class MyManager(codeintel.Manager):
        scanned = []
        def requestCompleted(self, request):
            self.scanned.append(request.path)
            if len(self.scanned) == len(scripts):
                finished.set()
    # Do NOT set Perl as a core language: don't want included re-scan to
    # confuse the results.
    mgr = MyManager()
    mgr.initialize(dbpath)
    try:
        # Force a re-scan of our scripts.
        for script in scripts:
            r = ScanRequest(script, "Perl", PRIORITY_OPEN, force=1)
            mgr.addRequest(r)

        finished.wait() # wait until done scanning
    finally:
        mgr.finalize()


def perf_setup_python_completion(dbpath):
    """Setup for python_completion().
    
    This will ensure that your CIDB has the Python files that
    "python_completion" requires.
    """
    import which
    import codeintel
    from codeintel.scheduler import PRIORITY_OPEN
    from codeintel import ScanRequest, CodeIntelError

    # Upgrade CIDB, if required, and initialize.
    # This should ensure that python.cix and python.cix are loaded.
    mgr = codeintel.Manager(coreLanguages=["Python", "Perl"])
    state, details = mgr.getCIDBUpgradeInfo(dbpath)
    if state == codeintel.CIDB_UPGRADE_NECESSARY:
        mgr.upgradeCIDB(dbpath)
    elif state == codeintel.CIDB_UPGRADE_NOT_POSSIBLE:
        raise Error("CIDB is not upgradable: %r" % dbpath)
    mgr.initialize(dbpath)

    try:
        # Scan in some test Python scripts.
        scripts = [
            os.path.join(g_corpus_dir, "cidb.py"),
            os.path.join(g_corpus_dir, "cb.py")
        ]
        for script in scripts:
            r = ScanRequest(script, "Python", PRIORITY_OPEN)
            mgr.addRequest(r)
        # let scheduler finish its scans
        time.sleep(2)
        while mgr._scheduler and mgr._scheduler.getNumRequests():
            time.sleep(1)
    finally:
        mgr.finalize()
    
def perf_python_completion(dbpath):
    """Get some Python completions.
    
    To run this time test:
        ciperf -f perf.db -r setup_python_completion
        ciperf -f perf.db -t python_completion
    """
    import which
    import codeintel

    mgr = codeintel.Manager(coreLanguages=["Python", "Perl"])
    mgr.initialize(dbpath)
    try:
        script = os.path.join(g_corpus_dir, "cidb.py")
        line = 227 # in the time_query() function
        content = open(script, 'r').read()
        
        # Do a few Python completions in this file.
        for i in range(5):
            completions = mgr.getCallTips("Python", script, line, "os.chmod",
                                          content=content)
            completions = mgr.getMembers("Python", script, line, "os",
                                         content=content)
            completions = mgr.getMembers("Python", script, line, "timer",
                                         content=content)
            completions = mgr.getMembers("Python", script, line, "t",
                                         content=content)
            completions = mgr.getCallTips("Python", script, line, "timeit.Timer",
                                          content=content)
            completions = mgr.getCallTips("Python", script, line, "t.timeit",
                                          content=content)
    
        # Do similar in a big file.
        script = os.path.join(g_corpus_dir, "cb.py")
        line = 566 # in a CBRootNode method
        content = open(script, 'r').read()

        for i in range(5):
            completions = mgr.getCallTips("Python", script, line, "os.chmod",
                                          content=content)
            completions = mgr.getMembers("Python", script, line, "os",
                                         content=content)
            completions = mgr.getMembers("Python", script, line, "self",
                                         content=content)
            completions = mgr.getCallTips("Python", script, line, "self.addModule",
                                          content=content)
            completions = mgr.getCallTips("Python", script, line, "self.generateRows",
                                          content=content)
    finally:
        mgr.finalize()

def perf_python_scan(dbpath):
    """Time scanning and loading a "real world" Python script into the CIDB.
    
    To run this time test:
        ciperf -f perf.db -t python_scan
    """
    import which
    import codeintel
    import threading
    
    # Some real-world examples
    scripts = glob.glob(os.path.join(g_corpus_dir, "*.py"))
    if not scripts:
        raise Error("no scripts found for 'perf_python_scan'")
    
    finished = threading.Event()

    class MyManager(codeintel.Manager):
        scanned = []
        def requestCompleted(self, request):
            self.scanned.append(request.path)
            if len(self.scanned) == len(scripts):
                finished.set()
    # Do NOT set Python as a core language: don't want included re-scan to
    # confuse the results.
    mgr = MyManager()
    mgr.initialize(dbpath)
    try:
        # Force a re-scan of our scripts.
        for script in scripts:
            r = ScanRequest(script, "Python", PRIORITY_OPEN, force=1)
            mgr.addRequest(r)

        finished.wait() # wait until done scanning
    finally:
        mgr.finalize()


def perf_tcl_scan(dbpath):
    """Time scanning and loading some "real world" Tcl scripts into the CIDB.
    
    To run this time test:
        ciperf -f perf.db -t tcl_scan
    """
    import which
    import codeintel
    import threading
    
    scripts = glob.glob(os.path.join(g_corpus_dir, "*.tcl"))
    if not scripts:
        raise Error("no scripts found for 'perf_tcl_scan'")
    
    finished = threading.Event()

    class MyManager(codeintel.Manager):
        scanned = []
        def requestCompleted(self, request):
            self.scanned.append(request.path)
            if len(self.scanned) == len(scripts):
                finished.set()
    mgr = MyManager()
    mgr.initialize(dbpath)
    try:
        # Force a re-scan of our scripts.
        for script in scripts:
            r = ScanRequest(script, "Tcl", PRIORITY_OPEN, force=1)
            mgr.addRequest(r)

        finished.wait() # wait until done scanning
    finally:
        mgr.finalize()



#---- internal support routines

def banner(text, ch='=', length=70):
    """Return a banner line centering the given text.
    
        "text" is the text to show in the banner. None can be given to have
            no text.
        "ch" (optional, default '=') is the banner line character (can
            also be a short string to repeat).
        "length" (optional, default 78) is the length of banner to make.

    Examples:
        >>> banner("Peggy Sue")
        '================================= Peggy Sue =================================='
        >>> banner("Peggy Sue", ch='-', length=50)
        '------------------- Peggy Sue --------------------'
        >>> banner("Pretty pretty pretty pretty Peggy Sue", length=40)
        'Pretty pretty pretty pretty Peggy Sue'
    """
    if text is None:
        return ch * length
    elif len(text) + 2 + len(ch)*2 > length:
        # Not enough space for even one line char (plus space) around text.
        return text
    else:
        remain = length - (len(text) + 2)
        prefix_len = remain / 2
        suffix_len = remain - prefix_len
        if len(ch) == 1:
            prefix = ch * prefix_len
            suffix = ch * suffix_len
        else:
            prefix = ch * (prefix_len/len(ch)) + ch[:prefix_len%len(ch)]
            suffix = ch * (suffix_len/len(ch)) + ch[:suffix_len%len(ch)]
        return prefix + ' ' + text + ' ' + suffix

def _get_komodo_user_data_dir(kover):
    if os.environ.has_key("KOMODO_USERDATADIR"):
        userdatadir = os.environ["KOMODO_USERDATADIR"]
    if sys.platform == "win32":
        from win32com.shell import shellcon, shell
        userdatadir = shell.SHGetFolderPath(0, shellcon.CSIDL_APPDATA, 0, 0)
        try:
            userdatadir = unicode(userdatadir)
        except:
            pass
        userdatadir = os.path.join(userdatadir, "ActiveState", "Komodo")
    else:
        userdatadir = os.path.expanduser("~/.komodo")
    
    return os.path.join(userdatadir, kover)
    

def find_komodo_cidb_path():
    log.debug("find_komodo_cidb_path()")

    # Find "Blackfile.py" in the current or a parent dir.
    landmark = "Blackfile.py"
    wd = os.getcwd()
    while wd:
        if os.path.isfile(os.path.join(wd, landmark)):
            break
        newwd = os.path.dirname(wd)
        if newwd == wd:
            wd = None
        else:
            wd = newwd
    else:
        raise Error("could not find base of a Komodo dev tree: no '%s' "
                    "in parent hierarchy" % landmark)

    # Determine the currently configured Komodo version.
    kodir = wd
    try:
        file, path, desc = imp.find_module("bkconfig", [kodir])
    except ImportError, ex:
        raise Error("could not determine Komodo version: %s" % ex)
    bkconfig = imp.load_module("bkconfig", file, path, desc)
    kover = '.'.join( bkconfig.version.split('.', 2)[:2] )
    
    return os.path.join(_get_komodo_user_data_dir(kover, True),
                        "codeintel.db")



def _list_perf_funcs(verbose=False):
    """Dump a table listing all performance functions in the module.

        "verbose" (optional, default false) is a boolean indicating if a
            verbose table should be dumped. The verbose version includes
            full docstring for targets and a tree of targets they call.

    A "performance function" is a function named perf_*.
    """
    prefix = "perf_"
    docmap = {}
    for perffunc, attr in sys.modules[__name__].__dict__.items():
        if perffunc.startswith(prefix):
            if attr.__doc__:
                doc = attr.__doc__
            else:
                doc = ''
            docmap[perffunc[len(prefix):]] = doc
    perffuncs = docmap.keys()
    
    print banner("Performance Functions")
    for i, perffunc in enumerate(perffuncs):
        doc = docmap[perffunc]
        if verbose:
            if i: print
            print perffunc
            if doc: print "    "+doc
        else:
            if doc:
                doc = doc.splitlines()[0]
            if len(doc) > 53:
                doc = doc[:50] + "..."
            print "  %-20s  %s" % (perffunc, doc)



#---- mainline

def time_perffunc(dbpath, perffunc, number=0, header=True):
    precision = 3
    repeat = 1
    if header:
        print banner("time perf_%s()" % perffunc)
        print "CIDB path:", dbpath
        print banner(None, ch='-')

    pysetup = "import ciperf"
    pystmt = "ciperf.perf_%s(%r)" % (perffunc, dbpath)
    t = timeit.Timer(stmt=pystmt, setup=pysetup)

    # Determine number so that 0.2 <= total time < 2.0
    if number == 0:
        for i in range(1, 10):
            number = 10**i
            try:
                x = t.timeit(number)
            except:
                t.print_exc()
                return 1
            if x >= 0.2:
                break

    # Do the timing.
    try:
        r = t.repeat(repeat, number)
    except:
        t.print_exc()
        return
    best = min(r)
    log.debug("raw times: %s", " ".join(["%.*g" % (precision, x) for x in r]))
    print "%d loops," % number,
    sec = best / number
    print "best of %d: %.*g sec per loop" % (repeat, precision, sec)


def main(argv):
    logging.basicConfig()

    # Parse options and args.
    try:
        opts, args = getopt.getopt(argv[1:], "Vvhf:Sltrcn:",
            ["version", "verbose", "help", "suite", "list", "timeit", "run",
             "coverage", "number="])
    except getopt.GetoptError, ex:
        log.error(str(ex))
        log.error("Try `ciperf --help'.")
        return 1
    dbpath = None
    number = 0
    mode = "timeit"
    for opt, optarg in opts:
        if opt in ("-h", "--help"):
            sys.stdout.write(__doc__)
            return
        elif opt in ("-V", "--version"):
            ver = '.'.join([str(part) for part in _version_])
            print "ciperf.py %s" % ver
            return
        elif opt in ("-v", "--verbose"):
            log.setLevel(logging.DEBUG)
        elif opt == "-f":
            dbpath = optarg
        elif opt in ("-d", "--dump-format"):
            format = optarg
        elif opt in ("-S", "--suite"):
            mode = "suite"
        elif opt in ("-l", "--list"):
            mode = "list"
        elif opt in ("-t", "--timeit"):
            mode = "timeit"
        elif opt in ("-r", "--run"):
            mode = "run"
        elif opt in ("-c", "--coverage"):
            mode = "coverage"
        elif opt in ("-n", "--number"):
            number = int(optarg)
    perffuncs = args

    try:
        if mode == "suite":
            dbpath = "ciperf.suite.db"
            if os.path.exists(dbpath):
                os.remove(dbpath)
            print banner("CodeIntel Performance Suite")
            print "dbpath:      %s" % dbpath
            print "machine:     %s (%s)" % (getHostname(), sys.platform)
            i,o,e = os.popen3("p4 changes -m1 ./...")
            output = o.read()
            i.close(); o.close(); retval = e.close()
            print "last change: %s" % output.split("'",1)[0].strip()
            print banner(None, ch='-')
            print "setup database..."
            perf_setup_perl_completion(dbpath)
            perf_setup_python_completion(dbpath)
            print "time 'perl_scan'..."
            time_perffunc(dbpath, "perl_scan", number=number, header=False)
            print "time 'perl_completion'..."
            time_perffunc(dbpath, "perl_completion", number=number, header=False)
            print "time 'python_scan'..."
            time_perffunc(dbpath, "python_scan", number=number, header=False)
            print "time 'python_completion'..."
            time_perffunc(dbpath, "python_completion", number=number, header=False)
            print banner(None, ch='-')
        if dbpath is None:
            dbpath = find_komodo_cidb_path()
        if mode == "suite":
            pass
        elif mode == "list":
            _list_perf_funcs(log.isEnabledFor(logging.DEBUG))
        elif mode == "timeit":
            for perffunc in perffuncs:
                time_perffunc(dbpath, perffunc, number=number)
        elif mode == "run":
            for perffunc in perffuncs:
                print banner("run perf_%s()" % perffunc)
                func = getattr(sys.modules[__name__], 'perf_'+perffunc)
                func(dbpath)
        elif mode == "coverage":
            import hotshot, hotshot.stats, test.pystone
            for perffunc in perffuncs:
                perfdump = "ciperf.%s.prof" % perffunc
                func = getattr(sys.modules[__name__], 'perf_'+perffunc)
                prof = hotshot.Profile(perfdump)
                res = prof.runcall(func, (dbpath))
                prof.close()
                stats = hotshot.stats.load(perfdump)
                stats.strip_dirs()
                stats.sort_stats('time', 'calls')
                #stats.sort_stats('cumulative', 'time', 'calls')
                stats.print_stats(20)
        else:
            raise Error("unexpected mode: '%r'" % mode)
    except Error, ex:
        log.error(str(ex))
        if log.isEnabledFor(logging.DEBUG):
            print
            import traceback
            traceback.print_exception(*sys.exc_info())
        return 1
    except KeyboardInterrupt:
        log.debug("user abort")

if __name__ == "__main__":
    sys.exit( main(sys.argv) )

