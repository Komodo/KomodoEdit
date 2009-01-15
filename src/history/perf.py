#!/usr/bin/env python

# Some performance testing for editorhistory.py.

from os.path import *
import os
import sys
import time
timestamp = (sys.platform == "win32" and time.clock or time.time)

from editorhistory import History, Location, Database

#---- internal support stuff

hotshotProfilers = {}

def hotshotit(func):
    def wrapper(*args, **kw):
        import hotshot
        global hotshotProfilers
        prof_name = func.func_name+".prof"
        profiler = hotshotProfilers.get(prof_name)
        if profiler is None:
            profiler = hotshot.Profile(prof_name)
            hotshotProfilers[prof_name] = profiler
        return profiler.runcall(func, *args, **kw)
    return wrapper


#---- performance tests

def perf_uris():
    """Test strategies for making lots of additions and lookups to the
    `history_uri` table quick.
    
    Cases:
    - How much does history_uri_uri index help?
      Answer: Not at all, because the "UNIQUE" constraint on `uri` results
      in an automatic index of the same kind.
    - Does caching uri id's in add_or_get_uri help?
      Yes, spectacularly.
    - TODO: What is the impact of NOCASE collation on `uri`?
    """
    import random
    
    db_path = join("tmp", "perf.sqlite")
    if False:
        if exists(db_path):
            os.remove(db_path)
        assert not exists(db_path)
    db = Database(db_path)
    
    # Our working-set files.
    ws = ["file:///home/trentm/%s.txt" % s for s in "abcdefghijklmnopqrstuvwxyz"]
    
    # Preload db with a lot of files.
    if False:
        print "Setting up db..."
        uris = ["file:///home/trentm/%05d.txt" % d for d in range(5000, 10000)]
        random.shuffle(uris)
        for uri in uris:
            db.uri_id_from_uri(uri)
        print "Done setting up db."
    
    rand = random.Random(42)
    randchoice = rand.choice
    M = 3
    times = []
    for j in range(M):
        N = 1000
        start = timestamp()
        for i in range(N):
            uri = randchoice(ws)
            id = db.uri_id_from_uri(uri)
        end = timestamp()
        times.append(end-start)
    for t in times:
        print "%d add/gets: %.3fs" % (N, t)
    

def setup_perf_load(db_path):
    if False:
        if exists(db_path):
            os.remove(db_path)
    if exists(db_path):
        return
    a = "file:///home/trentm/a.txt"
    db = Database(db_path)
    referer_id = None
    for i in range(1000):
        loc = Location(a, i, i)
        referer_id = db.add_loc(loc, referer_id)

def perf_load():
    """Play with getting a fast way to load the recent history from the db."""
    db_path = join("tmp", "perf_load.sqlite")
    setup_perf_load(db_path)
    
    hist = History(db_path)
    start = timestamp()
    hist.load()
    end = timestamp()
    print "time to load: %.3fs" % (end-start)



#---- mainline

def main(argv):
    #perf_uris()
    perf_load()

if __name__ == "__main__":
    retval = main(sys.argv)
    sys.exit(retval)