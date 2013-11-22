# Copyright (c) 2005-2007 ActiveState Software Ltd.

import sys
from pprint import pprint
import os
from os.path import normcase, normpath, abspath
import logging
import traceback
import types
import re
import time
from fnmatch import fnmatch
from operator import attrgetter

from mklib.common import *
from mklib.makefile import Makefile
from mklib.path import path as Path
from mklib.tasks import Task, File, Alias
from mklib.configuration import ConfigurationType


class TaskMaster(object):
    def __init__(self, options, makefile_path,
                 config_file_path_override=None, force=False):
        """
        ...
        @param force {boolean} can be set to True to force re-making
            tasks even if they are up-to-date.
        """
        self.options = options
        self.force = force

        #TODO: Put these (and "_run_data") in a ._reset() and call it.
        #      However, re-entrancy support is low prio.
        self._depth = 0     # log.debug indentation depth
        self.num_tasks_done = 0

        self.makefile = Makefile(makefile_path, self,
                                 config_file_path_override)
        self.tasks = _TaskList(self.makefile)
        self.files = _FileList(self.makefile)

    def _debug(self, msg, *args):
        log.debug(' '*self._depth + msg, *args)

    def list_tasks(self, filter=None):
        """Prints a list of tasks.

        @param filter is one of None (no filtering), a regex (filter on
            task names) or a string (do task selection identical to
            executable tasks).

        By default this prints only those tasks that are documented
        (have a doc string) or are a default task. If a filter is given,
        this extra filtering is skipped.
        """
        verbose = log.level < logging.INFO
        
        # Determine which tasks to list.
        if filter is None:
            tasks = self.tasks
            if not verbose:
                tasks = list(self.tasks.common())
            else:
                tasks = self.tasks
        elif hasattr(filter, "search"):
            tasks = [t for t in self.tasks if filter.search(t.nsname)]
        else:
            assert isinstance(filter, basestring)
            tasks = self.tasks.get(filter)

        if not tasks:
            return

        # List them.
        WIDTH = 78
        name_width = max([len(t.nsname) for t in tasks])
        for task in sorted(tasks, key=attrgetter("name_tuple")):
            doc = task.doc()
            if task.default and not task.makefile.ns:
                if doc:
                    doc = "(default) " + doc
                else:
                    doc = "(default)"
            if not doc:
                print "mk "+task.nsname
            else:
                # 7 == len('mk ' + '  # ')
                summary_width = WIDTH - name_width - 7
                summary = _first_paragraph(doc, True)
                if len(summary) > summary_width:
                    summary = summary[:summary_width-3] + "..."
                template = "mk %%-%ds  # %%s" % name_width
                print template % (task.nsname, summary)
            if verbose:
                for dep in task.deps:
                    print "    dep %s" % dep
                if hasattr(task, "results"):  # Alias' do not have results
                    for result in task.results:
                        print "    result %s" % result

    def default_makefile_doc(self):
        return "`%s' has no default target.\n\n${common_task_list}\n" \
               % self.makefile.nicepath

    def _do_default(self):
        doc = self.makefile.doc or self.default_makefile_doc()
        sys.stdout.write(self._preprocess_text(doc))

    def _preprocess_text(self, text):
        """Preprocess the following vars in the given text (generally a
        Makefile doc string). 
        
        ${common_task_list}
            A formatted table of documented tasks similar to that shown
            for `mk -T'.

        Note: these are similar to Python 2.4's string.Template
        interpolation but not quite.

        Returns the processed text.
        """
        preprocessors = {
            "${common_task_list}":    self._preprocess_common_task_list,
        }
        for marker, preprocessor in preprocessors.items():
            if marker in text:
                text = preprocessor(text)
        return text

    def _preprocess_common_task_list(self, text):
        MARKER = "${common_task_list}"
        indent, indent_width = _get_indent(MARKER, text)

        lines = ["Common tasks:"]
        common_tasks = list(self.tasks.common())
        if common_tasks:
            WIDTH = 78 - 4 - indent_width  # indented an extra 4 spaces
            name_width = max([len(t.nsname) for t in common_tasks])
            for task in sorted(common_tasks, key=attrgetter("name_tuple")):
                doc = task.doc()
                if task.default and not task.makefile.ns:
                    if doc:
                        doc = "(default) " + doc
                    else:
                        doc = "(default)"
                if not doc:
                    lines.append("    mk "+task.nsname)
                else:
                    # 7 == len('mk ' + '  # ')
                    summary_width = WIDTH - name_width - 7
                    summary = _first_paragraph(doc, True)
                    if len(summary) > summary_width:
                        summary = summary[:summary_width-3] + "..."
                    template = "    mk %%-%ds  # %%s" % name_width
                    lines.append(template % (task.nsname, summary))
        elif self.tasks:
            lines.append("    (none, use `mk -Tv' to show all tasks)")
        else:
            lines.append("    (none)")

        block = indent + ('\n' + indent).join(lines) + '\n'
        suffix = _get_trailing_whitespace(MARKER, text)
        text = text.replace(indent+MARKER+suffix, block, 1)
        return text

    _task_from_result_path_cache = None
    def _task_that_builds_path(self, path):
        """Return a task that builds the given file.
        
        Returns None if there is no such task.
        """
        if self._task_from_result_path_cache is None:
            #TODO: This caching should be done on a per-Makefile basis
            #      and lazily. I.e. try to avoid having to run every
            #      dynamic task.results() in the universe everytime
            #      'mk' is run.
            cache = self._task_from_result_path_cache = {}
            for task in self.tasks:
                if isinstance(task, Alias):
                    continue
                for result in task.results:
                    cpath = canon_path_from_path(result.path)
                    if cpath in cache:
                        raise IllegalMakefileError(
                            "multiple targets build the same file: "
                            "both %s and %s build `%s'"
                            % (cache[cpath], task, relpath(result.path)))
                    cache[canon_path_from_path(result.path)] = task

        canon_path = canon_path_from_path(path)
        return self._task_from_result_path_cache.get(canon_path)

    def tasks_or_files_from_name(self, name):
        """Returns either a list of tasks matching `name' or
        a list of File instances (usually just one) for that path.
        """
        tasks = self.tasks.get(name)
        if tasks:
            return tasks
        return self.files.get(name)

    def make(self, *target_names):
        # "target_names" is a list of target names (strings).

        if not target_names: # Use the default task.
            targets = self.tasks.get('')
            if not targets:
                return self._do_default()
        else:
            targets = []
            for name in target_names:
                targets += self.tasks_or_files_from_name(name)
        
        run_data = _RunData()
        self._do_make(targets, run_data, first_pass=True)

    def _do_make(self, targets, run_data, parent_target=None,
                 first_pass=False):
        """Ensure the given targets are up to date.

        @param targets is a list of File or Task instances.

        Dev Notes:
        - it is an error for more than one Task to have the same File
          result (see 'synerr_2' test)

        TODO: think about how Rules would work in here
        """
        targets_done = []
        targets_skipped = []
        targets_failed = []

        for target in _resolve_aliases(targets):
            assert isinstance(target, (Task, File))
            need_to_redo = False
            because = None # Minimal prose explanation of why need to redo.

            if target.id() in run_data.considered:
                self._debug("Pruning %s.", target)

            else:
                run_data.considered.add(target.id())
                self._debug("Considering %s.", target)
                self._depth += 1

                # Determine if we'll need to redo this target regardless of
                # the state of its dependencies.
                if isinstance(target, File):
                    if not target.exists():
                        self._debug("%s does not exist."
                                    % str(target).capitalize())
                        need_to_redo = True
                        because = "%s does not exist" % target
                else:
                    for result in target.results:
                        assert isinstance(result, File), \
                            "result for target %r is not a File instance: %r" \
                            % (target, result)
                        if not result.exists():
                            self._debug("Result %s of %s does not exist.",
                                        result, target)
                            need_to_redo = True
                            because = "result %s does not exist" % result

                # Redo any dependencies, if necessary.
                deps = list(_resolve_aliases(target.deps))
                if isinstance(target, File):
                    task = self._task_that_builds_path(target.path)
                    if task is not None:
                        deps += list(_resolve_aliases(task.deps))
                else:
                    task = None
                    for result in target.results:
                        deps += list(_resolve_aliases(result.deps))
                if deps:
                    self._depth += 1
                    deps_done, deps_skipped, deps_failed \
                        = self._do_make(deps, run_data, parent_target=target)
                    self._depth -= 1
                self._debug("Finished dependencies of %s.", target)
                if deps and deps_failed:
                    self._depth -= 1
                    self._debug("Giving up on %s.", target)
                    log.info("%s not re-done because of errors.",
                             str(target).capitalize())
                    targets_failed.append(target)
                    continue

                # We need to redo this target if any of the following is true:
                # 0. It is a File that doesn't exist or a Task with results
                #    that don't exist. (Handled above.)
                # 1. We're forcing a redo.
                # 2. It is a virtual task (i.e. a Task with no results)
                # 3. Any of its dependencies were re-done.
                # 4. It is out of date w.r.t. its dependencies.
                if need_to_redo:            # 0.
                    pass
                elif self.force and not (   # 1.
                     isinstance(target, File) and task is None):
                    need_to_redo = True
                    because = "'force' option is set"
                elif isinstance(target, Task) and not target.results:   # 2.
                    self._debug("%s is a virtual task.",
                                str(target).capitalize())
                    need_to_redo = True
                    because = "%s is a virtual task" % target
                elif not deps:
                    need_to_redo = False
                elif deps_done:             # 3.
                    need_to_redo = True
                    because = "deps were redone"
                else:                       # 4.
                    need_to_redo = self.is_out_of_date(target, task, deps,
                                                       run_data)
                    if need_to_redo:
                        because = "out-of-date w.r.t. deps"

                self._depth -= 1
                if need_to_redo:
                    if isinstance(target, File):
                        if task is None:
                            parent_str = ""
                            if parent_target:
                                parent_str = ", needed by %s" % parent_target
                            raise MkError("no task to make %s%s"
                                          % (target, parent_str))
                        task_str = "%s for %s" % (task, target)
                    else:
                        assert isinstance(target, Task)
                        task = target
                        task_str = str(task)

                    self._debug("Must redo %s (because %s).", task_str,
                                because)
                    err_str = self._execute_task(task)
                    if err_str:
                        log.error("[%s] %s", task.name, err_str)
                        self._debug("Failed to do %s.", task_str)
                        targets_failed.append(task)
                        run_data.status_from_task_nsname[task.nsname] = "redone (failed)"
                    else:
                        self._debug("Successfully did %s.", task_str)
                        targets_done.append(task)
                        run_data.status_from_task_nsname[task.nsname] = "redone"
                    
                else:
                    targets_skipped.append(target)
                    if isinstance(target, Task):
                        run_data.status_from_task_nsname[target.nsname] = "up-to-date"
                    self._debug("No need to redo %s.", target)

            if first_pass and not need_to_redo:
                if task and not hasattr(task, "make"):
                    log.info("Nothing to be done for %s.", task)
                else:
                    log.info("%s is up to date.", str(target).capitalize())


        return (targets_done, targets_skipped, targets_failed)


    def is_out_of_date(self, target, task, deps, run_data):
        """Return True iff this task is out of date w.r.t. it
        dependencies.

        @param target {Task|File} is the thing to check
        @param task {Task} is the Task instance that builds 'target' if
            target is a File. If 'target' is a Task, this is None.
        @param deps {list} is a list of Task or File dependencies of 'target'.
        
        What is out-of-date?
        ====================
        
        A task is out of date **iff any of its dependencies have changed
        since the last time it was done.**
        
        Practically this is calculated as follows:
        1. mtime-style:
           If any of the results of the task is older than any of the
           results of any dependency. 
        2. checksum-style (not yet supported, TODO):
           If the checksum of any result of any dependency has changed
           from the value cached for it when the task was last run.

           Dev Notes:
            cache:
                task-id -> {dependency-id: checksum, ...},
                ...
                (This has to store only for one level.)
        """
        # This currently implements the "mtime-style" check.
        # Assumption: all "results" for all tasks are always File's.
        out_of_date = False
        
        # Get the oldest mtime of all output files for this target.
        if isinstance(target, File):
            oldest_target_file_mtime = target.mtime()
            oldest_target_file = target
        else:
            oldest_target_file_mtime, oldest_target_file \
                = sorted((r.mtime(), r) for r in target.results)[0]

        # Compare against the results for each dependency.
        debug = log.isEnabledFor(logging.DEBUG)
        for dep in deps:
            if isinstance(dep, File):
                youngest_dep_file_mtime = dep.mtime()
                youngest_dep_file = dep
            elif not dep.results: # i.e. this is virtual Task
                youngest_dep_file = None
            else: 
                youngest_dep_file_mtime, youngest_dep_file \
                    = sorted((r.mtime(), r) for r in dep.results)[-1]

            if youngest_dep_file is None: # dep is a virtual Task
                assert run_data.status_from_task_nsname[dep.nsname] != "up-to-date"
                out_of_date = True
            elif youngest_dep_file_mtime > oldest_target_file_mtime:
                word = "newer"
                out_of_date = True
            else:
                # If they have the exact same mtime, the target is
                # considered up to date.
                word = "older"

            if debug:
                if youngest_dep_file is None:
                    # Example output:
                    #   Dependency file `foo.txt' (1234) is older than target \
                    #       file `bar.txt' (1234).
                    #   Dependency task `foo' was remade.
                    self._debug("Dependency %s was %s.", dep,
                                run_data.status_from_task_nsname[dep.nsname])
                else:
                    # Example output:
                    #   Dependency file `foo.txt' (1234) is older than target \
                    #       file `bar.txt' (1234).
                    #   Dependency task `foo' (result file `foo.txt', 1234) is \
                    #       older than target task `bar' (result file `bar.txt', 1234).
                    dep_details = time.asctime(time.localtime(youngest_dep_file_mtime))
                    if youngest_dep_file is not dep:
                        dep_details = "result %s, %s" % (youngest_dep_file, dep_details)
                    target_details = time.asctime(time.localtime(oldest_target_file_mtime))
                    if oldest_target_file is not target:
                        target_details = "result %s, %s" % (oldest_target_file, target_details)
                    self._debug(
                        "Dependency %s (%s) is %s than target %s (%s).",
                        dep, dep_details, word, target, target_details)

            # Optmization: We can stop processing here because we already
            # know that we need_to_redo. GNU make keeps going through (if
            # debugging with '-d', at least).
            if out_of_date and not debug:
                break

        return out_of_date

    def _execute_task(self, task):
        """Run the function body for this task.

        A task indicates an error by raising an exception
        The return value is ignored.

        How this method returns:
        - If the task function raises an exception and keep_going is
          false (i.e. '-k' was NOT used) then the exception is passed
          through.  If keep_going is true then a (string) summary of the
          error is returned.
        - Otherwise (the task was successfully run), None is returned.

        Callers should work with the return value rather than trapping
        any exceptions so that this function can properly deal with
        error handling as per the "-k" option.
        """
        if not hasattr(task, "make"):
            return
        if self.options.dry_run:
            log.debug("mk task `%s' (dry-run)", task.name)
            return
        try:
            task.make()
        except (SystemExit, KeyboardInterrupt):
            raise
        except:
            exc_class, exc, tb = sys.exc_info()
            if self.options.keep_going:
                tb_path, tb_lineno, tb_func = traceback.extract_tb(tb)[-1][:3]
                return "%s (%s:%s in %s)" % (exc, tb_path, tb_lineno, tb_func)
            elif exc is None: # string exception
                raise
            else:
                exc.mk_task = task # stash this away for error reporting
                raise


#---- internal support stuff


def _resolve_aliases(tasks_or_files):
    for task_or_file in tasks_or_files:
        if isinstance(task_or_file, Alias):
            for t_or_f in _resolve_aliases(task_or_file.deps):
                yield t_or_f
        else:
            yield task_or_file

class _RunData(object):
    def __init__(self):
        self.considered = set()
        # Track task status for this run where "status" is one
        # of the following strings:
        #   redone              needed to remake and succeeded
        #   redone (failed)     needed to remake and failed (relevant if -f)
        #   up-to-date          did not need to remake
        self.status_from_task_nsname = {}

class _FileList(list):
    """Wrapper for `<taskmaster>.files`.
   
    Files (instances of class File) can be explicitly defined in Makefile's
    (e.g., to define dependencies). Commonly, however, File instances are
    implicitly created for paths mentioned as targets on the command-line
    and in Task.results and Task.deps.

    This wrapper handles the search for, implicit creation of and caching of
    File instances via a basic interface:

    files.get(name)     -> list of File instances for that path
       This is almost always a single instance, but it *is* possible to
       explicitly define a File for the same path in two separate
       Makefiles.
    """
    def __init__(self, makefile):
        self._files_from_canon_path = {}
        self._load_makefile(makefile)
        #pprint(self._files_from_canon_path, width=1)

    def _load_makefile(self, makefile):
        for canon_path, file in makefile.files.items():
            if canon_path not in self._files_from_canon_path:
                self._files_from_canon_path[canon_path] = []
            self._files_from_canon_path[canon_path].append(file)
        for include in makefile.includes:
            self._load_makefile(include)

    def get(self, path):
        """Get a list of File instances (almost always just one) for
        the given path.

        @param path {str}
        """
        canon_path = canon_path_from_path(path)
        if canon_path not in self._files_from_canon_path:
            self._files_from_canon_path[canon_path] = [File(path)]
        return self._files_from_canon_path[canon_path]


class _TaskList(list):
    """Wrapper for `<taskmaster>.tasks`.
   
    The tasks are defined on the `taskmaster.makefile` tree. This wrapper
    provides a simpler (and hopefully faster) mechanism for getting and
    working with these tasks. Basically this is a list of tasks with some
    additional methods for looking up tasks by name.

    for t in tasks          -> iterate through all tasks
    tasks.get(name)         -> list of tasks matching 'name'
    tasks.getns(ns, name)   -> list of tasks matching 'name' relative to 'ns'
    tasks.common()          -> iterate over "common" tasks

    TODO: eventually do master._task_that_builds_path(self, path) via:
            tasks.that_builds_path(path)

    """
    def __init__(self, makefile):
        self._table = (
            # This data structure is used to assist .get() and .getns().
            {},  # Sub-namespaces: <namespace-string> -> (<sub-namespaces>, <makefiles>)
            []   # Makefiles with this namespace.
        )
        self._load_makefile(makefile, self._table)
        #pprint(self._table, width=1)

    def _load_makefile(self, makefile, table):
        sub_namespaces, makefiles = table
        makefiles.append(makefile)

        for task in makefile.tasks.values():
            self.append(task)

        for include in makefile.includes:
            inc_table = table
            if include.ns:
                ns_tail = include.ns[-1]
                if ns_tail not in sub_namespaces:
                    inc_table = sub_namespaces[ns_tail] = ({}, [])
            self._load_makefile(include, inc_table)

    def _gen_makefiles(self, ns_list=None):
        """Yield all makefiles.
        
        @param ns_list {list} is an optional list of namespace strings.
            If given, then yielded makefiles are just those under and
            including that namespace.
        """
        if ns_list:
            table = self._table
            try:
                for ns_str in ns_list:
                    table = table[0][ns_str]
            except KeyError, ex:
                log.debug("no such task namespace: %s", ex)
                tables = []
            else:
                tables = [table]
        else:
            tables = [self._table]
        while tables:
            sub_namespaces, makefiles = tables.pop(0)
            for makefile in makefiles:
                yield makefile
            tables += sub_namespaces.values()

    def common(self):
        """Generate the common tasks.
        
        What constitutes a "common" task is subjective. Here are
        our rules:
        - Default tasks in the default namespace are "common"
        - Documented tasks (i.e. they have docstring) in the default
          namespace are "common"
        - The default task(s) in a first-level namespace (e.g. 'a:' but
          not 'a:b:') is "common". Here the idea is that this default
          task can be invoked by just giving its namespace:
            mk the_ns
        """
        for makefile in self._table[1]:
            for task in makefile.tasks.values():
                if task.default or task.doc():
                    yield task
        for ns, table in self._table[0].items():
            for makefile in table[1]:
                if makefile.default_task:
                    yield makefile.default_task

    def get(self, name):
        """Get the tasks matching the given name.

        @param name is a task name or pattern to match against.

        Examples of supported name patterns:

        get('a:foo')    -> tasks named 'foo' in 'a' namespace
        get('*:foo')    -> tasks named 'foo' in all namespaces
        get('foo')      -> tasks named 'foo' in default namespace
                           plus default task(s) in 'foo' namespace (if any)
        get(':foo')     -> tasks named 'foo' in default namespace
        get('a:')       -> default task(s) in 'a' namespace (if any)
        get('')         -> default task(s) in the default namespace

        get('a:*:foo')  -> tasks named 'foo' in all namespaces under
                           and including 'a'
            Necessary to support usage of "*:foo" in task deps and not
            have accidents with included Makefiles.
        """
        # Quick abort for path names.
        if os.sep in name or '.' in name or (os.altsep and os.altsep in name):
            return []

        #log.debug("get tasks matching %r", name)

        # Normalize the name.
        if name == ":":
            name = ""
        elif name.startswith(':') and name.count(':') > 1:
            # ':a:foo' -> 'a:foo'
            # The leading ':' is only meaningful with out a namespace,
            # to distinguish ':foo' from 'foo'.
            name = name[1:]

        # Do the lookup.
        tasks = []
        if name == "":
            for makefile in self._table[1]:
                if makefile.default_task:
                    tasks.append(makefile.default_task)

        elif name.startswith(':'):
            # get(':foo')     -> tasks named 'foo' in default namespace
            tname = name[1:]
            for makefile in self._table[1]:
                if tname in makefile.tasks:
                    tasks.append(makefile.tasks[tname])

        elif name.endswith(':'):
            # get('a:')       -> default task in 'a' namespace
            table = self._table
            try:
                for ns in name[:-1].split(':'):
                    table = table[0][ns]
            except KeyError, ex:
                log.debug("no such task namespace: %s", ex)
            else:
                for makefile in table[1]:
                    if makefile.default_task:
                        tasks.append(makefile.default_task)

        elif ':' not in name:
            # get('foo')      -> tasks named 'foo' in default namespace
            #                    plus default task in 'foo' namespace
            for makefile in self._table[1]:
                if name in makefile.tasks:
                    tasks.append(makefile.tasks[name])
            if name in self._table[0]:
                for makefile in self._table[0][name][1]:
                    if makefile.default_task:
                        tasks.append(makefile.default_task)

        elif '*' in name:
            # get('*:foo')    -> tasks named 'foo' in all namespaces
            # get('a:*:foo')  -> tasks named 'foo' in all namespaces under
            #                    and including 'a'
            ns_str, tname = name.rsplit(':', 1)

            if ns_str.endswith("*"):
                ns_list = ns_str.split(':')[:-1] or None
                for makefile in self._gen_makefiles(ns_list):
                    if tname in makefile.tasks:
                        tasks.append(makefile.tasks[tname])
            else:
                raise MkError("invalid task query name: %r" % name)

        else:
            # get('a:foo')    -> tasks named 'foo' in 'a' namespace
            ns_str, tname = name.rsplit(':', 1)

            table = self._table
            for ns in ns_str.split(':'):
                if ns in table[0]:
                    table = table[0][ns]
                else:
                    break
            else:
                for makefile in table[1]:
                    if tname in makefile.tasks:
                        tasks.append(makefile.tasks[tname])

        return tasks

    def getns(self, ns, name):
        """Get the tasks matching `name` relative to the given namespace
        list (ns).

        @param ns {list} is a list of namespace strings or None
        @param name {string} is a task name/pattern (see .get())
        """
        if ns:
            ns_str = ':'.join(ns) + ':'
            if name.startswith(':'):
                name = name[1:]
            name = ns_str + name
        return self.get(name)



def _get_indent(marker, s, tab_width=8):
    """_get_indent(marker, s, tab_width=8) ->
        (<indentation-of-'marker'>, <indentation-width>)"""
    # Figure out how much the marker is indented.
    INDENT_CHARS = tuple(' \t')
    start = s.index(marker)
    i = start
    while i > 0:
        if s[i-1] not in INDENT_CHARS:
            break
        i -= 1
    indent = s[i:start]
    indent_width = 0
    for ch in indent:
        if ch == ' ':
            indent_width += 1
        elif ch == '\t':
            indent_width += tab_width - (indent_width % tab_width)
    return indent, indent_width

def _get_trailing_whitespace(marker, s):
    """Return the whitespace content trailing the given 'marker' in string 's',
    up to and including a newline.
    """
    suffix = ''
    start = s.index(marker) + len(marker)
    i = start
    while i < len(s):
        if s[i] in ' \t':
            suffix += s[i]
        elif s[i] in '\r\n':
            suffix += s[i]
            if s[i] == '\r' and i+1 < len(s) and s[i+1] == '\n':
                suffix += s[i+1]
            break
        else:
            break
        i += 1
    return suffix

# Recipe: first_paragraph (1.0.1) in /home/trentm/tm/recipes/cookbook
def _first_paragraph(text, join_lines=False):
    """Return the first paragraph of the given text."""
    para = re.split(r"\n[ \t]+\n", text.lstrip(), 1)[0]
    if join_lines:
        lines = [line.strip() for line in  para.splitlines(0)]
        para = ' '.join(lines)
    return para

