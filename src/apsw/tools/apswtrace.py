#!/usr/bin/env python
#
# See the accompanying LICENSE file.
#
# This module lets you automatically trace SQL operations in a program
# using APSW without having to modify the program in any way.

import time
import sys
import weakref

class APSWTracer(object):

    def __init__(self, options):
        if sys.version_info<(3,):
            self.u=eval("u''")
            import thread
            self.threadid=thread.get_ident
            self.stringtypes=(unicode,str)
            self.numtypes=(int, long, float)
            self.binarytypes=(buffer,)
        else:
            self.u=""
            import _thread
            self.threadid=_thread.get_ident
            self.stringtypes=(str,)
            self.numtypes=(int, float)
            self.binarytypes=(bytes,)
        self.options=options
        if options.output in ("-", "stdout"):
            self._writer=sys.stdout.write
        elif options.output=="stderr":
            self._writer=sys.stderr.write
        else:
            self._writer=open(options.output, "wt").write

        try:
            import apsw
            apsw.connection_hooks.append(self.connection_hook)
        except:
            sys.stderr.write(self.u+"Unable to import apsw\n")
            raise

        self.mapping_open_flags=apsw.mapping_open_flags
        self.zeroblob=apsw.zeroblob
        self.apswConnection=apsw.Connection

        self.newcursor={}
        self.threadsused={} # really want a set
        self.queries={}
        self.timings={}
        self.rowsreturned=0
        self.numcursors=0
        self.numconnections=0
        self.timestart=time.time()

    def writerpy2(self, s):
        # s should be a unicode string
        self._writer(s.encode("utf-8")+"\n")

    def writerpy3(self, s):
        self._writer(s+"\n")

    if sys.version_info<(3,):
        writer=writerpy2
    else:
        writer=writerpy3

    def format(self, obj):
        if isinstance(obj, dict):
            return self.formatdict(obj)
        if isinstance(obj, tuple):
            return self.formatseq(obj, '()')
        if isinstance(obj, list):
            return self.formatseq(obj, '[]')
        if isinstance(obj, self.stringtypes):
            return self.formatstring(obj)
        if obj is True:
            return "True"
        if obj is False:
            return "False"
        if obj is None:
            return "None"
        if isinstance(obj, self.numtypes):
            return repr(obj)
        if isinstance(obj, self.binarytypes):
            return self.formatbinary(obj)
        if isinstance(obj, self.zeroblob):
            return "zeroblob(%d)" % (obj.length(),)
        return repr(obj)

    def formatstring(self, obj, quote='"', checkmaxlen=True):
        obj=obj.replace("\n", "\\n").replace("\r", "\\r")
        if checkmaxlen and len(obj)>self.options.length:
            obj=obj[:self.options.length]+'..'
        return self.u+quote+obj+quote

    def formatdict(self, obj):
        items=list(obj.items())
        items.sort()
        op=[]
        for k,v in items:
            op.append(self.format(k)+": "+self.format(v))
        return self.u+"{"+", ".join(op)+"}"

    def formatseq(self, obj, paren):
        return self.u+paren[0]+", ".join([self.format(v) for v in obj])+paren[1]

    def formatbinarypy2(self, obj):
        if len(obj)<self.options.length:
            return "X'"+"".join(["%x" % ord(obj[i]) for i in range(len(obj))])+"'"
        return "(%d) X'"%(len(obj),)+"".join(["%x" % ord(obj[i]) for i in range(self.options.length)])+"..'"

    def formatbinarypy3(self, obj):
        if len(obj)<self.options.length:
            return "X'"+"".join(["%x" % obj[i] for i in range(len(obj))])+"'"
        return "(%d) X'"%(len(obj),)+"".join(["%x" % obj[i] for i in range(self.options.length)])+"..'"

    if sys.version_info<(3,):
        formatbinary=formatbinarypy2
    else:
        formatbinary=formatbinarypy3

    def sanitizesql(self, sql):
        sql=sql.strip("; \t\r\n")
        while sql.startswith("--"):
            sql=sql.split("\n", 1)[1]
            sql=sql.lstrip("; \t\r\n")
        return sql
            
    def profiler(self, sql, nanoseconds):
        sql=self.sanitizesql(sql)
        if sql not in self.timings:
            self.timings[sql]=[nanoseconds]
        else:
            self.timings[sql].append(nanoseconds)

    def cursorfinished(self, cursor):
        del self.newcursor[cursor]

    def exectracer(self, cursor, sql, bindings):
        tid=self.threadid()
        if tid not in self.threadsused:
            self.threadsused[tid]=True
        if self.options.report:
            fix=self.sanitizesql(sql)
            if fix not in self.queries:
                self.queries[fix]=1
            else:
                self.queries[fix]=self.queries[fix]+1
        if not isinstance(cursor, self.apswConnection):
            wr=weakref.ref(cursor, self.cursorfinished)
            if wr not in self.newcursor:
                self.newcursor[wr]=True
                self.numcursors+=1
                if self.options.sql:
                    self.log(id(cursor), "CURSORFROM:", "%x" % (id(cursor.getconnection()),),
                             "DB:", self.formatstring(cursor.getconnection().filename, checkmaxlen=False))
        if self.options.sql:
            args=[id(cursor), "SQL:", self.formatstring(sql, '', False)]
            if bindings:
                args.extend(["BINDINGS:", self.format(bindings)])
            self.log(*args)
        return True

    def rowtracer(self, cursor, row):
        if self.options.report:
            self.rowsreturned+=1
        if self.options.rows:
            self.log(id(cursor), "ROW:", self.format(row))
        return row

    def flagme(self, value, mapping, strip=""):
        v=[(k,v) for k,v in mapping.items() if isinstance(k, int)]
        v.sort()
        op=[]
        for k,v in v:
            if value&k:
                if v.startswith(strip):
                    v=v[len(strip):]
                op.append(v)
        return self.u+"|".join(op)

    def connection_hook(self, con):
        self.numconnections+=1
        if self.options.report:
            con.setprofile(self.profiler)
        if self.options.sql or self.options.report:
            con.setexectrace(self.exectracer)
        if self.options.rows or self.options.report:
            con.setrowtrace(self.rowtracer)
        if self.options.sql:
            self.log(id(con), "OPEN:", self.formatstring(con.filename, checkmaxlen=False), con.open_vfs, self.flagme(con.open_flags, self.mapping_open_flags, "SQLITE_OPEN_"))

    def log(self, lid, ltype, *args):
        out=["%x" % (lid,)]
        if self.options.timestamps:
            out.append("%.03f" % (time.time()-self.timestart,))
        if self.options.thread:
            out.append("%x" % (self.threadid(),))
        out.append(ltype)
        out.extend(args)
        self.writer(self.u+" ".join(out))

    def run(self):
        import sys
        import __main__
        d=__main__.__dict__
        if sys.version_info<(3,):
            execfile(sys.argv[0],d, d)
        else:
            # We use compile so that filename is present in printed exceptions
            code=compile(open(sys.argv[0], "rb").read(), sys.argv[0], "exec")
            exec(code, d, d)

    def mostpopular(self, howmany):
        all=[(v,k) for k,v in self.queries.items()]
        all.sort()
        all.reverse()
        return all[:howmany]
        
    def longestrunningaggregate(self, howmany):
        all=[(sum(v),len(v),k) for k,v in self.timings.items()]
        all.sort()
        all.reverse()
        return all[:howmany]

    def longestrunningindividual(self, howmany):
        res=[]
        for k,v in self.timings.items():
            for t in v:
                res.append( (t, k) )
        res.sort()
        res.reverse()
        res=res[:howmany]
        return res

    def report(self):
        import time
        if not self.options.report:
            return
        w=lambda *args: self.writer(self.u+" ".join(args))
        if "summary" in self.options.reports:
            w("APSW TRACE SUMMARY REPORT")
            w()
            w("Program run time                   ", "%.03f seconds" % (time.time()-self.timestart,))
            w("Total connections                  ", str(self.numconnections))
            w("Total cursors                      ", str(self.numcursors))
            w("Number of threads used for queries ", str(len(self.threadsused)))
        total=0
        for k,v in self.queries.items():
            total+=v
        fmtq=len("%d" % (total,))+1
        if "summary" in self.options.reports:
            w("Total queries                      ", str(total))
            w("Number of distinct queries         ", str(len(self.queries)))
            w("Number of rows returned            ", str(self.rowsreturned))
            total=0
            for k,v in self.timings.items():
                for v2 in v:
                    total+=v2
            w("Time spent processing queries      ", "%.03f seconds" % (total/1000000000.0))

        # show most popular queries
        if "popular" in self.options.reports:
            w()
            w("MOST POPULAR QUERIES")
            w()
            for count, query in self.mostpopular(self.options.reportn):
                w("% *d" % (fmtq, count,), self.formatstring(query, '', False))

        # show longest running (aggregate)
        if "aggregate" in self.options.reports:
            w()
            w("LONGEST RUNNING - AGGREGATE")
            w()
            fmtt=None
            for total, count, query in self.longestrunningaggregate(self.options.reportn):
                if fmtt is None:
                    fmtt=len(fmtfloat(total/1000000000.0))+1
                w("% *d %s" % (fmtq, count, fmtfloat(total/1000000000.0, total=fmtt)), self.formatstring(query, '', False))

        # show longest running (individual)
        if "individual" in self.options.reports:
            w()
            w("LONGEST RUNNING - INDIVIDUAL")
            w()
            fmtt=None
            for t,query in self.longestrunningindividual(self.options.reportn):
                if fmtt is None:
                    fmtt=len(fmtfloat(total/1000000000.0))+1
                w(fmtfloat(t/1000000000.0, total=fmtt), self.formatstring(query, '', False))

def fmtfloat(n, decimals=3, total=None):
    "Work around borken python float formatting"
    s="%0.*f" % (decimals, n)
    if total:
        s=(" "*total+s)[-total:]
    return s

def main():
    import optparse
    import os
    import sys

    reports=("summary", "popular", "aggregate", "individual")

    parser=optparse.OptionParser(usage="%prog [options] pythonscript.py [pythonscriptoptions]",
                                 description="This script runs a Python program that uses APSW "
                                 "and reports on SQL queries without modifying the program.  This is "
                                 "done by using connection_hooks and registering row and execution "
                                 "tracers.  See APSW documentation for more details on the output.")
    parser.add_option("-o", "--output", dest="output", default="stdout",
                      help="Where to send the output.  Use a filename, a single dash for stdout, or the words stdout and stderr. [%default]")
    parser.add_option("-s", "--sql", dest="sql", default=False, action="store_true",
                      help="Log SQL statements as they are executed. [%default]")
    parser.add_option("-r", "--rows", dest="rows", default=False, action="store_true",
                      help="Log returned rows as they are returned (turns on sql). [%default]")
    parser.add_option("-t", "--timestamps", dest="timestamps", default=False, action="store_true",
                      help="Include timestamps in logging")
    parser.add_option("-i", "--thread", dest="thread", default=False, action="store_true",
                      help="Include thread id in logging")
    parser.add_option("-l", "--length", dest="length", default=30, type="int",
                      help="Max amount of a string to print [%default]")
    parser.add_option("--no-report", dest="report", default=True, action="store_false",
                      help="A summary report is normally generated at program exit.  This turns off the report and saves memory.")
    parser.add_option("--report-items", dest="reportn", metavar="N", default=15, type="int",
                      help="How many items to report in top lists [%default]")
    parser.add_option("--reports", dest="reports", default=",".join(reports),
                      help="Which reports to show [%default]")

    parser.disable_interspersed_args()
    options, args=parser.parse_args()

    options.reports=[x.strip() for x in options.reports.split(",") if x.strip()]
    for r in options.reports:
        if r not in reports:
            parser.error(r+" is not a valid report.  You should supply one or more of "+", ".join(reports))

    if options.rows:
        options.sql=True

    if not args:
        parser.error("You must specify a python script to execute")

    if not os.path.exists(args[0]):
        parser.error("Unable to find script %r\n" % (args[0],))

    sys.argv=args
    sys.path[0]=os.path.split(os.path.abspath(sys.argv[0]))[0]

    t=APSWTracer(options)

    try:
        t.run()
    finally:
        t.report()

if __name__=="__main__":
    main()
