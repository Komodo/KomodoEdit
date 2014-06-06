import time
import operator
from collections import defaultdict

_g_reporter = None

class BenchReporter(object):
    def __init__(self, time0=None, name=""):
        self.time0 = time0 if time0 is not None else time.time()
        self.name = name
        self._depth = 0
        self._starts = defaultdict(list)
        # Entries are a list of (time_started, duration, depth) tuples.
        self._entries = defaultdict(list)
        self._missing_starts = defaultdict(list)
        self._events = []
        self._cumulative = defaultdict(lambda: [0, 0])
        # Always report at shutdown time.
        import atexit
        atexit.register(self.display)

    def startTiming(self, name):
        self._starts[name].append((time.time(), self._depth))
        self._depth += 1

    def endTiming(self, name):
        """End of a timing"""
        now = time.time()
        start = self._starts[name]
        if not start:
            self._missing_starts[name].append(now)
        else:
            start_time, depth = start.pop()
            duration = now - start_time
            self._entries[name].append((now - duration, duration, depth))
        self._depth -= 1

    def addTiming(self, name, duration):
        self._entries[name].append((time.time() - duration, duration, self._depth))

    def addEvent(self, name):
        self._events.append((name, time.time()))

    def accumulate(self, name, duration):
        """Keep a record of the number of calls and how long it takes."""
        hit = self._cumulative[name]
        hit[0] += 1
        hit[1] += duration

    def addEventAtTime(self, name, t):
        self._events.append((name, t))

    def displayEvents(self, limit=None):
        if self._events:
            print "Events:"
            for name, t in sorted(self._events, key=operator.itemgetter(1)):
                print "  %-66s at %0.5f" % (name, t - self.time0)

    def displayAccumulations(self, limit=None):
        if self._cumulative:
            print "Cumulative:"
            for name, hit in sorted(self._cumulative.items(), key=lambda x: x[1][1]):
                print "  %-46s %d calls - %0.5f" % (name, hit[0], hit[1])

    def display(self, order="by-time", limit=None):
        """Display the reports.
        
        The `order` argument can be used to order the results in a particular
        manner. Supported variations are:
            "by-time": reports are displayed in chronological order
            "by-spent": reports are displayed in order of the time spent

        The `limit` argument is used to limit the number of reports displayed.
        """
        if order == "by-time":
            print "Timings:"
            entries_by_time = defaultdict(list)
            for name, timings in self._entries.items():
                for start, spent, depth in timings:
                    entries_by_time[start].append((name, spent, depth))

            for start in sorted(entries_by_time):
                entries = entries_by_time[start]
                for name, spent, depth in entries:
                    print "  %-58s %0.5f at %0.5f" % (depth * " " + name, spent, start - self.time0)
        else:
            print "Unknown sort order %r" % (order, )

        self.displayEvents()
        self.displayAccumulations()

def initialise(t=None):
    global _g_reporter
    if _g_reporter is None:
        _g_reporter = BenchReporter(t)
    return True

class bench(object):
    """Decorator to benchmark a function call, records the time it takes to execute."""
    def __init__(self, name=None):
        self.name = name
    def __call__(self, fn):
        if self.name is None:
            self.name = fn.__name__
        this = self
        def fn_wrap(*args, **kwargs):
            if _g_reporter is None:
                initialise()
            _g_reporter.startTiming(this.name)
            try:
                result = fn(*args, **kwargs)
            finally:
                _g_reporter.endTiming(this.name)
            return result
        return fn_wrap

class bench_accumulate(object):
    """Records the number of calls and total time it took to execute."""
    def __init__(self, name=None):
        self.name = name
    def __call__(self, fn):
        if self.name is None:
            self.name = fn.__name__
        this = self
        def fn_wrap(*args, **kwargs):
            if _g_reporter is None:
                initialise()
            t = time.time()
            try:
                result = fn(*args, **kwargs)
            finally:
                _g_reporter.accumulate(this.name, time.time() - t)
            return result
        return fn_wrap

def startTiming(name):
    if _g_reporter is None:
        initialise()
    _g_reporter.startTiming(name)

def endTiming(name):
    if _g_reporter is None:
        initialise()
    _g_reporter.endTiming(name)

def addTiming(name, duration):
    if _g_reporter is None:
        initialise()
    _g_reporter.addTiming(name, duration)

def addEvent(name):
    if _g_reporter is None:
        initialise()
    _g_reporter.addEvent(name)

def accumulate(name, duration):
    if _g_reporter is None:
        initialise()
    _g_reporter.accumulate(name)

def addEventAtTime(name, t):
    if _g_reporter is None:
        initialise()
    _g_reporter.addEventAtTime(name, t)

def display():
    assert _g_reporter is not None
    _g_reporter.display()

import inspect
def klass(cls, ismethod=inspect.ismethod):
    """Wrap all class functions with benchmarked versions"""
    clsname = cls.__name__
    for name in dir(cls):
        if name.startswith("_") and name != "__init__":
            continue
        item = getattr(cls, name)
        if ismethod(item):
            wrappeditem = bench("%s.%s" % (clsname, name))(item)
            setattr(cls, name, wrappeditem)
