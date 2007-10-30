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
    ptimeline - parse a Mozilla timeline log

    Usage:
        ptimeline.py [<options>...] [<statistic>...]

    Options:
        -v, --verbose   Verbose output
        -q, --quiet     Quieten output
        -h, --help      Print this text and exit.
        -V, --version   Print the current version and exit.

        -f <filename>   Log file to parse. Defaults to
                        NS_TIMELINE_LOG_FILE environment variable.
        -l <pattern>    Pattern of last record to parse.
        --records       Dump all records. (Wad '-d'. Deemed useless and
                        temporarily removed.)

        -c <pattern>    Dump info for the given counter pattern. Can be
                        repeated.
        --counters      Dump all "interesting" counters (as determined
                        by the hardcoded list 'interesting_counter_defs').
        --log           Dump contributing log lines for processed
                        counters.

        -n <num>        Number of top statistic records to print. See
                        <statistic> below.  Defaults to 30.

    <statistic> is the name of a statistic to print. The top so many (as
    determined by '-n') contributing records are printing. Available
    statistics are:
        event_total         XXX 'splain
        gap                 XXX 'splain
        event_gap           XXX 'splain

    XXX 'splain

    See howto-timeline.txt in Komodo's internal-docs tree for
    information on generating timeline log for your Komodo build.

    Examples:
        ptimeline -c os.stat        # dump number of lines matching 'os.stat'
        ptimeline -c os.stat --log  # ...also dump the contributing lines

        >>> import ptimeline
        >>> records = ptimeline.parse("timeline.log")
        >>> counter = ptimeline.count("os.stat", records)
"""
# TODO:
#   - Add a module interface.
#
# Dev Notes:
#   - This was adapted from parse_timeline.py with the goal of (1) my
#     understanding it (TrentM), (2) making it more user friendly, (3)
#     more robust and (4) giving it a module interface for use by
#     perf_timeline.py.
#   - Currently finds the top n "totals" (ie, top times reported by)
#     standard "timer total: 0.00000" lines, and the top 10 "gaps" (ie,
#     a gap between 2 items, not reported by the second line having a
#     "total: 0.00000" entry.
#     NOTE: gaps are a little suspect.
#

import os
import sys
import re
import getopt
import pprint
import types

try:
    import logging
except ImportError, ex:
    sys.stderr.write("""\
This script now requires Python's Logging module. It will be standard with
Python 2.3. If you don't have it you can get it here:
   http://www.red-dove.com/python_logging.html#download 
""")


#---- exceptions

class ParseError(Exception):
    pass


#---- globals

_version_ = (0, 2, 0)
log = logging.getLogger("ptimeline")

# "Interesting" counters. These are the counters that will be dumped by 
interesting_counter_defs = [
    # {"regex": <regex>,
    #  "name": <name>}  # 'name' is optional
    {"name": "PyXPCOM components created (total)",
     "regex": re.compile("constructing component")},
    {"name": "PyXPCOM components created (koPrefs)",
     "regex": re.compile("constructing component:koPrefs")},
    {"name": "PyXPCOM incoming calls (total)",
     "regex": re.compile("PyXPCOM: component")},
    {"name": "PyXPCOM incoming calls (koPrefs)",
     "regex": re.compile("PyXPCOM: component:koPrefs")},
    {"name": "PyXPCOM incoming calls (koFile)",
     "regex": re.compile("PyXPCOM: component:koFile")},
    {"name": "PR_LoadLibrary calls",
     "regex": re.compile("PR_LoadLibrary")},
    {"name": "IO Service channels created",
     "regex": re.compile("nsIOService::NewChannelFromURI")},
    {"name": "Python imports",
     "regex": re.compile("Python module import")},
    {"name": "Python os.stat calls",
     "regex": re.compile("os.stat")},
    {"name": "Python os.listdir calls",
     "regex": re.compile("os.listdir")},
]

# Regexes to parse timeline log lines. For example:
#   00000.062 (00254898):   PR_LoadLibrary total: 0.015 (D:\moz...mponents.dll)
#   00000.046 (00254898):  startupNotifier...
re_timeline = re.compile("(\d+\.\d+) \(([0-9a-zA-Z]+)\): (\W*)(\w.*)$")
# This parses the subpart of "total lines", of which the first sample
# line above is an example:
#   00000.062 (00254898):   PR_LoadLibrary total: 0.015 (D:\moz...mponents.dll)
#                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
re_total = re.compile("(.*)total: (\d+\.\d+)(.*)")



#---- internal support stuff

# Some "transformers" - a set of (regex, functions) that
# can translate the text to something more meaningful.
msg_map = {}
notify_map = {}
flags_map = {}

# Convert raw SciMoz WndProc messages into symbolic names.
def scimoz_transform(match):
    import win32con, win32api
    if not msg_map:
        def _load_message_constants(module, prefix, map):
            for name, val in module.__dict__.items():
                if name.startswith(prefix):
                    if map.has_key(val):
                        log.debug("overwriting %s with %s", map[val], name)
                    map[val] = name
        def _load_flags_constants(module, prefix):
            for name, val in module.__dict__.items():
                if name.startswith(prefix):
                    this_flags = flags_map.setdefault(prefix, [])
                    this_flags.append((val, name))

        # WM_ map
        _load_message_constants(win32con, "WM_", msg_map)

        # WM_NOTIFY messages
        # SN_* messages
        from pywin.scintilla import scintillacon
        _load_message_constants(scintillacon, "SCN_", notify_map)
        _load_message_constants(win32con, "WN_", notify_map)
        _load_flags_constants(win32con, "SWP_")
        _load_flags_constants(win32con, "SIZE_")

    def _convert_flags(prefix, value):
        f = []
        this_flags = flags_map[prefix]
        for flag, name in this_flags:
            if value & flag == flag:
                f.append(name)
        return "|".join(f)

    # Process the regex, swapping constants for names.
    d = match.groupdict()
    msg = int(match.group("msg"))
    msg_name = msg_map.get(msg, hex(msg))
    wparam = int(d["wparam"])
    lparam = int(d["lparam"])
    
    d["msg_name"] = msg_name
    info = "%(leading)s <%(name)s> hwnd=0x%(hwnd)s msg=%(msg_name)s(%(wparam)s %(lparam)s)%(trailing)s" % d
    
    extra_type = d["extra_type"]
    extra_details = d["extra_details"]
    if extra_type == "notify":
        n_wndfrom, n_idfrom, n_code = extra_details.split(",")
        n_code = int(n_code)
        code_name = notify_map.get(n_code, str(n_code))
        info += " (0x%s, %s, %s)" % (n_wndfrom, n_idfrom, code_name)
    elif extra_type == "windowpos":
        hwnd, hwndAfter, x, y, cx, cy, flags = extra_details.split(",")
        flags = int(flags)
        flag_desc = _convert_flags("SWP_", flags)
        info += " Pos (%s,%s), Size (%s,%s), Flags=0x%x (%s)"\
                % (x, y, cx, cy, flags, flag_desc)
    if msg==win32con.WM_MOVE:
        info += " Move %d,%d" % (win32api.LOWORD(lparam),
                                 win32api.HIWORD(lparam))
    if msg==win32con.WM_SIZE:
        flag_desc = _convert_flags("SIZE_", wparam)
        info += " Size flags=0x%x (%s), Width=%d, Height=%d"\
                % (wparam, flag_desc, win32api.LOWORD(lparam),
                   win32api.HIWORD(lparam))

    return info

scimoz_regex = re.compile(
    # SciMoz::WndProc <name> 52069e 273 50332759 2623104
    # SciMoz::WndProc <name> 52069e 78 1111 1225032 (something: ...)
    # |leading| <|name|> |hwnd| |msg| |wparam| |lparam| (|extra_type|:|extra_details|)
    r"(?P<leading>[^:]*::.*Proc) (\<(?P<name>.*)\> )?(?P<hwnd>[0-9a-fA-f]+) (?P<msg>-?\d+) (?P<wparam>-?\d+) (?P<lparam>-?\d+)"
        # The optional extra portion
        "( \((?P<extra_type>[^:]*):(?P<extra_details>.*)\))?"
        # The tail
        "(?P<trailing>.*)$"
    )

# The list transformers
transformers =  (
    (scimoz_regex, scimoz_transform),
)

def transform_desc(desc):
    for regex, fn in transformers:
        m = regex.match(desc)
        if m is not None:
            return fn(m)
    return desc


def count(regex, records=None):
    """Return the number of occurences of the given pattern.
    
    "regex" is a regular expression to match against timeline log file
        record descriptions. If a plain string is passed in, it is
        compiled to a regex.
    "records" is the return value of parse(). If not specified it
        attempts to automatically determine this using the
        NS_TIMELINE_LOG_FILE variable.

    Returns a dictionary of the form:
        {"regex": <given regex>,
         "count": <number of occurences>,
         "records": <contributing records>}
    """
    if not records:
        filename = os.environ.get("NS_TIMELINE_LOG_FILE", None)
        if filename:
            records = parse(filename)
        else:
            raise ParseError("'records' not specified and "
                             "NS_TIMELINE_LOG_FILE not set")
    if type(regex) in types.StringTypes:
        regex = re.compile(regex)

    counter_def = {"regex": regex}
    counters = create_counters([counter_def], records)
    counter = {"count": 0, "records": []}
    counter.update(counter_def)
    for thread_id, thread_counters in counters.items():
        c = thread_counters.get(regex.pattern)
        if c:
            counter["count"] += c["count"]
            counter["records"] += c["records"]
    return counter


def create_counters(counter_defs, records_by_thread):
    """Count the number of occurrences of each counter pattern.

    "counter_defs" is a list of counter definitions, each of which is a
        dictionary of the form:
            {"regex": <regex instance>,
             "name": <counter name>} # "name" is optional
    "records_by_thread" is a dictionary of parsed Record instances,
        keyed by thread id.

    Returns a dictionary of the form:
        {<thread id>:
            <counter id>: {"regex": <regex>,
                           "name": <counter name>, # if in counter_def
                           "count": <n>,
                           "records": [<r1>, <r2>, ...]},
            ...
         ...
        }
    """
    counters_by_thread = {}

    for thread_id, records in records_by_thread.items():
        # Initialize counter.
        thread_counters = counters_by_thread[thread_id] = {}
        for counter_def in counter_defs:
            counter_id = counter_def["regex"].pattern
            thread_counters[counter_id] = {"count": 0, "records": []}
            thread_counters[counter_id].update(counter_def)

        for record in records:
            desc = record.desc.strip()
            for counter_def in counter_defs:
                regex = counter_def["regex"]
                id = regex.pattern # counter id
                if regex.match(desc):
                    thread_counters[id]["count"] += 1
                    thread_counters[id]["records"].append(record)

    return counters_by_thread


class Record:
    def __init__(self, match):
        event_time, thread_id, leading_ws, desc = match.groups()
        leading_ws = leading_ws or ''
        self.desc = (leading_ws + transform_desc(desc)).rstrip()
        total_match = re_total.match(desc)
        self.event_total = None
        self.thread_id = thread_id
        self.event_time = float(event_time)
        if total_match:
            self.counter_name = total_match.group(1).strip()
            self.counter_total = float(total_match.group(2))
        else:
            self.counter_name = self.counter_total = None

    def __str__(self):
        ret = "%08.3f: %s" % (self.event_time, self.desc)
#        ret += " (gaps=%g/%g" % (self.total_gap, self.gap)
        if self.event_total is not None:
            ret += " (this event=%g)" % self.event_total
        return ret

def calc_times(records_by_thread):
    """Update 'records_by_thread' in-place with calculated event times."""
    for thread_id, records in records_by_thread.items():
        last_time = 0.0
        counter_times = {}
        for record in records:
            counter = record.counter_name
            if counter is not None:
                last_counter_time = counter_times.get(counter, 0.0)
                record.event_total = record.counter_total - last_counter_time
                counter_times[counter] = record.counter_total
            # And update the gap time.
            record.gap = record.event_time - last_time
            if record.gap < -0.1:
                log.error("invalid negative gap: %s (record=%s)",
                          record.gap, record)
            last_time = record.event_time

def cmp_totals(rec1, rec2):
    return cmp(rec1.event_total, rec2.event_total)

def _print_top(records_by_thread, attr, n=20):
    # Print top records for the given "attr"/statistic.
    print "="*70
    print "Top records for '%s' statistic:" % attr
    print "-"*70
    records = []
    for rs in records_by_thread.values():
        records += rs
    comparer = lambda r1, r2, attr=attr: cmp(getattr(r1, attr), getattr(r2, attr))
    records.sort(comparer)
    records.reverse()
    tot = 0.0
    for t in records[:n]:
        print t
        tot += getattr(t, attr)
    print "-"*70
    print "Top", n, "records have total", attr, "of", tot
    print "="*70


def parse(filename=None, last_record=None):
    """Parse the given Mozilla timeline log file.

    "filename" is the path the timeline log file. If not specified it
        attempt to determine it from NS_TIMELINE_LOG_FILE.
    "last_record" (optional) is the name of a record at which to stop
        processing.

    This returns a dictionary of records keyed on their thread_id.
    """
    if filename is None:
        try:
            filename = os.environ["NS_TIMELINE_LOG_FILE"]
        except KeyError, ex:
            raise ParseError("Could not determine timeline log file name: "
                             "'filename' not specified and "
                             "NS_TIMELINE_LOG_FILE not defined.")
    if not os.path.exists(filename):
        raise ParseError("The given timeline log file does not exist: '%s'"
                         % filename)
    log.debug("parsing '%s'", filename)

    # Parse records out of the log file.
    fin = open(filename, 'r')
    try:
        records = []
        for line in fin.readlines():
            match = re_timeline.match(line)
            if match is None:
                # Little bit of debugging - flag suspect lines
                if line[0].isdigit():
                    log.warn("regex may have failed on line: %r", line)
                continue
            r = Record(match)
            records.append(r)
            if last_record is not None and r.desc.strip() == last_record:
                break
    finally:
        fin.close()

    records_by_thread = { # list of records for each thread
        # <thread id 1>: [<record 1>, <record 2>, ...]
    }
    for r in records:
        if r.thread_id not in records_by_thread:
            records_by_thread[r.thread_id] = []
        records_by_thread[r.thread_id].append(r)

    log.debug("parsed %d records from %s threads",
              len(records), len(records_by_thread))
    return records_by_thread


def _dump_counters(counter_defs, records_by_thread, dump_log=0):
    counters = create_counters(counter_defs, records_by_thread)
    records = []
    for thread_id, thread_counters in counters.items():
        print "Counter values for thread %s:" % thread_id
        values = thread_counters.values()
        values.sort(lambda a,b: cmp(a.get("name", a["regex"].pattern),
                                    b.get("name", b["regex"].pattern)))

        for counter in values:
            if counter["count"]:
                prettyname = counter.get("name", counter["regex"].pattern)
                print " %s %s" % (prettyname, counter["count"])
                if dump_log:
                    records += counter["records"]

    if records:
        print "Log:"
        for record in records:
            print record



#---- mainline

def main(argv):
    logging.basicConfig()
    log.setLevel(logging.INFO)

    # parse options
    try:
        opts, statistics = getopt.getopt(argv[1:], "vqhVn:f:l:c:",
            ["verbose", "quiet", "help", "version", "counters", "log"])
    except getopt.error, ex:
        log.error(str(ex))
        return 1
    filename = None
    last_record = None
    num_recs = 30
    dump_interesting_counters = 0
    dump_log = 0
    counter_defs = []
    for opt, optarg in opts:
        if opt in ("-h", "--help"):
            print __doc__
            return 0
        elif opt in ("-v", "--verbose"):
            log.setLevel(logging.DEBUG)
        elif opt in ("-q", "--quiet"):
            log.setLevel(logging.WARN)
        elif opt in ("-V", "--version"):
            ver = '.'.join([str(i) for i in _version_])
            print "ptimeline %s" % ver
            return 0
        elif opt == "-n":
            try:
                num_recs = int(optarg)
            except ValueError, ex:
                log.error("invalid value for -n: %s\n", ex)
                return 1
        elif opt == "-f":
            filename = optarg
        elif opt == "-l":
            last_record = optarg
        elif opt == "--counters":
            dump_interesting_counters = 1
        elif opt == "--log":
            dump_log = 1
        elif opt == "-c":
            counter_def = {"regex": re.compile(optarg)}
            counter_defs.append(counter_def)

    if filename is None:
        try:
            filename = os.environ["NS_TIMELINE_LOG_FILE"]
        except KeyError, ex:
            log.error("No timeline log to parse. Use the '-f' option or "
                      "set NS_TIMELINE_LOG_FILE.")
            return 1

    try:
        records_by_thread = parse(filename, last_record)
        calc_times(records_by_thread)
        if dump_interesting_counters:
            _dump_counters(interesting_counter_defs, records_by_thread,
                           dump_log)
        if counter_defs:
            _dump_counters(counter_defs, records_by_thread, dump_log)
        for statistic in statistics:
            _print_top(records_by_thread, statistic, num_recs)
    except ParseError, ex:
        log.error(str(ex))
        if log.isEnabledFor(logging.DEBUG):
            print
            import traceback
            traceback.print_exception(*sys.exc_info())
        return 1
    

if __name__ == '__main__':
    sys.exit( main(sys.argv) )

