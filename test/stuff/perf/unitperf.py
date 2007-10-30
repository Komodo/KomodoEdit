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
#
# Adapted from Python's unittest.py:
#   Copyright (c) 1999, 2000, 2001 Steve Purcell
#   This module is free software, and you may redistribute it and/or
#   modify it under the same terms as Python itself, so long as this
#   copyright message and disclaimer are retained in their original
#   form.
#
#   IN NO EVENT SHALL THE AUTHOR BE LIABLE TO ANY PARTY FOR DIRECT,
#   INDIRECT, SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES ARISING OUT
#   OF THE USE OF THIS CODE, EVEN IF THE AUTHOR HAS BEEN ADVISED OF THE
#   POSSIBILITY OF SUCH DAMAGE.
#
#   THE AUTHOR SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING, BUT NOT
#   LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
#   FOR A PARTICULAR PURPOSE.  THE CODE PROVIDED HEREUNDER IS ON AN "AS
#   IS" BASIS, AND THERE IS NO OBLIGATION WHATSOEVER TO PROVIDE
#   MAINTENANCE, SUPPORT, UPDATES, ENHANCEMENTS, OR MODIFICATIONS.

"""Python performance metric framework (based on Python's unittest.py)

This module contains the core framework classes for writing performance
metric tests, or "perfs", (PerfCase, PerfSuite, etc.). Writing perfs is
similar to writing tests with Python's unittest framework.

Simple usage:

    import unitperf

    class StartupPerfCase(unitperf.PerfCase):
        def perf_startup(self):  # perf method names begin 'perf_*'
            "startup time (ms)"
            #... code to test how long app takes to startup
            return startup_time

    if __name__ == '__main__':
        suite = unitperf.makeSuite(StartupPerfCase)
        runner = unitperf.TextPerfRunner(verbosity=2)
        runner.run(suite)
"""

_version_ = (0, 1, 0)

import os
import sys
import time
import types



#---- perf framework core

class PerfResult:
    """Holder for perf result information.

    Perf results are automatically managed by the PerfCase and PerfSuite
    classes, and do not need to be explicitly manipulated by writers of
    perfs.

    Each instance holds the total number of perfs run, and collections of
    results from those perf runs. The collections contain tuples of
    (<perfcase>, <result>), where <result> is the floating point result
    of a perf.
    """
    def __init__(self):
        self.results = []
        self.perfsRun = 0
        self.shouldStop = 0

    def startPerf(self, perf):
        "Called when the given perf is about to be run"
        self.perfsRun = self.perfsRun + 1

    def stopPerf(self, perf):
        "Called when the given perf has been run"
        pass

    def addResult(self, perf, result, log=None):
        "Called when a perf has completed successfully"
        self.results.append( (perf, result, log) )

    def stop(self):
        "Indicates that the perfs should be aborted"
        self.shouldStop = 1

    def __repr__(self):
        return "<%s run=%i results=%i>" % \
               (self.__class__, self.perfsRun, len(self.results))


class PerfCase:
    """A class whose instances are single perf cases.

    By default, the perf code itself should be placed in a method named
    'runPerf'.

    If the fixture may be used for many perf cases, create as many perf
    methods as are needed. When instantiating such a PerfCase subclass,
    specify in the constructor arguments the name of the perf method
    that the instance is to execute.

    Perf authors should subclass PerfCase for their own perfs.
    Construction and deconstruction of the perf's environment
    ('fixture') can be implemented by overriding the 'setUp' and
    'tearDown' methods respectively.

    If it is necessary to override the __init__ method, the base class
    __init__ method must always be called. It is important that
    subclasses should not change the signature of their __init__ method,
    since instances of the classes are instantiated automatically by
    parts of the framework in order to be run.
    """
    def __init__(self, methodName='runPerf'):
        """Create a PerfCase
        
        "methodName" is the name of the method to run when executed.
            Raises a ValueError if the instance does not have a method
            with the specified name.
        """
        try:
            self.__perfMethodName = methodName
            perfMethod = getattr(self, methodName)
            self.__perfMethodDoc = perfMethod.__doc__
        except AttributeError:
            raise ValueError("no such perf method in %s: %s"
                             % (self.__class__, methodName))

    def setUp(self):
        "Hook method for setting up the perf fixture before exercising it."
        pass

    def tearDown(self):
        "Hook method for deconstructing the perf fixture after perfing it."
        pass

    def countPerfCases(self):
        return 1

    def defaultPerfResult(self):
        return PerfResult()

    def shortDescription(self):
        """Returns a one-line description of the perf, or None if no
        description has been provided.

        The default implementation of this method returns the first line
        of the specified perf method's docstring.
        """
        doc = self.__perfMethodDoc
        return doc and doc.split("\n")[0].strip() or None

    def id(self):
        return "%s.%s" % (self.__class__, self.__perfMethodName)

    def __str__(self):
        return "%s (%s)" % (self.__perfMethodName, self.__class__)

    def __repr__(self):
        return "<%s perfMethod=%s>" % \
               (self.__class__, self.__perfMethodName)

    def run(self, result=None):
        return self(result)

    def __call__(self, result=None):
        if result is None:
            result = self.defaultPerfResult()
        result.startPerf(self)
        perfMethod = getattr(self, self.__perfMethodName)
        try:
            self.setUp()

            # Returns either <value> or (<value>, <log>).
            retval = perfMethod()
            if isinstance(retval, tuple):
                value, log = retval
            else:
                value, log = retval, None
            result.addResult(self, value, log)

            self.tearDown()
        finally:
            result.stopPerf(self)

    def debug(self):
        """Run the perf without collecting errors in a PerfResult"""
        self.setUp()
        getattr(self, self.__perfMethodName)()
        self.tearDown()



class PerfSuite:
    """A perf suite is a composite perf consisting of a number of
    PerfCases.

    For use, create an instance of PerfSuite, then add perf case
    instances.  When all perfs have been added, the suite can be passed
    to a perf runner, such as TextPerfRunner. It will run the individual
    perf cases in the order in which they were added, aggregating the
    results. When subclassing, do not forget to call the base class
    constructor.
    """
    def __init__(self, perfs=()):
        self._perfs = []
        self.addPerfs(perfs)

    def __repr__(self):
        return "<%s perfs=%s>" % (self.__class__, self._perfs)

    __str__ = __repr__

    def countPerfCases(self):
        cases = 0
        for perf in self._perfs:
            cases = cases + perf.countPerfCases()
        return cases

    def addPerf(self, perf):
        self._perfs.append(perf)

    def addPerfs(self, perfs):
        for perf in perfs:
            self.addPerf(perf)

    def run(self, result):
        return self(result)

    def __call__(self, result):
        for perf in self._perfs:
            if result.shouldStop:
                break
            perf(result)
        return result

    def debug(self):
        """Run the perfs without collecting errors in a PerfResult"""
        for perf in self._perfs:
            perf.debug()


#---- Locating and loading perfs

class PerfLoader:
    """This class is responsible for loading perfs according to various
    criteria and returning them wrapped in a Perf
    """
    # Dev Note:
    # - Using a prefix of "perf_" instead of "perf" differs slight in
    #   spirit from unittest.py. This is more reminiscent of the "do_"
    #   prefix in cmd.py and suggested "test_" prefix usage for
    #   unittest.py.
    perfMethodPrefix = 'perf_'
    sortPerfMethodsUsing = cmp
    suiteClass = PerfSuite

    def loadPerfsFromPerfCase(self, perfCaseClass):
        """Return a suite of all perfs cases contained in perfCaseClass"""
        return self.suiteClass(map(perfCaseClass,
                                   self.getPerfCaseNames(perfCaseClass)))

    def loadPerfsFromModule(self, module):
        """Return a suite of all perfs cases contained in the given module"""
        perfs = []
        for name in dir(module):
            obj = getattr(module, name)
            if type(obj) == types.ClassType and issubclass(obj, PerfCase):
                perfs.append(self.loadPerfsFromPerfCase(obj))
        return self.suiteClass(perfs)

    def loadPerfsFromName(self, name, module=None):
        """Return a suite of all perfs cases given a string specifier.

        The name may resolve either to a module, a perf case class, a
        perf method within a perf case class, or a callable object which
        returns a PerfCase or PerfSuite instance.

        The method optionally resolves the names relative to a given module.
        """
        parts = name.split('.')
        if module is None:
            if not parts:
                raise ValueError, "incomplete perf name: %s" % name
            else:
                parts_copy = parts[:]
                while parts_copy:
                    try:
                        module = __import__('.'.join(parts_copy))
                        break
                    except ImportError:
                        del parts_copy[-1]
                        if not parts_copy: raise
                parts = parts[1:]
        obj = module
        for part in parts:
            obj = getattr(obj, part)

        if type(obj) == types.ModuleType:
            return self.loadPerfsFromModule(obj)
        elif type(obj) == types.ClassType and issubclass(obj, unitperf.PerfCase):
            return self.loadPerfsFromPerfCase(obj)
        elif type(obj) == types.UnboundMethodType:
            return obj.im_class(obj.__name__)
        elif callable(obj):
            perf = obj()
            if not isinstance(perf, PerfCase) and \
               not isinstance(perf, PerfSuite):
                raise ValueError("calling %s returned %s, not a perf"
                                 % (obj,perf))
            return perf
        else:
            raise ValueError("don't know how to make perf from: %s" % obj)

    def loadPerfsFromNames(self, names, module=None):
        """Return a suite of all perfs cases found using the given
        sequence of string specifiers. See 'loadPerfsFromName()'.
        """
        suites = []
        for name in names:
            suites.append(self.loadPerfsFromName(name, module))
        return self.suiteClass(suites)

    def getPerfCaseNames(self, perfCaseClass):
        """Return a sorted sequence of method names found within
        perfCaseClass
        """
        perfFnNames = filter(lambda n,p=self.perfMethodPrefix: n[:len(p)] == p,
                             dir(perfCaseClass))
        for baseclass in perfCaseClass.__bases__:
            for perfFnName in self.getPerfCaseNames(baseclass):
                if perfFnName not in perfFnNames:  # handle overridden methods
                    perfFnNames.append(perfFnName)
        if self.sortPerfMethodsUsing:
            perfFnNames.sort(self.sortPerfMethodsUsing)
        return perfFnNames


defaultPerfLoader = PerfLoader()



#---- Patches for old functions: these functions should be considered obsolete

def _makeLoader(prefix, sortUsing, suiteClass=None):
    loader = PerfLoader()
    loader.sortPerfMethodsUsing = sortUsing
    loader.perfMethodPrefix = prefix
    if suiteClass:
        loader.suiteClass = suiteClass
    return loader

def getPerfCaseNames(perfCaseClass, prefix, sortUsing=cmp):
    return _makeLoader(prefix, sortUsing).getPerfCaseNames(perfCaseClass)

def makeSuite(perfCaseClass, prefix='perf_', sortUsing=cmp,
              suiteClass=PerfSuite):
    loader = _makeLoader(prefix, sortUsing, suiteClass)
    return loader.loadPerfsFromPerfCase(perfCaseClass)

def findPerfCases(module, prefix='perf_', sortUsing=cmp,
                  suiteClass=PerfSuite):
    loader = _makeLoader(prefix, sortUsing, suiteClass)
    return loader.loadPerfsFromModule(module)



#---- Text UI

class _TextPerfResult(PerfResult):
    """A perf result class that can print formatted text results to a stream.

    Used by TextPerfRunner.
    """
    separator1 = '=' * 70
    separator2 = '-' * 70

    def __init__(self, stream, descriptions):
        PerfResult.__init__(self)
        self.stream = stream
        self.descriptions = descriptions

    def getDescription(self, perf):
        if self.descriptions:
            return perf.shortDescription() or str(perf)
        else:
            return str(perf)

    def startPerf(self, perf):
        PerfResult.startPerf(self, perf)
        self.stream.write(self.getDescription(perf))
        self.stream.write(" ... ")

    def addResult(self, perf, value, log=None):
        PerfResult.addResult(self, perf, value, log)
        self.stream.write("%s\n" % value)


class TextPerfRunner:
    """A perf runner class that displays results in textual form.

    It prints out the names of perfs as they are run, errors as they
    occur, and a summary of the results at the end of the perf run.
    """
    def __init__(self, stream=sys.stderr, descriptions=1):
        self.stream = stream
        self.descriptions = descriptions

    def _makeResult(self):
        return _TextPerfResult(self.stream, self.descriptions)

    def run(self, perf):
        "Run the given perf case or perf suite."
        result = self._makeResult()
        startTime = time.time()
        perf(result)
        stopTime = time.time()
        timeTaken = float(stopTime - startTime)
        self.stream.write(result.separator2+'\n')
        run = result.perfsRun
        self.stream.write("Ran %d perf metric%s in %.3fs\n"
                          % (run, run == 1 and "" or "s", timeTaken))
        self.stream.write("\n")
        return result


