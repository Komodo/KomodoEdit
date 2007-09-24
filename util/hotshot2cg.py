#!/usr/bin/env python
# _*_ coding: latin1 _*_

#
# Copyright (c) 2003 by WEB.DE, Karlsruhe
# Autor: Jörg Beyer <job@webde-ag.de>
#
# hotshot2cachegrind is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.
#
#
# This script transforms the pstat output of the hotshot
# python profiler into the input of kcachegrind. 
#
# example usage:
# modify you python script to run this code:
#
# import hotshot
# filename = "pythongrind.prof"
# prof = hotshot.Profile(filename, lineevents=1)
# prof.runcall(run) # assuming that "run" should be called.
# prof.close()
#
# it will run the "run"-method under profiling and write
# the results in a file, called "pythongrind.prof".
#
# then call this script:
# hotshot2cachegrind -o <output> <input>
# or here:
# hotshot2cachegrind cachegrind.out.0 pythongrind.prof
#
# then call kcachegrind:
# kcachegrind cachegrind.out.0
#
# TODO: 
#  * es gibt Probleme mit rekursiven (direkt und indirekt) Aufrufen - dann
#    stimmen die Kosten nicht.
#
#  * einige Funktionen werden mit "?" als Name angezeigt. Evtl sind
#    das nur die C/C++ extensions.
#
#  * es fehlt noch ein Funktionsnamen Mangling, dass die Filenamen berücksichtigt,
#    zZ sind alle __init__'s und alle run's schwer unterscheidbar :-(
#
version = "$Revision: 1.1 $"
progname = "hotshot2cachegrind"

import os, sys
from hotshot import stats,log
import os.path 

file_limit=0

what2text = { 
    log.WHAT_ADD_INFO    : "ADD_INFO", 
    log.WHAT_DEFINE_FUNC : "DEFINE_FUNC", 
    log.WHAT_DEFINE_FILE : "DEFINE_FILE", 
    log.WHAT_LINENO      : "LINENO", 
    log.WHAT_EXIT        : "EXIT", 
    log.WHAT_ENTER       : "ENTER"}

# a pseudo caller on the caller stack. This represents
# the Python interpreter that executes the given python 
# code.
root_caller = ("PythonInterpreter",0,"execute")

class CallStack:
    """A tiny Stack implementation, based on python lists"""
    def __init__(self):
       self.stack = []
       self.recursion_counter = {}
    def push(self, elem):
        """put something on the stack"""
        self.stack.append(elem)
        rc = self.recursion_counter.get(elem, 0)
        self.recursion_counter[elem] = rc + 1

    def pop(self):
        """get the head element of the stack and remove it from teh stack"""
        elem = self.stack[-1:][0]
        rc = self.recursion_counter.get(elem) - 1
        if rc>0:
            self.recursion_counter[elem] = rc
        else:
            del self.recursion_counter[elem]
        return self.stack.pop()

    def top(self):
        """get the head element of the stack, stack is unchanged."""
        return self.stack[-1:][0]
    def handleLineCost(self, tdelta):
        p, c = self.stack.pop()
        self.stack.append( (p,c + tdelta) )
    def size(self):
        """ return how many elements the stack has"""
        return len(self.stack)

    def __str__(self):
        return "[stack: %s]" % self.stack

    def recursion(self, pos):
        return self.recursion_counter.get(pos, 0)
        #return self.recursion_dict.has_key((entry[0][0], entry[0][2]))

def return_from_call(caller_stack, call_dict, cost_now):
    """return from a function call
       remove the function from the caller stack,
       add the costs to the calling function.
    """
    called, cost_at_enter = caller_stack.pop()
    caller, caller_cost = caller_stack.top()

    #print "return_from_call: %s ruft %s" % (caller, called,)

    per_file_dict = call_dict.get(called[0], {})
    per_caller_dict = per_file_dict.get(called[2], {})
    cost_so_far, call_counter = per_caller_dict.get(caller, (0, 0))

    if caller_stack.recursion(called):
        per_caller_dict[caller] = (cost_so_far, call_counter + 1)
    else:
        per_caller_dict[caller] = (cost_so_far + cost_now - cost_at_enter, call_counter + 1)

    per_file_dict[called[2]] = per_caller_dict
    call_dict[called[0]] = per_file_dict


def updateStatus(filecount):
    sys.stdout.write("reading File #%d    \r" % filecount)
    sys.stdout.flush()
def convertProfFiles(output, inputfilenames):
    """convert all the given input files into one kcachegrind 
       input file.
    """
    call_dict = {}
    cost_per_pos = {}
    cost_per_function = {}
    caller_stack = CallStack()
    caller_stack.push((root_caller, 0))

    total_cost = 0
    filecount = 1
    number_of_files = len(inputfilenames)
    for inputfilename in inputfilenames:
        updateStatus(filecount)
        cost, filecount = convertHandleFilename(inputfilename, caller_stack, call_dict, cost_per_pos, cost_per_function, filecount)
        total_cost += cost
        if (file_limit > 0) and (filecount > file_limit):
            break
    
    print
    print "total_cost: % d Ticks",total_cost
    dumpResults(output, call_dict, total_cost, cost_per_pos, cost_per_function)

def convertHandleFilename(inputfilename, caller_stack, call_dict, cost_per_pos, cost_per_function, filecount):
    updateStatus(filecount)
    if not ((file_limit > 0) and (filecount > file_limit)):
        if os.path.isdir(inputfilename):
            cost, filecount = convertProfDir(inputfilename, caller_stack, call_dict, cost_per_pos, cost_per_function, filecount)
        elif os.path.isfile(inputfilename):
            cost = convertProfFile(inputfilename, caller_stack, call_dict, cost_per_pos, cost_per_function)
            filecount += 1 
        else:
            sys.stderr.write("warn: ignoring '%s', is no file and no directory\n" % inputfilename)
            cost = 0
    return (cost, filecount)

def convertProfDir(start, caller_stack, call_dict, cost_per_pos, cost_per_function, filecount):
    cost = 0
    filenames = os.listdir(start)
    for f in filenames:
        if (file_limit > 0) and (filecount > file_limit): 
            break
        full = os.path.join(start, f)
        c, filecount = convertHandleFilename(full, caller_stack, call_dict, cost_per_pos, cost_per_function, filecount)
        cost += c;
    return (cost, filecount)

def handleCostPerPos(cost_per_pos, pos, current_cost):
    """
       the cost per source position are managed in a dict in a dict.

       the cost are handled per file and there per function.
       so, the per-file-dict contains some per-function-dicts
       which sum up the cost per line (in this function and in 
       this file).
    """
    filename  = pos[0]
    lineno    = pos[1]
    funcname  = pos[2]
    file_dict = cost_per_pos.get(filename, {})
    func_dict = file_dict.get(funcname, {})
    func_dict.setdefault(lineno, 0)
    func_dict[lineno] += current_cost
    file_dict[funcname] = func_dict
    cost_per_pos[filename] = file_dict

def convertProfFile(inputfilename, caller_stack, call_dict, cost_per_pos, cost_per_function):
    """convert a single input file into one kcachegrind
       data.

       this is the most expensive function in this python source :-)
    """

    total_cost = 0
    try:
        logreader = log.LogReader(inputfilename)
        current_cost = 0
        hc = handleCostPerPos # shortcut
        for item in logreader:
            what, pos ,tdelta = item
            (file, lineno, func) = pos
            #line = "%s %s %d %s %d" % (what2text[what], file, lineno, func, tdelta)
            #print line
            # most common cases first
            if what == log.WHAT_LINENO:
                # add the current cost to the current function
                hc(cost_per_pos, pos, tdelta)
                total_cost += tdelta
            elif what == log.WHAT_ENTER:
                caller_stack.push((pos, total_cost))
                hc(cost_per_pos, pos, tdelta)
                total_cost += tdelta
            elif what == log.WHAT_EXIT:
                hc(cost_per_pos, pos, tdelta)
                total_cost += tdelta
                return_from_call(caller_stack, call_dict, total_cost)
            else:
                assert 0, "duh: %d" % what


        # I have no idea, why sometimes the stack is not empty - we
        # have to rewind the stack to get 100% for the root_caller
        while caller_stack.size() > 1:
            return_from_call(caller_stack, call_dict, total_cost)

    except IOError:
        print "could not open inputfile '%s', ignore this." % inputfilename
    except EOFError, m:
        print "EOF: %s" % (m,)
    return total_cost

def pretty_name(file, function):
    #pfile = os.path.splitext(os.path.basename(file)) [0]
    #return "%s_[%s]" % (function, file)
    return "%s" % function
    #return "%s::%s" % (file, function)
    #return "%s_%s" % (pfile, function)

class TagWriter:
    def __init__(self, output):
        self.output = output
        self.last_values = {}

    def clearTag(self, tag):
        if self.last_values.has_key(tag):
            del self.last_values[ tag ]
    def clear(self):
        self.last_values = {}

    def write(self, tag, value):
        self.output.write("%s=%s\n" % (tag, value))
        #if (not self.last_values.has_key(tag)) or self.last_values[tag] != value:
        #    self.last_values[ tag ] = value
        #    self.output.write("%s=%s\n" % (tag, value))

def dumpResults(output, call_dict, total_cost, cost_per_pos, cost_per_function):
    """write the collected results in the format kcachegrind
       could read.
    """
    # the intro
    output.write("events: Tick\n")
    output.write("summary: %d\n" % total_cost)
    output.write("cmd: your python script\n")
    output.write("\n")
    tagwriter = TagWriter(output)

    # now the costs per line
    for file in cost_per_pos.keys():
        func_dict = cost_per_pos[file]
        for func in func_dict.keys():
            line_dict = func_dict[func]
            tagwriter.write("ob", file)
            tagwriter.write("fn", func)# pretty_name(file, func)) ; output.write("# ^--- 2\n")
            tagwriter.write("fl", file)
            for line in line_dict:
                output.write("%d %d\n" %( line, line_dict[line] ))

    output.write("\n\n")
    # now the function calls. For each caller all the called
    # functions and their costs are written.
    for file in call_dict.keys():
        per_file_dict = call_dict[file]
        #print "file %s -> %s" % (file, per_file_dict)
        for called_x in per_file_dict.keys():
            #print "called_x:",called_x
            per_caller_dict = per_file_dict[called_x]
            #print "called_x %s wird gerufen von: %s" % (called_x, per_caller_dict)
            for caller_x in per_caller_dict.keys():
                tagwriter.write("ob", caller_x[0])
                tagwriter.write("fn", caller_x[2])# pretty_name(caller_x[2], caller_x[0])) ; output.write("# ^--- 1\n")
                tagwriter.write("fl", caller_x[0])
                tagwriter.write("cob", file)
                tagwriter.write("cfn", called_x) #pretty_name(file, called_x))
                #tagwriter.write("cfl", file)
                cost, count = per_caller_dict[caller_x]
                #print "called_x:",called_x
                output.write("calls=%d\n%d %d\n" % (count, caller_x[1], cost))
                tagwriter.clear()
                #tagwriter.clearTag("cob")
                # is it a bug in kcachegrind, that the "cob=xxx" line has
                # to be rewritten after a calls entry with costline ?
                #assert cost <= total_cost, "caller_x: %s, per_caller_dict: %s " % (caller_x, per_caller_dict, )
                #output.write("calls=%d\n%d %d\n" % (count, caller_x[1], cost))
                output.write("\n")

def run_without_optparse():
    """parse the options without optparse, use sys.argv"""
    if  len(sys.argv) < 4 or sys.argv[1] != "-o" :
        print "usage: hotshot2cachegrind -o outputfile in1 [in2 [in3 [...]]]"
        return
    outputfilename = sys.argv[2]
    try:
        output = file(outputfilename, "w")
        args = sys.argv[3:]
        convertProfFiles(output, args)
        output.close()
    except IOError:
        print "could not open '%s' for writing." % outputfilename

def run_with_optparse():
    """parse the options with optparse"""

    global file_limit

    versiontext = "%s version: %s" % ( progname, version.split()[1], )
    parser = OptionParser(version=versiontext)
    parser.add_option("-o", "--output",
      action="store", type="string", dest="outputfilename",
      help="write output into FILE")
    parser.add_option("--file-limit",
      action="store", dest="file_limit", default=0,
      help="stop after given number of input files")
    output = sys.stdout
    close_output = 0
    (options, args) = parser.parse_args()
    file_limit = int(options.file_limit)
    try:
        if options.outputfilename and options.outputfilename != "-":
            output = file(options.outputfilename, "w")
            close_output = 1
    except IOError:
        print "could not open '%s' for writing." % options.outputfilename
    if output:
        convertProfFiles(output, args)
        if close_output:
            output.close()


def profile_myself():
    import hotshot
    filename = "self.prof"
    if not os.path.exists(filename):
        prof = hotshot.Profile(filename, lineevents=1)
        prof.runcall(run)
        prof.close()
    else:
        print "not profiling myself, since '%s' exists, running normal" % filename
        run()

# check if optparse is available.
try:
    from optparse import OptionParser
    run = run_with_optparse
except ImportError:
    run = run_without_optparse

if __name__ == "__main__":
    try:
        run()
        #profile_myself()
    except KeyboardInterrupt:
        sys.exit(1)
