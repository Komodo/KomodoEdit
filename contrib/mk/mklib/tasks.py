# Copyright (c) 2005-2007 ActiveState Software Ltd.

"""Task classes."""

import sys
import os
from os.path import exists, dirname, abspath, normpath, join
import logging
import types

from mklib.common import *



class TaskType(type):
    """Metaclass for Task's to catch definitions in Makefiles and handle
    accordingly.
    """
    def __init__(cls, name, bases, dct):
        super(TaskType, cls).__init__(name, bases, dct)
        if dct["__module__"] != __name__:
            frame = sys._getframe(1)
            try:
                makefile = frame.f_globals["_mk_makefile_"]
            except KeyError:
                # This isn't defined in a makefile. Don't do anything
                # special with it.
                return

            # Normalizing descriptors for <task>.deps and <task>.results
            # and <taskgroup>.pairs.
            if issubclass(cls, TaskGroup):
                if dct.get("results"):
                    raise IllegalMakefileError(
                        "TaskGroup %s (in %s) has a `results' attribute. "
                        "This is not allowed on TaskGroup classes. "
                        "Results are defined by the output of `pairs'." 
                        % (cls.__name__, makefile.path))
                if dct.get("make"):
                    raise IllegalMakefileError(
                        "TaskGroup %s (in %s) has a `make' attribute. "
                        "This is not allowed on TaskGroup classes. "
                        % (cls.__name__, makefile.path))

                cls.pairs = PairsListAccessor("pairs",
                    getattr(cls, "pairs", None))
                cls.deps = TaskGroupDepsListAccessor("deps",
                    getattr(cls, "deps", None))
                cls.results = TaskGroupResultsListAccessor()
            elif issubclass(cls, Alias):
                if dct.get("results"):
                    raise IllegalMakefileError(
                        "Alias %s (in %s) has a `results' attribute. "
                        "This is not allowed on Alias classes. "
                        % (cls.__name__, makefile.path))
                cls.deps = TaskOrFileListAccessor("deps",
                    getattr(cls, "deps", None))
            else:
                cls.deps = TaskOrFileListAccessor("deps",
                    getattr(cls, "deps", None))
                cls.results = FileListAccessor("results",
                    getattr(cls, "results", None))

            # Defining "default" on a Task is only good for that class
            # -- *not* for subclasses.
            cls.default = dct.get("default", False)

            # Register this on the Makefile.
            makefile.define_task(cls, name, bases, dct)
            if issubclass(cls, TaskGroup):
                log_makefile_defn("TaskGroup", name, frame)
            else:
                log_makefile_defn("Task", name, frame)


class Task(object):
    """Base class for a Makefile.py task.
    Typically a specific task is a subclass of Task. For example:

        from mklib.tasks import Task
        class install(Task):
            deps = ["build"]
            def results(self):
                yield os.path.join(self.cfg.prefix, "bin", "foo")
            def make(self):
                ...
    
    See mk's main documentation for more details.
    """
    __metaclass__ = TaskType

    default = False  # set to true to set this as the default task

    def __init__(self, makefile, cfg):
        self.name = self.__class__.__name__
        self.makefile = makefile
        self.dir = makefile.dir # for convenience
        if makefile.ns:
            self.nsname = "%s:%s" % (':'.join(makefile.ns), self.name)
        else:
            self.nsname = self.name
        self.cfg = cfg
        self.log = logging.getLogger("mk.task." + self.name)

    def __repr__(self):
        if not self.results:
            return "<Task '%s' (virtual)>" % self.nsname
        else:
            return "<Task '%s'>" % self.nsname
    def __str__(self):
        return "task `%s'" % self.nsname
    def id(self):
        # Use for tracking by the TaskMaster
        return ("task", self.nsname)

    @property
    def name_tuple(self):
        """A tuple of the task namespace and name suitable as a sorting key."""
        if self.makefile.ns:
            rv = (tuple(self.makefile.ns), self.name)
        else:
            rv = (None, self.name)
        return rv

    #TODO: is this necessary? Not really anymore.
    def doc(self):
        """Return documentation for this task, if any."""
        return self.__doc__

    # The presence of a make()' implementation on a Task class
    # indicates if there is anything to execute to do this task. For
    # example, typically an "all" task will not have a "make" method.
    # Instead it will just have a number of dependencies.
    #def make(self):
    #    ...

    #TODO: Add this when/if add support for Task sub-classes.
    #def is_complete(self):
    #    """Is this task complete.
    #    
    #    This is *not* meant to reflect the state of `self.results' for
    #    this task, just the task itself. This means that for the base
    #    class "Task" (a virtual task) this is always False.
    #    """


class Alias(Task):
    """A special kind of Task to provide a short name for one or more
    tasks.
    
        class stage_one(Alias):
            deps = ["this_task", "and_that_task"]
    
    This allows for some task dependency trees that don't artificially
    create situations where tasks are re-built unnecessarily.
    Consider this set of tasks:
    
        ...
        class stage_docs(Task):
            deps = ["docs_subtask_a", "docs_subtask_b"]
        class stage_app(Task):
            deps = ["app_subtask_a", "app_subtask_b"]
        class installer(Task):
            deps = ["stage_docs", "stage_app"]
            results = ["app-1.0.0.dmg"]
            def make(self):
                # build the installer package...
    
    The problem here is that 'stage_docs' and 'stage_app' are "virtual
    tasks". (Virtual tasks are tasks with no 'results'. Like phony targets
    in GNU Makefiles, virtual tasks are always "out-of-date".)
    Because of that running:
    
        mk installer
    
    will *always* cause the installer build steps to be executed
    ("installer" depends on virtual tasks, hence it will always be
    out-of-date).
    
    Making the virtual tasks aliases solves this:

        class stage_docs(Alias):
            deps = ["docs_subtask_a", "docs_subtask_b"]
        class stage_app(Alias):
            deps = ["app_subtask_a", "app_subtask_b"]
    
    Now running `mk installer` will only rebuild if one of the subtasks
    is out-of-date.
    """
    def __repr__(self):
        return "<Alias '%s'>" % self.nsname
    def __str__(self):
        return "alias `%s'" % self.nsname
    def id(self):
        # Use for tracking by the TaskMaster
        return ("alias", self.nsname)


class TaskGroup(Task):
    """Base class for a Makefile.py task group. E.g.:

        from mklib.tasks import TaskGroup
        from mklib import sh
        class move_source_files(TaskGroup):
            def pairs(self):
                for name in os.listdir("src"):
                    src = join("src", name)
                    dst = join("build", name)
                    yield src, dst
            def make_pair(self, src, dst)
                sh.cp(src, dst)
    
    See mk's main documentation for more details.
    """
    default = False  # set to true to set this as the default task

    def __repr__(self):
        return "<TaskGroup '%s'>" % self.nsname
    def __str__(self):
        return "task group `%s'" % self.nsname

    #TODO: is this necessary? Not really anymore.
    def doc(self):
        return self.__doc__

    #TODO: START HERE:
    # - add special handling in TaskMaster for TaskGroups to call
    #   make_pair as necessary
    def pairs(self):
        raise NotImplementedError("sub-classes must implement pairs()")
    def make_pair(self, dep, result):
        raise NotImplementedError("sub-classes must implement make_pair()")



class FileType(type):
    """Metaclass for File's to catch definitions in Makefiles and handle
    accordingly.
    """
    def __init__(cls, name, bases, dct):
        super(FileType, cls).__init__(name, bases, dct)
        if dct["__module__"] != __name__:
            # Normalizing descriptor for <file>.deps.
            # String *results* are assumed to be file result paths
            # (hence are transformed into File instances), because
            # a base-Task instance -- i.e. a virtual task -- doesn't make
            # sense: you can't have a "virtual" result.
            cls.deps = FileListAccessor("deps",
                getattr(cls, "deps", None))

            # Register this on the Makefile.
            frame = sys._getframe(1)
            makefile = frame.f_globals["_mk_makefile_"]
            makefile.define_file(cls, name, bases, dct)
            log_makefile_defn("File", dct["path"], frame)


class File(object):
    __metaclass__ = FileType

    def __init__(self, path, makefile=None, cfg=None):
        # Use absolute paths to guard against process cwd changes.
        path = makefile and normpath(join(makefile.dir, path)) or path
        self.path = abspath(path)
        self.makefile = makefile
        self.dir = makefile and makefile.dir or None
        self.cfg = cfg
    def __repr__(self):
        return "<File '%s'>" % self.path
    def __str__(self):
        return "file `%s'" % self.nicepath
    def id(self):
        # Use for tracking by the TaskMaster
        return ("file", self.path)

    @property
    def relpath(self):
        return relpath(self.path)

    @property
    def nicepath(self):
        r = self.relpath
        a = self.path
        if not sys.platform == "win32":
            home = os.environ["HOME"]
            if a.startswith(home):
                #XXX:TODO: bug here for, e.g., "/home/jan" vs "/home/jane"
                a = "~" + a[len(home):]
        if len(r) < len(a):
            return r
        else:
            return a

    @property
    def deps(self):
        """By default a file has no deps."""
        # Dev Note: Using a property here to ensure separate instances
        # don't share a single list instance.
        return []

    def exists(self):
        return exists(self.path)
    def mtime(self):
        return os.stat(self.path).st_mtime



#---- descriptors for some Task and File attributes

class TaskOrFileListAccessor(object):
    """Descriptor for `<task>.deps`.

    This wraps the definition of the attribute on the class (it can
    be a list, a method that results a list, or a generator) so that
    accessing this attribute always results in a list of Task or File
    instances.
    """
    def __init__(self, attrname, defn):
        self._attrname = attrname
        self._defn = defn
        self._cache = None

    def _get_items(self, obj, objtype):
        if not self._defn:
            items = []
        elif isinstance(self._defn, (types.FunctionType, types.MethodType)):
            items = self._defn(obj) # is either a generator or result list
        else:
            items = self._defn

        # If the string matches a defined Task then it becomes that
        # Task instance, else it becomes a File.
        rv = []
        for item in items:
            if item is None:
                continue
            if isinstance(item, (File, Task)):
                rv.append(item)
            else:
                rv += obj.makefile.tasks_or_files_from_name(item)
        return rv
    
    def __get__(self, obj, objtype):
        if isinstance(self._defn, basestring):
            raise IllegalMakefileError(
                # '%ss': cheating, I know __str__() endswith an apostrophe
                "%ss `%s' attribute is a string, it must "
                "be a list (or a method that returns a list)"
                % (obj, self._attrname))
        if self._cache is None:
            self._cache = self._get_items(obj, objtype)

        return self._cache


class TaskGroupDepsListAccessor(TaskOrFileListAccessor):
    """Descriptor for `<taskgroup>.deps`."""
    def _get_items(self, obj, objtype):
        # A TaskGroup's deps are any possible items mentioned in
        # a 'deps' attribute ...
        rv = TaskOrFileListAccessor._get_items(self, obj, objtype)

        # ... plus the deps from the individual dep/result "pairs".
        rv += [dep for dep, res in obj.pairs]
        return rv

class TaskGroupResultsListAccessor(object):
    """Descriptor for `<taskgroup>.results`."""
    _cache = None

    def __get__(self, obj, objtype):
        if self._cache is None:
            self._cache = [res for dep, res in obj.pairs]
        return self._cache


class FileListAccessor(object):
    """Descriptor for `<task>.results` or `<file>.deps`.

    This wraps the definition of the attribute on the class (it can
    be a list, a method that results a list, or a generator) so that
    accessing this attribute always results in a list of File instances.

    Strings in `<task>.results` and `<file>.deps` are assumed to be file
    result paths (hence are transformed into File instances), because a
    base-Task instance -- i.e. a virtual task -- doesn't make sense: you
    can't have a "virtual" result.
    """
    def __init__(self, attrname, defn):
        self._attrname = attrname
        self._defn = defn
        self._cache = None

    def __get__(self, obj, objtype):
        # This `return None` early out is an attempt to avoid this
        # problem when defining a task from another task where the base
        # task-class defines a "def results()" generator. I don't
        # *really* understand what is going on here.
        #
        #-----
        # Traceback
        #   ...
        #   File "support/metricstasks.py", line 299, in <module>
        #     class aslogs_downloads(_FooTask):
        #   File "/home/trentm/as/mk/mklib/tasks.py", line 62, in __init__
        #     getattr(cls, "results", None))
        #   File "/home/trentm/as/mk/mklib/tasks.py", line 406, in __get__
        #     items = self._defn(obj) #  is either a generator or result list
        # TypeError: Error when calling the metaclass bases
        #     unbound method results() must be called with _FooTask instance as first argument (got NoneType instance instead)
        #-----
        if obj is None:
            return None

        if isinstance(self._defn, basestring):
            raise IllegalMakefileError(
                # '%ss': cheating, I know __str__() endswith an apostrophe
                "%ss `%s' attribute is a string, it must "
                "be a list (or a method that returns a list)"
                % (obj, self._attrname))
        if self._cache is None:
            if not self._defn:
                items = []
            elif isinstance(self._defn, (types.FunctionType, types.MethodType)):
                items = self._defn(obj) # is either a generator or result list
            else:
                items = self._defn

            # String *deps* can be virtual. If the string matches a defined
            # Task then it becomes that Task instance, else it becomes
            # a file task.
            self._cache = []
            for item in items:
                assert not isinstance(item, Task)
                if isinstance(item, File):
                    self._cache.append(item)
                else:
                    self._cache += obj.makefile.files_from_path(item)

        return self._cache

class PairsListAccessor(object):
    """Descriptor for `<taskgroup>.pairs`.

    A "pair" for a task group is 2-tuple representing one
    dependency/result part of the group:
        (<dependency-path>, <result-path>)
    
    Note: Typically each part of the tuple will be a single path, but
    (TODO) multiple deps and/or results should be allowed (e.g. a .java
    file producing multiple .class files).

    This wraps the definition of the attribute on the class (it can
    be a list, a method that results a list, or a generator) so that
    accessing this attribute always results in a list of 2-tuples:
        (<File-instance-for-dependency-path>,
         <File-instance-for-result-path>)
    """
    def __init__(self, attrname, defn):
        self._attrname = attrname
        self._defn = defn
        self._cache = None
    
    def __get__(self, obj, objtype):
        if isinstance(self._defn, basestring):
            raise IllegalMakefileError(
                # '%ss': cheating, I know __str__() endswith an apostrophe
                "%ss `%s' attribute is a string, it must "
                "be a list (or a method that returns a list)"
                % (obj, self._attrname))
        if self._cache is None:
            if not self._defn:
                items = []
            elif isinstance(self._defn, (types.FunctionType, types.MethodType)):
                items = self._defn(obj) # is either a generator or result list
            else:
                items = self._defn

            # If the string matches a defined Task then it becomes that
            # Task instance, else it becomes a File.
            self._cache = []
            for dep, res in items:
                #TODO: Current limitation on single or multiple files
                #      here. Deal with that.
                #TODO: should *tasks* be allowed for deps here?
                assert "*" not in dep and "?" not in dep
                dep_file = (isinstance(dep, File)
                            and dep
                            or obj.makefile.files_from_path(dep)[0])
                assert "*" not in res and "?" not in res
                res_file = (isinstance(res, File)
                            and res
                            or obj.makefile.files_from_path(res)[0])
                self._cache.append( (dep_file, res_file) )

        return self._cache

