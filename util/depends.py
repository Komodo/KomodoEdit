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

# Script to analyze dependencies between XUL, JS and DTD files to eliminate bloat.
from __future__ import generators
import os, re, fnmatch, sys, pprint
jsmap = {}  # map from JS filenames to JS objects
xulmap = {}  # map from XUL filenames to XUL objects
warnings = []
errors = []
funcmap = {}  # map from function names to JS objects corresponding to files where they are defined.

JSGlobals = ['dump', 'alertDialog', 'setTimeout', 'getService', 'doSendInput', 'alert', 'typeof',
             'getAttribute', 'getElementsByTagName', 'getElementById', 'open', 'write', 'close', 'setAttribute',
             'eval']

def findallfiles(dirname):
    """Generate all files in given directory or children thereof."""
    contents = os.listdir(dirname)
    for f in contents:
        fullpath = os.path.join(dirname, f)
        if os.path.isfile(fullpath):
            yield fullpath
        if os.path.isdir(fullpath):
            for subdirname in findallfiles(fullpath):
                yield subdirname

    

def find_files(basedir, pattern):
    files = []
    for file in findallfiles(basedir):
        if fnmatch.fnmatch(file, pattern):
            files.append(file)
    return files


class File:
    def __init__(self, fname):
        #print "GOT ", fname
        self.fname = fname
        self.data = open(fname).read()

useRE = re.compile("([_\w]+?)\([^\)]*?\)\s*;", re.DOTALL);
bodysplitRE = re.compile(r"function (\w+)[^\{]+?\{\n(.*?)\n\}", re.DOTALL)
jsdepends = {}


class JS(File):
    def __init__(self, *args, **kw):
        File.__init__(self, *args, **kw)
        self.indirectfuncnames = []
        self.fname = os.path.normpath(self.fname)
        assert self.fname.startswith('src\\chrome\\komodo\\content\\')
        self.fname = self.fname[len('src\\chrome\\komodo\\content\\'):]
        jsmap[self.fname] = self  # registration of ourselves as a known JS file
        self.defines = {}
        self.uses = {}  # list of functions called in this file
        self.includedby= [] # XUL files which include us

    def __str__(self):
        return "\"%s\"" % self.fname
        
    def get_weight(self):
        # return a measure of how heavy this file is
        return '%d/%d' % (len(self.defines), len(self.uses))
    
    def analyze(self):
        # these are regular functions
        for line in self.data.split('\n'):
            match = re.match("function (\w+)\s*?\(", line)
            if match is None:
                call = re.match("\s*?(_\w+?)\(.*\)?;?\n", line)
                if call is not None:
                     # we've found a function _call_
                     calledfunc = call.group(1)
                     self.defines[currentfunction][calledfunc] = 1
            else:
                currentfunction = match.group(1)
                self.defines[currentfunction] = {}
        #pprint.pprint(self.defines)
        
        fname = self.fname
        for func in self.defines:
            if func in funcmap:
                funcmap[func].append(self)
            else:
                funcmap[func] = [self]
        # these are method names
        #matches = re.findall("\.prototype\.(.*?)\s*?=\s*?function", self.data)
        #self.funcnames.extend(matches)
        # this tries to figure out all of the functions being _called_ inside this file.
        uses = re.findall(useRE, self.data)
        uses = [use for use in uses if use not in JSGlobals]
        for use in uses: # make unique
            if use not in self.uses:
                self.uses[use] = 1 # Should instead map where they're defined
        # need to find which function calls which function.
        
        # We need to find out what functions a given JS function depends on.
        # split the data in groups
        #print self.data
        bodies = re.findall(bodysplitRE, self.data)
        for funcname, funcbody in bodies:
            #print 'XXX', funcname
            uses = re.findall(useRE, funcbody)
            jsdepends.setdefault(funcname, []).extend(uses)
        #if fname.endswith('perlapp.js'):
        #    print self.uses.keys()
        #    raise SystemExit

class XUL(File):
    def __init__(self, *args, **kw):
        File.__init__(self, *args, **kw)
        self.fname = os.path.normpath(self.fname)
        assert self.fname.startswith('src\\chrome\\komodo\\content\\'), self.fname
        self.fname = self.fname[len('src\\chrome\\komodo\\content\\'):]
        xulmap[self.fname] = self  # registration of ourselves as a known JS file
        self.jsfiles = []  # list of JS objects for each JS file included
        self.imports = {}  # map of function names available to the Namespace to
                           # the JS object corresponding. (only 1 allowed --
                           # error otherwise)
        self.required_funcs = {}  # map of required functions, mapped to the files in which they're defined
        
    def describe(self):
        mainJS = mapMainJSFiles[self]
        print "FNAME = ", self.fname
        print "USES FUNCTIONS: ", ' '.join(self.uses)
        print "MAIN JS", mapMainJSFiles[self].fname
        print "called by main", '\n\t'.join(mainJS.uses)
        #print "Main funcs", ' '.join(mainJS.defines.keys())
        perfiles = {}
        for k,v in self.imports.items():
            if type(k) != type(''):
                print type(k), k, type(v), v
                raise SystemExit
            perfiles.setdefault(v.fname, []).append(k)
        for used in self.uses:
            print used
            if used not in deepjsdepends:
                print used + ' has no depency info\n'
                continue
            for func in deepjsdepends[used]:
                if func in funcmap:
                    filename = funcmap[func][0].fname
                    if (type(func) == type('')):
                        perfiles.setdefault(filename, []).append(func)
                    else:
                        perfiles.setdefault(filename, []).extend(func)
                else:
                    if (func in JSGlobals): continue
                    print 'func=', func
                    #raise SystemExit
                    filename = 'mystery!'
                    set = perfiles.setdefault(filename, [])
                    if func not in set: set.append(func)
                print "FILENAME", filename
        print "EXTRAS:"
        useds = self.uses + mainJS.defines.keys()
        print useds
        n = useds[:]
        for used in useds:
            if used in deepjsdepends:
                n.extend(deepjsdepends[used])
            else:
                print 'XXX weird', used
        x = {}
        for used in n:
            x[used] = 1
        for file, funcs in perfiles.items():
            print file + ': \n',
            if type(funcs) == type(''): funcs = [funcs]
            funcs.sort()
            for func in funcs:
                if func in x:
                    print '\t'+'* '+func
                else:
                    print '\t'+'  '+func
        #print "IMPORTS: ", extras.keys()

    def __str__(self):
        return "<%s>" % self.fname
        
    def _addJS(self, match, fname, debug=0):
        if match not in jsmap:
            errors.append("File %(match)s is imported by %(fname)s but isn't in our tree!" % vars())
            return
        js = jsmap[match]
        if js in self.jsfiles:
            print "%(js)s is included multiple times in %(fname)s" % vars()
            return
        if debug: "APPENDING ", js
        self.jsfiles.append(js)
        if fname not in js.includedby:
            js.includedby.append(fname)  # add one to the use count for that file
        for f in js.defines:
            if f in self.imports:
                origimport = self.imports[f].fname
                thisimport = js.fname
                if (origimport != thisimport):
                    errors.append('Function %(f)s is defined in \n%(thisimport)s AND in \n%(origimport)s \n(imported by %(fname)s' % vars())
            else: # XXX check logic
                self.imports[f] = js

    def analyze(self):
        self.mainjs = mapMainJSFiles.get(self, None)

        # look for occurences of the word function.
        matches = re.findall('<script.*?src="chrome://komodo/content/(.*?.js)"\s*/>', self.data)
        fname = self.fname
        debug = 0
        if fname.endswith('@@@perlapp.xul'): debug = 1
        #if debug: print "MATCHES FOR %(fname)s = " % vars(), matches 
        for match in matches:
            match = os.path.normpath(match)
            if debug: print "IN MATCH LOOP, MATCH + ", match
            #assert match.startswith('src\\chrome\\komodo\\content\\')
            #match = self.fname[len('src\\chrome\\komodo\\content\\'):]
            #if debug: print "BEFORE ADD, JSFILES = ", self.jsfiles
            self._addJS(match, fname, debug)
            #if debug: print "AFTER ADD, JSFILES = ", self.jsfiles
        self.defines = re.findall("function (\w+)\s*?\(", self.data)
        self.uses = re.findall(useRE, self.data)
        self.uses = [use for use in self.uses if use not in JSGlobals]
        #print self.fname, "uses", self.uses
        # need to find out which functions are _defined_ here

    def second_phase(self):
        # look for OVERLAYs
        fname = self.fname
        if fname.endswith("@@authenticate.xul"): debug = 1
        overlays = re.findall('<\?xul-overlay.*?href="chrome://komodo/content/(.*?.xul)"\?>', self.data)
        if not overlays: return
        self.overlays = [os.path.normpath(overlay) for overlay in overlays]
        for overlay in self.overlays:
            if overlay not in xulmap:
                errors.append("Unfindable overlay %(overlay)s included by %(fname)s" % vars())
                continue
            for js in xulmap[overlay].jsfiles:
                self._addJS(js.fname, overlay)

def find(hash, name):
    for x in hash:
        if x.fname.find(name) != -1:
            return x
    raise "not found"


mapMainJSFiles = {}

def teachMain(xulleaf, jsleaf):
    xul = find(xulfiles, xulleaf)
    js = find(jsfiles, jsleaf)
    mapMainJSFiles[xul] = js

# these appear to have circular dependencies somewhere in their call tree -- lovely
#exceptions = {'_updateKomodoHomePage':1, 'refreshPage':1, 'deleteMRUCell': 1, 'mruOnLoad': 1, 'updateKomodoHomePage':1, 'which':1}
def makedeepjsdepends(trace=0):
    global deepjsdepends
    deepjsdepends = {}
    for funcname in jsdepends:
            if trace: print 'making deep for', funcname
            deepjsdepends[funcname] = []
            for callee in find_callees(funcname, {}):
                deepjsdepends[funcname].append(callee)
    return deepjsdepends



def find_callees(funcname, _cache, trace=0):
    # look for each direct callee
    if funcname not in jsdepends: return
    _cache[funcname] = 1
    for callee in jsdepends[funcname]:
        if callee in _cache: continue
        if trace: print 'looking at', callee
        if funcname == callee: return  # some sick case
        for secondcaller in find_callees(callee, _cache, trace):
            if secondcaller != callee and secondcaller != funcname and secondcaller not in _cache:
            #if trace: print 'looking at', callee
                _cache[secondcaller] = 1
                yield secondcaller
        yield callee

def run(basedir):
    global xulfiles, jsfiles
    
    jsfiles = find_files(basedir, "*.js")
    print "Found %d JS files" % len(jsfiles)
    jsfiles = [JS(file) for file in jsfiles]
    print "Processing JS files: ",
    for file in jsfiles:
        file.analyze()
        sys.stdout.write('.')
    print
    xulfiles = find_files(basedir, "*.xul")
    print "Processed %d XUL files" % len(xulfiles)
    xulfiles = [XUL(file) for file in xulfiles]


    teachMain('find.xul', 'find.js')

    print "Processing XUL files: ",
    for file in xulfiles:
        file.analyze()
        sys.stdout.write('.')
    print
    
    for f in xulmap.keys():
        if f.endswith('koPlatformEditorBindings.xul'):
            xulmap['koPlatformEditorBindings.xul'] = xulmap[f]
            del xulmap[f]
            continue
        if f.endswith('koPlatformDialogOverlay.xul'):
            xulmap['koPlatformDialogOverlay.xul'] = xulmap[f]
            del xulmap[f]
            continue

    print "Processing XUL files, phase 2: ",
    for xul in xulfiles:
        xul.second_phase()
        sys.stdout.write('.')
    print
    print
    
    # now jsdepends needs to have its tree 'followed out'
    
    global deepjsdepends    
    makedeepjsdepends()
    #for (func, callees) in deepjsdepends.items():
    #    print func, ':', ' '.join(callees)
    funcs = deepjsdepends.keys()
    funcs.sort()
    #print '\n'.join(funcs)
    print deepjsdepends['func_helpPerlMailingLists']
    perlapp_xul = find(xulfiles, 'find.xul')
    perlapp_xul.describe()
    
    return    
    print '-'*70
    print "JS files never referenced by XUL:"
    uses = jsmap.items()
    MIA = [fname for (fname, js) in uses if len(js.includedby) == 0]
    for fname in MIA:
        print '\t' + fname
    print
    print
    print '-'*70
    print "JS files referenced more than once:"
    perfileuses = [(fname, js.includedby) for (fname, js) in uses if len(js.includedby) > 1]
    perfileuses .sort(lambda a,b: cmp(len(a), len(b)))
    for fname, specuses in perfileuses :
        weight = jsmap[fname].get_weight()
        print '%(fname)s (%(weight)s): referenced by' % vars()
        for use in specuses:
            print "\t%(use)s" % vars()
    print
    print
    print '-'*70
    print "Duplicate Definitions:"
    dupes = funcmap.items()
    dupes.sort(lambda i,j: cmp(len(i[1]), len(j[1])))
    dupes = [dupe for dupe in dupes if len(dupe[1]) > 1]
    for func, jss in dupes:
        names = '\n\t'.join([str(js) for js in jss])
        print '%(func)s defined in:\n\t%(names)s' % vars()
    print
    print
    # Now the hard part -- figure out what functions a XUL file really uses, and what functions those need
    # and where they are, and what functions are being loaded but aren't necessary.
    for xul in xulfiles:
        fname = xul.fname
        for func in xul.uses:
            if func in xul.defines:  # XUL fines can define their own.
                found = 1
                break
            found = 0
            jss = xul.jsfiles
            for js in jss:
                #print js
                if func in js.defines:
                    found = 1
                    break
            if not found:
                print 'Function %(func)s not found in any of the included files in %(fname)s' % vars()
                for js in jss:
                    print '\t'+js.fname
    
    print 'Number of functions included by each XUL file'
    for xul in xulfiles:
        total = 0
        for js in xul.jsfiles:
            total += len(js.defines)
        fname = xul.fname
        print "%(fname)s: --> %(total)d" % vars()

    for xul in xulfiles:
        total = 0
        print "XULFILE: ", xul.fname
        for func in xul.uses:
            print func
            

    if errors:
        print
        print
        print '-'*70
        print "ERRORS FOUND:\n"
        for error in errors: print error
def test():
    run('src\chrome\komodo\content')
    
if __name__ == "__main__":
    test()
    