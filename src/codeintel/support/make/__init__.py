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
# Author:
#   Trent Mick (TrentM@ActiveState.com)

"""A Python interpretation of GNU make."""

__revision__ = "$Id$"
__version_info__ = (0, 3, 0)
__version__ = '.'.join(map(str, __version_info__))

import os
from os.path import exists, abspath, dirname, normpath, expanduser
import sys
import getopt
import re
from pprint import pprint
import glob
import logging
import optparse
import time



#---- exceptions

class MakeError(Exception):
    pass

class MakeTargetError(MakeError):
    def __init__(self, err, target=None):
        self.err = err
        self.target = target
    def __str__(self):
        if self.target is not None:
            return "[%s] %s" % (self.target, self.err)
        else:
            return str(self.err)

class IllegalMakefileError(MakeError):
    """Semantic error in makefile.
    
    'path' is the path to the makefile.
    """
    def __init__(self, err, path=None):
        self.err = err
        self.path = path
    def __str__(self):
        if self.target is not None:
            return "%s: %s" % (self.path, self.err)
        else:
            return str(self.err)



#---- main functions

def default(func):
    """Decorator to mark a make_*() target as the default.
    
    Example:
        @make.default
        def make_foo(log, opts):
            #...
    """
    func.default = True
    return func

def makes(*outputs):
    """Decorator to specify output for a make_*() target.
    
    Example:
        @make.makes("foo.txt", "bar.txt")
        def make_foo(log, opts):
            #...
    """
    def decorate(f):
        if not hasattr(f, "outputs"):
            f.outputs = []
        f.outputs += [xpath(output) for output in outputs]
        return f
    return decorate

def dep(*deps):
    """Decorator to specify dependencies for a make_*() target.
    
    Example:
        @make.dep("eggs.txt", "bacon.txt")
        def make_breakfast(log, opts):
            #...
    """
    def decorate(f):
        if not hasattr(f, "deps"):
            f.deps = []
        f.deps += deps
        return f
    return decorate

def find_makefile_path(makefile_opt):
    #XXX Eventually might do the Cons-thang: walk up dir tree looking
    #    for Makefile.py.
    makefile_path = xpath(makefile_opt or "Makefile.py")
    if not exists(makefile_path):
        raise MakeError("could not file makefile: '%s'" % makefile_path)
    return makefile_path


class Maker(object):
    def __init__(self, makefile_path):
        self.module = self._load_makefile(makefile_path)
        self.path = makefile_path
        self.keep_going = True
        self._depth = 0     # log.debug indentation depth
        self.num_targets_made = 0

        self._process_makefile()

    def _load_makefile(self, makefile_path):
        sys.path.insert(0, dirname(abspath(makefile_path)))
        try:
            return _module_from_path(makefile_path)
        finally:
            del sys.path[0]

    def _process_makefile(self):
        func_from_target = {}
        for name, attr in self.module.__dict__.items():
            if name.startswith('make_'):
                func_from_target[ name[len('make_'):] ] = attr
        self.func_from_target = func_from_target

        default_targets = []
        for target, target_func in func_from_target.items():
            if hasattr(target_func, "default") and target_func.default:
                default_targets.append(target)
        if not default_targets:
            self.default_target = None
        elif len(default_targets) == 1:
            self.default_target = default_targets[0]
        else:
            raise IllegalMakefileError("more than one default target: %s"
                                       % ', '.join(default_targets))

    def get_deps(self, target):
        #XXX Where to properly handle no such target?
        target_func = self.func_from_target[target]
        if hasattr(target_func, "deps"):
            return target_func.deps
        else:
            return []

    def get_outputs(self, target):
        #XXX Where to properly handle no such target?
        target_func = self.func_from_target[target]
        if hasattr(target_func, "outputs"):
            return target_func.outputs
        else:
            return []

    def _debug(self, msg, *args):
        log.debug(' '*self._depth + msg, *args)

    def make(self, *targets):
        """Make the given targets.

        Returns (<num-made>, <num-failed>) where <num-made> only
        includes those that needed to be rebuilt.
        """
        if not targets: # Use the default target.
            if self.default_target:
                targets = [self.default_target]
            else:
                raise MakeError("no target given and no default target in '%s'"
                                % self.path)

        num_targets_made = 0
        num_targets_failed = 0
        for target in targets:
            self._debug("Considering target `%s'.", target)
            self._depth += 1

            # If any of this targets outputs do not exist, then we know for
            # sure that we need to remake it.
            outputs = self.get_outputs(target)
            nonexistant_outputs = [o for o in outputs if not exists(o)]
            for output in nonexistant_outputs:
                self._debug("Output `%s' of target `%s' does not exist.",
                            output, target)

            # Re-make any of this target's dependencies if necessary.
            deps = self.get_deps(target)
            if deps:
                self._depth += 1
                num_deps_remade, num_deps_failed = self.make(*deps)
                self._depth -= 1
            self._debug("Finished dependencies of target `%s'.", target)
            if deps and num_deps_failed:
                self._depth -= 1
                self._debug("Giving up on target `%s'", target)
                log.info("Target `%s' not remade because of errors.", target)
                continue

            # We need to remake this target if any of the following is true:
            # 1. It has no outputs (i.e. it is virtual).
            # 2. At least one of its outputs does not exist.
            # 3. Any of its dependencies were remade.
            # 4. It is older than any of its dependencies.
            #    Because a target can have multiple outputs (or none) this
            #    isn't so straightforward: if any of the outputs of this
            #    target is older than any of the outputs of any dependency.
            if not outputs:                                     # 1.
                need_to_remake = True
            elif nonexistant_outputs:                           # 2.
                need_to_remake = True
            elif deps and num_deps_remade:                      # 3.
                need_to_remake = True
            else:
                need_to_remake = False
                oldest_output_mtime = min([os.stat(o).st_mtime for o in outputs])
                for dep in deps:
                    yougest_dep_mtime = max(
                        [os.stat(o).st_mtime for o in self.get_outputs(dep)])
                    if yougest_dep_mtime > oldest_output_mtime: # 4.
                        word = "newer"
                        need_to_remake = True
                        # Optmization: We can stop processing here because
                        # we already know that we need_to_remake.  GNU make
                        # keeps going through (if debugging with '-d', at
                        # least).
                        if not log.isEnabledFor(logging.DEBUG):
                            break
                    else:
                        word = "older"
                    self._debug("Dependency `%s' is %s than target `%s'.",
                                dep, word, target)

            self._depth -= 1
            if need_to_remake:
                self._debug("Must remake target `%s'.", target)
                retval = self._do_make(target)
                if retval:
                    log.error("[%s] %s", target, retval)
                    self._debug("Failed to remake target `%s'.", target)
                    num_targets_failed += 1
                else:
                    self._debug("Successfully remade target `%s'.", target)
                    num_targets_made += 1
            else:
                self._debug("No need to remake target `%s'.", target)

        return (num_targets_made, num_targets_failed)

    def _do_make(self, target):
        """Run the function body for this target.

        How this method returns:
        - If the target function returns 0 (or None or False) then that
          value is returned.
        - If the target function returns a non-false value (typically an
          error string) and self.keep_going is false (i.e. '-k' was NOT
          used) then a MakeTargetError is raised. If self.keep_going is
          true then that return value is returned.
        - If the target function raises an exception, regardless of the
          value of self.keep_going the exception passes through.

        Callers should work with the return value rather than trapping
        any exceptions so that this function can properly deal with
        error handling as per the "-k" option.
        """
        target_func = self.func_from_target[target]
        log.target = target
        try:
            retval = target_func(self, log)
        finally:
            log.target = None
        if not retval:
            self.num_targets_made += 1
            return retval
        elif self.keep_going:
            return retval
        else:
            raise MakeTargetError(retval, target)



#---- internal support functions

def xpath(*parts):
    """Massage a Unix-like path into an appropriately native one."""
    if len(parts) == 1:
        path = parts[0]
    else:
        path = join(*parts)
    if sys.platform == "win32":
        path = path.replace('/', '\\')
    return normpath(expanduser(path))

# Recipe: module_from_path (1.0) in /Users/trentm/tm/recipes/cookbook
def _module_from_path(path):
    from os.path import dirname, basename, splitext
    import imp
    dir  = dirname(path) or os.curdir
    name = splitext(basename(path))[0]
    iinfo = imp.find_module(name, [dir])
    return imp.load_module(name, *iinfo)


# Recipe: run (0.5.3) in C:\trentm\tm\recipes\cookbook
_RUN_DEFAULT_LOGSTREAM = ("RUN", "DEFAULT", "LOGSTREAM")
def __run_log(logstream, msg, *args, **kwargs):
    if not logstream:
        pass
    elif logstream is _RUN_DEFAULT_LOGSTREAM:
        try:
            log
        except NameError:
            pass
        else:
            if hasattr(log, "debug"):
                log.debug(msg, *args, **kwargs)
    else:
        logstream(msg, *args, **kwargs)

def _run(cmd, logstream=_RUN_DEFAULT_LOGSTREAM):
    """Run the given command.

        "cmd" is the command to run
        "logstream" is an optional logging stream on which to log the 
            command. If None, no logging is done. If unspecifed, this 
            looks for a Logger instance named 'log' and logs the command 
            on log.debug().

    Raises OSError is the command returns a non-zero exit status.
    """
    __run_log(logstream, "running '%s'", cmd)
    retval = os.system(cmd)
    if hasattr(os, "WEXITSTATUS"):
        status = os.WEXITSTATUS(retval)
    else:
        status = retval
    if status:
        #TODO: add std OSError attributes or pick more approp. exception
        raise OSError("error running '%s': %r" % (cmd, status))

def _run_in_dir(cmd, cwd, logstream=_RUN_DEFAULT_LOGSTREAM):
    """Run the given command in the given working directory.

        "cmd" is the command to run
        "cwd" is the directory in which the commmand is run.
        "logstream" is an optional logging stream on which to log the 
            command. If None, no logging is done. If unspecifed, this 
            looks for a Logger instance named 'log' and logs the command 
            on log.debug().

    Raises OSError is the command returns a non-zero exit status.
    """
    old_dir = os.getcwd()
    try:
        os.chdir(cwd)
        __run_log(logstream, "running '%s' in '%s'", cmd, cwd)
        _run(cmd, logstream=None)
    finally:
        os.chdir(old_dir)


# Based on Recipe: pretty_logging (0.1) in C:\trentm\tm\recipes\cookbook
class _MakeLogFormatter(logging.Formatter):
    """make-specific logging output.

    - lowercase logging level names
    - no "info" for normal info level
    - when logging from a target include the target name in the message:
      set the "target" attribute to the current target name.

    XXX The "target" stuff won't work for -j: multiple sync target
        building. Solution: could isolate via thread ID.
    """
    def get_fmt(self, record):
        fmt = "%(name)s: "
        target = getattr(record, "target", None)
        if target:
            fmt += "[%(target)s] "
        if record.levelno != logging.INFO:
            fmt += "%(levelname)s: " 
        fmt += "%(message)s"
        return fmt
    def format(self, record):
        record.levelname = record.levelname.lower() # uppercase is ugly
        #XXX This is a non-threadsafe HACK. Really the base Formatter
        #    class should provide a hook accessor for the _fmt
        #    attribute. *Could* add a lock guard here (overkill?).
        _saved_fmt = self._fmt
        self._fmt = self.get_fmt(record)
        try:
            return logging.Formatter.format(self, record)
        finally:
            self._fmt = _saved_fmt

class _MakeLogger(logging.Logger):
    """A Logger that passes on its "target" attr to created LogRecord's
    for the benefit of the handling Formatter. 
    """
    target = None
    def makeRecord(self, *args):
        record = logging.Logger.makeRecord(self, *args)
        record.target = self.target
        return record

def _setup_logging():
    logging.setLoggerClass(_MakeLogger)
    hdlr = logging.StreamHandler()
    fmtr = _MakeLogFormatter()
    hdlr.setFormatter(fmtr)
    logging.root.addHandler(hdlr)
    global log
    log = logging.getLogger("make")
    log.setLevel(logging.INFO)


#---- mainline

def main(argv=sys.argv):
    _setup_logging()

    usage = "usage: %prog [TARGETS...]"
    version = "%prog "+__version__
    parser = optparse.OptionParser(prog="make", usage=usage, version=version,
                                   description=__doc__)
    parser.add_option("-v", "--verbose", dest="log_level",
        action="store_const", const=logging.DEBUG,
        help="more verbose output")
    parser.add_option("-q", "--quiet", dest="log_level",
        action="store_const", const=logging.WARNING,
        help="quieter output")
    parser.add_option("-f", dest="makefile_path",
        help="specify the makefile (defaults to Makefile.py in the "
             "current directory)")
##    parser.add_option("-G", "--generate-makefile", action="store_true",
##        help="generate a GNU Makefile from the given Makefile.py")
    parser.set_defaults(log_level=logging.INFO)
    opts, targets = parser.parse_args()
    logging.getLogger("make").setLevel(opts.log_level)

    makefile_path = find_makefile_path(opts.makefile_path)
    maker = Maker(makefile_path)
    before = time.time()
    maker.make(*targets)
    after = time.time()
    #XXX Should use the state object to keep running total of *all*
    #    targets re-made. The top-level number here is useless.
    log.info("%d targets made in %.2fs.", maker.num_targets_made, after-before)


if __name__ == "__main__":
    try:
        retval = main(sys.argv)
    except KeyboardInterrupt:
        sys.exit(1)
    except SystemExit:
        raise
    except:
        exc_info = sys.exc_info()
        if hasattr(exc_info[0], "__name__"):
            #log.error("%s: %s", exc_info[0].__name__, exc_info[1])
            log.error(exc_info[1])
        else:  # string exception
            log.error(exc_info[0])
        if log.isEnabledFor(logging.DEBUG):
            import traceback
            print
            traceback.print_exception(*exc_info)
        sys.exit(1)
    else:
        sys.exit(retval)


