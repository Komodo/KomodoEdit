#!/usr/bin/env python
# Copyright (c) 2005-2007 ActiveState Software Inc.

"""Perform tasks defined in a Makefile.py in the current or parent
directories.
"""

# The primary usage of this module is for command-line usage. The "mk"
# tool calls "main()" here.
#
#     from mklib import runner
#     runner.main()
# 
# There is also a "mk()" function here for less command-line oriented
# running (it doesn't setup logging, it doesn't call sys.exit). Currently
# it is being used for creating doctests in the test area. Typical usage
# might be:
# 
#     >>> from mklib import runner
#     >>> runner.setup_logging()
#     >>> runner.mk(['', 'some_task_name'])
# 
# 
# Notes on logging levels and verbosity
# -------------------------------------
# 
# How loud `mk` is depends on these options (the last one given wins):
#     (none given)        default verbosity (logging.INFO level)
#     -v, --verbose       more verbose (logging.INFO-1 level)
#     -q, --quiet         less verbose (logging.WARN level)
#     -d, --debug         debugging output (logging.DEBUG level)
# 
# Full tracebacks on errors are shown on the command-line with -d|--debug.
# '-v|--verbose' is useful for some commands that have normal and more
# verbose output modes (e.g. `mk --tasks` will show more information with
# '--verbose').

import os
from os.path import exists, dirname, abspath, join, basename
import sys
import re
from pprint import pprint
import glob
import logging
import optparse
import time
import traceback

from mklib.common import *
from mklib.makefile import find_makefile_path
from mklib.taskmaster import TaskMaster
import mklib



#---- internal support functions

# Recipe: regex_from_encoded_pattern (1.0)
def _regex_from_encoded_pattern(s):
    """'foo'    -> re.compile(re.escape('foo'))
       '/foo/'  -> re.compile('foo')
       '/foo/i' -> re.compile('foo', re.I)
    """
    if s.startswith('/') and s.rfind('/') != 0:
        # Parse it: /PATTERN/FLAGS
        idx = s.rfind('/')
        pattern, flags_str = s[1:idx], s[idx+1:]
        flag_from_char = {
            "i": re.IGNORECASE,
            "l": re.LOCALE,
            "s": re.DOTALL,
            "m": re.MULTILINE,
            "u": re.UNICODE,
        }
        flags = 0
        for char in flags_str:
            try:
                flags |= flag_from_char[char]
            except KeyError:
                raise ValueError("unsupported regex flag: '%s' in '%s' "
                                 "(must be one of '%s')"
                                 % (char, s, ''.join(flag_from_char.keys())))
        return re.compile(s[1:idx], flags)
    else: # not an encoded regex
        return re.compile(re.escape(s))

# Based on Recipe: pretty_logging (0.1)
class _MkLogFormatter(logging.Formatter):
    """mk-specific logging output.

    - lowercase logging level names
    - no "info" for normal info level
    - when logging from a task include the task name in the message:
      set the "task" attribute to the current task name.

    XXX The "task" stuff won't work for -j: multiple sync task
        building. Solution: could isolate via thread ID.
    """
    def get_fmt(self, record):
        fmt = "%(name)s: "
        task = getattr(record, "task", None)
        if task:
            fmt += "[%(task)s] "
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

class _MkTaskFilter(logging.Filter):
    prefix = "mk.task."
    prefix_len = len("mk.task.")
    def filter(self, record):
        if record.name.startswith(self.prefix):
            record.task = record.name[self.prefix_len:]
            record.name = "mk"
        return 1

def setup_logging(stream=None):
    """Do logging setup:

    1. We want a prettier default format:
            mk: level: ...
       Spacing. Lower case. Skip " level:" if INFO-level. 

    2. We want the task name in there if this a "mk.task.foo" logger:
            mk: [foo] level: ...
    """
    hdlr = logging.StreamHandler(stream)
    fmtr = _MkLogFormatter()
    hdlr.addFilter(_MkTaskFilter())
    hdlr.setFormatter(fmtr)
    logging.root.addHandler(hdlr)


def _optparse_zero_or_one_arg(option, opt_str, value, parser):
    """Add optparse option callback that will accept one or zero args.

    An arg is only consumed if (1) one is available and (2) it doesn't
    look like an option. Use this callback as follows:

        parser.add_option("-x", ..., action="callback",
            callback=_optparse_zero_or_one_arg, dest="blah")

    Specifying "dest" is necessary (getting auto-gleaning from the
    option strings is messy).

    After parsing, 'opts.blah' will be:
        None        option was not specified
        True        option was specified, no argument
        <string>    option was specified, the value is the argument string
    """
    value = True
    rargs = parser.rargs
    if parser.rargs:
        arg = parser.rargs[0]
        # Stop if we hit an arg like "--foo", "-a", "-fx", "--file=f",
        # etc.  Note that this also stops on "-3" or "-3.0", so if
        # your option takes numeric values, you will need to handle
        # this.
        if ((arg[:2] == "--" and len(arg) >= 2) or
            (arg[:1] == "-" and len(arg) > 1 and arg[1] != "-")):
            pass
        else:
            value = arg
            del parser.rargs[0]
    setattr(parser.values, option.dest, value)



#---- mainline

class _CleanHelpOptionParser(optparse.OptionParser):
    """Just get the OptionParser to not screw up the description when
    printing -h|--help output.
    """
    def format_description(self, formatter):
        return self.get_description()


def mk(argv=sys.argv, doc=None):
    usage = "usage: %prog [-f makefile] {options} tasks..."
    version = "%prog "+mklib.__version__
    doc = doc or __doc__
    if not doc.endswith("\n"):
        doc += "\n"
    # TODO: Switch to _NoReflowFormatter (see svn_add_ignore.py)
    parser = _CleanHelpOptionParser(prog="mk", usage=usage,
                                    version=version,
                                    description=doc or __doc__)

    # Verbosity options.
    parser.add_option("-q", "--quiet", dest="log_level",
        action="store_const", const=logging.WARNING,
        help="quieter output")
    parser.add_option("-v", "--verbose", dest="log_level",
        action="store_const", const=logging.INFO-1,
        help="more verbose output")
    parser.add_option("-d", "--debug", dest="log_level",
        action="store_const", const=logging.DEBUG,
        help="verbose debugging output")

    parser.add_option("--start", action="store_true",
        help="create a new starter 'Makefile.py' in the current directory")

    # Other options (we're somewhat following make's and rake's leads).
    parser.add_option("-f", "--makefile", dest="makefile_path",
        metavar="PATH", help="use the given Makefile.py")
    parser.add_option("-c", "--config",
        dest="config_file_path_override", metavar="PATH",
        help="override the default config file")
    # `mk -Tv` provides dep info as per `rake -P`.
    parser.add_option("-T", "--tasks", action="callback",
        callback=_optparse_zero_or_one_arg, dest="list_tasks",
        help="list tasks with a description (optional arg is a filter "
             "string), use --verbose for more detail")
    parser.add_option("-n", "--dry-run", action="store_true",
        help="dry-run, don't *execute* any tasks (use with -v to "
             "trace how tasks are executed)")
    parser.add_option("-N", "--nosearch", action="store_true",
        help="do not search in parent dirs for 'Makefile.py'")
    parser.add_option("-k", "--keep-going", action="store_true",
        help="keep going as far as possible after an error")
    parser.add_option("-F", "--force", action="store_true",
        help="force redo of tasks, even if up-to-date")

    parser.set_defaults(log_level=logging.INFO,
                        config_file_path_override=None,
                        force=False, no_lookup=False,
                        start=False)
    opts, tasks = parser.parse_args(argv[1:])
    log.setLevel(opts.log_level)

    if opts.start:
        makefile_path = "Makefile.py"
        if exists(makefile_path):
            raise MkError("cannot create starter Makefile: `%s' exists"
                          % makefile_path)
        template_path = join(dirname(__file__), "Makefile.py.template")
        template = open(template_path, 'r').read()
        project_name = basename(os.getcwd()) or None
        if project_name:
            template = template.replace("PROJECT_NAME", project_name)
        fout = open(makefile_path, 'w')
        try:
            fout.write(template)
        finally:
            fout.close()
        log.info("`%s' starter created (Try `mk hello`.)", makefile_path)
        return

    if opts.config_file_path_override is not None \
       and not exists(opts.config_file_path_override):
        raise MkError("config file does not exist: `%s'"
                        % opts.config_file_path_override)
    makefile_path = opts.makefile_path \
        or find_makefile_path(allow_search=not opts.nosearch)
    master = TaskMaster(opts, makefile_path,
                        opts.config_file_path_override, force=opts.force)

    if opts.list_tasks is not None:
        if opts.list_tasks is True:
            filter = None
        elif opts.list_tasks.startswith('/'):
            filter = _regex_from_encoded_pattern(opts.list_tasks)
        else:
            filter = opts.list_tasks
        master.list_tasks(filter)
    else:
        before = time.time()
        master.make(*tasks)
        after = time.time()
        ##XXX Should use the state object to keep running total of *all*
        ##    tasks re-done. The top-level number here is useless.
        #log.info("%d tasks done in %.2fs.", master.num_tasks_done, 
        #         after - before)


def main(argv=sys.argv, doc=None):
    """Main command-line entry point for 'mk' tool.

    "argv" (optional, default sys.argv) is the command line args array
    "doc" (optional) is a description for help output for the Makefile.py.
    """
    # Handle hidden 'mk --configurelib-path' option to ease deployment
    # of 'mk'. With this option and the following snippet, users need
    # only get 'mk' running (typically by putting the "mk/bin" dir on
    # their PATH) and they are good to go:
    #
    # try:
    #     import configurelib
    # except ImportError:
    #     configurelib_path = os.open("mk --configurelib-path").read().strip()
    #     sys.path.insert(0, configurelib_path)
    #     import configurelib
    #     del configurelib_path
    if "--configurelib-path" in argv:
        print join(dirname(dirname(abspath(__file__))))
        return 0
    
    setup_logging(sys.stdout)
    try:
        retval = mk(argv, doc)
    except KeyboardInterrupt:
        sys.exit(1)
    except SystemExit:
        raise
    except:
        exc_info = sys.exc_info()
        if hasattr(exc_info[0], "__name__"):
            exc_class, exc, tb = exc_info
            if issubclass(exc_class, MkUsageError):
                log.error(str(exc_info[1]))
            else:
                task = hasattr(exc, "mk_task") and exc.mk_task or None
                prefix = task and ("[%s] " % task.name) or ""

                exc_str = str(exc_info[1])
                sep = ('\n' in exc_str and '\n' or ' ')
                
                where_str = ""
                tb_path, tb_lineno, tb_func = traceback.extract_tb(tb)[-1][:3]
                if not tb_path.startswith(dirname(__file__)+os.sep):
                    in_str = (tb_func != "<module>"
                              and " in %s" % tb_func
                              or "")
                    where_str = "%s(%s:%s%s)" \
                                % (sep, tb_path, tb_lineno, in_str)

                log.error("%s%s%s", prefix, exc_str, where_str)
        else:  # string exception
            log.error(exc_info[0])
        if log.isEnabledFor(logging.INFO-1):
            print
            traceback.print_exception(*exc_info)
        sys.exit(1)
    else:
        sys.exit(retval)

if __name__ == "__main__":
    main()

