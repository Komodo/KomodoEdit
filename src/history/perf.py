#!/usr/bin/env python

# Some performance testing for editorhistory.py.

from os.path import *
import os
import sys
import time
import random
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
    
class HistoryVisitor:
    def _visit_weekend(self):
        roll = random.choice(range(10))
        if roll < 7:
            # Most weekends we do nothing
            return
        elif roll == 9:
            # This one's busy
            self._visit_weekday()
            return
        # Treat it like a half day
        self.num_to_add = random.randint(2, 5)
        self.num_to_drop = random.randint(0, 4)
        self.num_visits = int(random.gauss(150, 40))
        self.num_hours = 4
        self._visit_()
        
    def _visit_weekday(self):
        self.num_to_add = random.randint(5, 10)
        self.num_to_drop = random.randint(3, 8)
        self.num_visits = int(random.gauss(300, 30))
        self.num_hours = 8
        self._visit_()
        
    def _visit_(self):
        # Adjust the list of URIs
        self.uri_nums += range(self._next_uri, self._next_uri + self.num_to_add)
        self._next_uri += self.num_to_add
        for i in range(self.num_to_drop):
            idx = random.randint(0, len(self.uri_nums) - 1)
            del self.uri_nums[idx]
        time_interval = (self.num_hours / 24.0) / self.num_visits
        
        for i in range(self.num_visits):
            # old uri or a new one?
            if random.random() < 0.25:
                uri_id = self._most_recent_uri
            else:
                self._most_recent_uri = uri_id = random.choice(self.uri_nums)
            
            # self.time is negative, like -35 for 35 days ago
            # No need to randomize the intervals.
            this_time = self.curr_time + self.time + i * time_interval
            
            self.cu.execute("""
                INSERT INTO history_visit(referer_id, uri_id, line, col, view_type, marker_handle,
                    window_num, tabbed_view_id, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, 
                (0, uri_id, i, 0, "editor", -1, 0, 1, this_time))
            # print "uri:%d, time:%f" % (uri_id, this_time)
    
    second_interval = 1.0/86400.0
    def cull_period(self, start_time, end_time):
        #print "culling: %r - %r" % (start_time, end_time)
        #return
        self.cu.execute("""SELECT h1.uri_id, h1.timestamp from history_visit h1
                    where h1.timestamp = (select max(h2.timestamp)
                    from history_visit h2 where h1.uri_id = h2.uri_id
                    and h2.timestamp between ? and ?)""",
                    (start_time, end_time))
        rows = self.cu.fetchall()
        for uri_id, max_timestamp in rows:
            max_timestamp_prev_sec = max_timestamp - self.second_interval
            #print "start-time:%r, end_time:%r, limit:%r, uri:%d" % (
            #    start_time, end_time, max_timestamp_prev_sec, uri_id
            #)
            #self.cu.execute("""SELECT count(*) from history_visit
            #            where uri_id = ? and timestamp between ? and ?""",
            #            (uri_id, start_time, max_timestamp_prev_sec))
            #print "Before: count: %r" % (self.cu.fetchone()[0],)
            self.cu.execute("""DELETE FROM HISTORY_VISIT
                            WHERE uri_id = ? AND timestamp BETWEEN ? and ?""",
                            (uri_id, start_time, max_timestamp_prev_sec))
            #self.cu.execute("""SELECT count(*) from history_visit
            #            where uri_id = ? and timestamp between ? and ?""",
            #            (uri_id, start_time, max_timestamp_prev_sec))
            #print "After: count: %r" % (self.cu.fetchone()[0],)
        
    def perf_test_delete(self):
        """ Create a database with typical use over 2 months, and then
        clean it out.
        """
        # Simulate working over 6 weeks
        # 50 files each day
        # Each day add rand(5,10) new files and drop rand(3, 8) files
        # Each make 300 edits over our files, uniform selection
        self._next_uri = 50
        self.uri_nums = range(self._next_uri)
        self._most_recent_uri = 0
        start = timestamp()
        db_path = join("tmp", "perf_delete.sqlite")
        self.db = Database(db_path)
        with self.db.connect(True, cu=None) as cu:
            self.cu = cu
            cu.execute("DELETE FROM history_visit")
            cu.execute("SELECT julianday('now')")
            self.curr_time = float(cu.fetchone()[0])
            num_days = 42 # No, not that.  6 weeks.
            self.time = -1 * num_days;
            for day in range(num_days):
                if day % 7 < 2:
                    self._visit_weekend()
                else:
                    self._visit_weekday()
                self.time += 1
            cu.execute("SELECT count(*) from history_visit")
            num_to_delete = int(cu.fetchone()[0])
        print "Done"
        end = timestamp()
        print "time to fill the database with %d items: %.3fs" % (num_to_delete, end - start)
        # Now remove the entries
        
        with self.db.connect(True, cu=None) as cu:
            self.cu = cu
            # Remove P4: more than 28 days old
            cu.execute("SELECT count(*) from history_visit where timestamp < ?",
                       (self.curr_time - 28,))
            num_to_delete = int(cu.fetchone()[0])
            start = timestamp()
            cu.execute("DELETE from history_visit where timestamp < ?",
                       (self.curr_time - 28,))
            end = timestamp()
            cu.execute("SELECT count(*) from history_visit where timestamp < ?",
                       (self.curr_time - 28,))
            num_not_deleted = int(cu.fetchone()[0])
            print "P4 delete %d items (leaving %d undeleted): %.3fs" % (num_to_delete, num_not_deleted, end - start)
            
            # Cull P3: more than 7 days old
            cu.execute("SELECT count(*) from history_visit where timestamp < ?",
                       (self.curr_time - 7,))
            num_to_delete = int(cu.fetchone()[0])
            start = timestamp()
            for day in range(7, 21):
                self.cull_period(self.curr_time - day - 1, self.curr_time - day)
            end = timestamp()
            cu.execute("SELECT count(*) from history_visit where timestamp < ?",
                       (self.curr_time - 7,))
            num_not_deleted = int(cu.fetchone()[0])
            print "P3 delete over %d items (leaving %d undeleted): %.3fs" % (num_to_delete, num_not_deleted, end - start)
            
            # Cull P2: 1 - 7 days old
            cu.execute("SELECT count(*) from history_visit where timestamp between ? and ?",
                       (self.curr_time - 7, self.curr_time - 1))
            num_to_delete = int(cu.fetchone()[0])
            start = timestamp()
            hour_period = 1.0/24.0;
            for day in range(1, 7):
                for hour in range(0, 24):
                    hour_point = self.curr_time - day + hour * hour_period
                    self.cull_period(hour_point, hour_point + hour_period)
            end = timestamp()
            cu.execute("SELECT count(*) from history_visit where timestamp between ? and ?",
                       (self.curr_time - 7, self.curr_time - 1))
            num_not_deleted = int(cu.fetchone()[0])
            print "P2 delete over %d items (leaving %d undeleted): %.3fs" % (num_to_delete, num_not_deleted, end - start)
            



#---- mainline

def main(argv):
    #perf_uris()
    #perf_load()
    HistoryVisitor().perf_test_delete()

if __name__ == "__main__":
    retval = main(sys.argv)
    sys.exit(retval)