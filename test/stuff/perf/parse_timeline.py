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

# parse_timeline - parse a Mozilla timeline log, and get some interesting
# stats

# Currently finds the top n "totals" (ie, top times reported by)
# standard "timer total: 0.00000" lines, and the top 10 "gaps"
# (ie, a gap between 2 items, not reported by the second line having
# a "total: 0.00000" entry.
# NOTE: gaps are a little suspect.
import os, sys, re


# 00000.953 (00275228):  InitializeProfileService...
# 00000.953 (00275228):   PR_LoadLibrary total: 0.031 (E:\src\as\Apps\Mozilla-devel\build\moz-20030313-ko25-debug\mozilla\dist\bin\components\profile.dll)
# 00001.015 (00275228):  ...InitializeProfileService
# first regex splits into:
# {event_time} (thread_id): {indent}{leave}{tail}
# then 'tail' split into:
# {counter}{enter} total: {counter_time} ({comment})

re_timeline = re.compile("(?P<event_time>\d+\.\d+) \((?P<thread_id>[0-9a-zA-Z]+)\): (?P<indent> *)(?P<leave>\.\.\.)?(?P<tail>.*)$")
re_total = re.compile("(.*)total: (\d+\.\d+)( \((.*)\))?$")

verbose = 0

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
                    if verbose and map.has_key(val):
                        print "Overwriting %s with %s" % (map[val], name)
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
        info += " Pos (%s,%s), Size (%s,%s), Flags=0x%x (%s)" % (x, y, cx, cy, flags, flag_desc)
    if msg==win32con.WM_MOVE:
        info += " Move %d,%d" % (win32api.LOWORD(lparam), win32api.HIWORD(lparam))
    if msg==win32con.WM_SIZE:
        flag_desc = _convert_flags("SIZE_", wparam)
        info += " Size flags=0x%x (%s), Width=%d, Height=%d" % (wparam, flag_desc, win32api.LOWORD(lparam), win32api.HIWORD(lparam))
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

# Keep track of individual counters.
def create_counters(counter_defs, records):
    counters = {} # indexed by thread id giving another dict of counters
    for record in records:
        thread_counters = counters.setdefault(record.thread_id, {})
        text = record.detail.strip()
        for name, regex in counter_defs:
            if regex.match(text):
                thread_counters[name] = thread_counters.get(name,0) + 1
    return counters

class Record:
    def __init__(self, match):
        d = match.groupdict()
        self.event_time = float(d['event_time'])
        self.thread_id = d['thread_id']
        self.indent_level = len(d['indent'])
        self.is_leave = d['leave'] is not None
        # Now pull tail off.
        total_match = re_total.match(d['tail'])
        if total_match:
            self.counter_name = total_match.group(1).strip()
            self.counter_total = float(total_match.group(2))
            self.counter_comment = total_match.group(4)
            detail = self.counter_name
            self.is_enter = False
        else:
            self.counter_name = self.counter_total = self.counter_comment = None
            detail = d['tail']
            if detail.endswith("..."):
                detail = detail[:-3]
                self.is_enter = True
            else:
                self.is_enter = False
        self.detail = transform_desc(detail)
        self.event_total = None

    def IsMatchingEnterLeave(self, other):
        return abs(self.event_time - other.event_time) < 0.001 and \
           self.indent_level == other.indent_level and \
           self.counter_name == other.counter_name and \
           self.counter_comment == other.counter_comment and \
           self.detail == other.detail and \
           ( (self.is_enter and other.is_leave) or (self.is_leave and other.is_enter))

    def Format(self, show_collapsed = False):
        enter_str = leave_str = total_str = comment_str = ""
        if show_collapsed:
            assert self.is_enter or self.is_leave
            enter_str = "..."
            leave_str = "..."
        else:
            if self.is_enter: enter_str = "..."
            if self.is_leave: leave_str = "..."
        if self.counter_total:
            total_str = " total: %7.3f" % self.counter_total
        if self.counter_comment:
            comment_str = " (" + self.counter_comment + ")"
        indent_str = " " * self.indent_level
        ret = "%011.6f: %s%s%s%s%s%s" % (self.event_time, indent_str, leave_str, self.detail, total_str, comment_str, enter_str)
        if self.event_total is not None:
            ret += " (this event=%g)" % self.event_total
        return ret
        
    def __str__(self):
        return self.Format()

def parse(file, last_record):
    records = []
    for line in file.readlines():
        match = re_timeline.match(line)
        if match is None:
            # Little bit of debugging - flag suspect lines
            if line[0].isdigit():
                print >> sys.stderr, "WARNING: regex may have failed on line:"
                print >> sys.stderr, line
            continue
        r = Record(match)
        records.append(r)
        if last_record is not None and r.detail.strip()==last_record:
            break
    return records

def calc_times(thread_records):
    for thread_id, records in thread_records.items():
        last_time = 0
        counter_times = {}
        for record in records:
            counter = record.counter_name
            if counter is not None:
                last_counter_time = counter_times.get(counter,0.0)
                record.event_total = record.counter_total - last_counter_time
                counter_times[counter] = record.counter_total
            # And update the gap time.
            record.gap = record.event_time - last_time
            if verbose and record.gap < -0.1:
                print >> sys.stderr, "Invalid negative gap", self.gap
                print >> sys.stderr, self
            last_time = record.event_time

def cmp_totals(rec1, rec2):
    return cmp(rec1.event_total, rec2.event_total)

def print_top(records, attr, n=20):
    r = records[:]
    comparer = lambda r1, r2, attr=attr: cmp(getattr(r1, attr), getattr(r2, attr))
    r.sort(comparer)
    r.reverse()
    tot = 0.0
    for t in r[:n]:
        print t
        _t = getattr(t, attr)
        if _t:
            tot += _t
    print "Top", n, "records have total", attr, "of", tot

def split_thread_records(records):
    threads = {}
    for r in records:
        thread_records = threads.setdefault(r.thread_id, [])
        thread_records.append(r)
    return threads

def dump_records(thread_records, collapse_enter_leaves = True):
    if collapse_enter_leaves:
        print "Dumping all records (collapsing consecutive enter/leave pairs)"
    else:
        print "Dumping all records"
    for thread_id, records in thread_records.items():
        print "Dumping records from thread", thread_id
        i = 0
        while i < len(records):
            r = records[i]
            if collapse_enter_leaves and i != len(records)-1:
                if r.IsMatchingEnterLeave(records[i+1]):
                    print r.Format(show_collapsed = True)
                    i += 2
                    continue
            print r.Format()
            i+=1

def usage(msg=None):
    if msg:
        print msg
        print
    print "%s [options] stat_name ... - parse a Mozilla timeline log file" % os.path.basename(sys.argv[0])
    print "Options:"
    print "-v : Verbose"
    print "-n num : Number of records to print"
    print "-f filename: Name of file to process."
    print "-d: Dump all records"
    print "-l desc: Description of last record to process"
    print "-c: Dump all counters (the counter list is hardcoded)"
    print "--dont-collapse: Don't collapse identical 'enter/leave' timeline pairs"
    print "stat_name is the name of a statistic to print - eg, 'event_total', 'gap'"
    print
    print "If -f is not specified and NS_TIMELINE_LOG_FILE exists in the"
    print "environment, it will be used"
    print
    print "The following attributes can be used: event_total, gap, event_gap"
    sys.exit(1)

def main():
    collapse_enter_leaves = True
    filename = None
    last_record = None
    num_recs = 30
    dump = dump_counters = 0
    import getopt
    try:
        opts, args = getopt.getopt(sys.argv[1:], "vn:f:dl:c", ["dont-collapse"])
    except getopt.error, msg:
        usage(msg)
    for opt, val in opts:
        if opt == "-v":
            global verbose
            verbose = 1
        if opt == "-n":
            num_recs = int(val)
        elif opt == "-f":
            filename = val
        elif opt == "-d":
            dump = 1
        elif opt == "-l":
            last_record = val
        elif opt == "-c":
            dump_counters = 1
        elif opt == "--dont-collapse":
            collapse_enter_leaves = False

    if not filename:
        filename = os.getenv("NS_TIMELINE_LOG_FILE")
    if not filename or not os.path.exists(filename):
        usage("You must specify a filename\n(NS_TIMELINE_LOG_FILE doesn't exist or is invalid)")
    f = open(filename)
    r = parse(f, last_record)
    thread_records = split_thread_records(r)
    calc_times(thread_records)
    print filename, "contains", len(r), "records from", len(thread_records), "threads."
    if dump:
        dump_records(thread_records, collapse_enter_leaves)
        print

    if dump_counters:
        counter_defs = (
            ("PyXPCOM components created (total)", re.compile("constructing component")),
            ("PyXPCOM components created (koPrefs)", re.compile("constructing component:koPrefs")),
            ("PyXPCOM incoming calls (total)", re.compile("PyXPCOM: component")),
            ("PyXPCOM incoming calls (koPrefs)", re.compile("PyXPCOM: component:koPrefs")),
            ("PyXPCOM incoming calls (koFile)", re.compile("PyXPCOM: component:koFile")),
            ("PR_LoadLibrary calls", re.compile("PR_LoadLibrary")),
            ("IO Service channels created", re.compile("nsIOService::NewChannelFromURI")),
            ("Python imports", re.compile("Python module import")),
            ("Python os.stat calls", re.compile("os.stat")),
            ("Python os.listdir calls", re.compile("os.listdir")),
        )
        counters = create_counters(counter_defs, r)
        for thread_id, thread_counters in counters.items():
            print "Counter values for thread %s:" % thread_id
            keys = thread_counters.keys()
            keys.sort()
            for name in keys:
                print "", name, thread_counters[name]
        print
    for attr in args:
        print "Top records:", attr
        print_top(r, attr, num_recs)
        print

if __name__=='__main__':
    main()
