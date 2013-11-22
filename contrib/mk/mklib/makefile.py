# Copyright (c) 2005-2007 ActiveState Software Ltd.
# Author:
#   Trent Mick (TrentM@ActiveState.com)

"""Makefile.py parsing/handling."""

import sys
import os
from os.path import dirname, join, isabs, normpath, splitext, basename
from glob import glob
from pprint import pprint

from mklib.common import log, MkError, IllegalMakefileError, \
                         relpath, canon_path_from_path
from mklib.path import path as Path #TODO: drop usage of? yes, remove str(path)'s too
from mklib.tasks import TaskType, FileType
from mklib.configuration import ConfigurationType



def find_makefile_path(allow_search=True):
    makefile_path = Path("Makefile.py")
    if makefile_path.exists():
        return makefile_path
    if allow_search:
        d = os.getcwd()
        while d != dirname(d):
            d = dirname(d)
            makefile_path = Path(join(d, "Makefile.py"))
            if makefile_path.exists():
                return makefile_path
        dirs_str = " or parent dirs"
    else:
        dirs_str = " dir"
    raise MkError("could not find `Makefile.py' in current%s" % dirs_str)


def include(makefile_path, ns=None):
    # Makefile loading places some state on the module at '_mk_*_'
    # attributes.
    f = sys._getframe(1)
    parent = f.f_globals["_mk_makefile_"]

    # If the included path is relative it must be relative to the
    # including Makefile.
    if not isabs(makefile_path):
        parent_makefile_dir = dirname(f.f_code.co_filename)
        makefile_path = normpath(join(relpath(parent_makefile_dir),
                                      makefile_path))

    ns_str = ns and " (ns=%r)" % ns or ""
    log.debug("include makefile `%s'%s", makefile_path, ns_str)

    #TODO: not sure what todo about config_file_path_override (defer)
    ns_list = (parent.ns or []) + (ns and [ns] or [])
    makefile = Makefile(makefile_path, parent.master, ns=ns_list,
                        parent=parent)
    parent.includes.append(makefile)


class Makefile(object):
    path = None
    master = None
    ns = None   # None or a list of namespace strings
    parent = None
    cfg = None
    doc = None

    def __init__(self, makefile_path, master, config_file_path_override=None,
                 ns=None, parent=None):
        self.path = makefile_path
        self.dir = dirname(makefile_path) or os.curdir # for convenience
        self.master = master
        self.config_file_path_override = config_file_path_override
        self.ns = ns
        self.parent = parent

        self.tasks = {} # <task-name> -> <task>
        self.files = {} # <abs-file-path>  ->  <file>
        self.includes = []
        self._load()

    def __repr__(self):
        ns_str = (self.ns 
                  and (" (ns=%s)" % ':'.join(self.ns))
                  or "")
        return "<Makefile `%s'%s>" % (self.path, ns_str)

    @property
    def nicepath(self):
        a = self.path
        r = relpath(self.path)
        if not sys.platform == "win32" and isabs(a):
            home = os.environ["HOME"]
            if a.startswith(home):
                #XXX:TODO: bug here for, e.g., "/home/jan" vs "/home/jane"
                a = "~" + a[len(home):]
        if len(r) < len(a):
            return r
        else:
            return a

    def define_configuration(self, cls, name, bases, dct):
        if self.cfg is not None:
            raise IllegalMakefileError(
                "more than one Configuration defined in `%s'"
                % self.path)
        self.cfg = cls(self, self.config_file_path_override)

    def define_task(self, cls, name, bases, dct):
        if name.startswith("_"):  # skip private task classes
            return
        if name in self.tasks:
            raise IllegalMakefileError(
                "conflicting definitions: Alias, Task or "
                "TaskGroup `%s' defined more than once" % name)
        self.tasks[name] = cls(self, self.cfg)

    def define_file(self, cls, name, bases, dct):
        path = dct.get("path", name)
        canon_path = canon_path_from_path(path, relto=self.dir)
        if canon_path in self.files:
            raise IllegalMakefileError(
                "conflicting file definitions: File `%s' "
                "defined more than once" % path)
        self.files[canon_path] = cls(path, self, self.cfg)

    def define_alias(self, cls, name, bases, dct):
        if name.startswith("_"):  # skip private task classes
            return
        if name in self.tasks:
            raise IllegalMakefileError(
                "conflicting definitions: Alias, Task or "
                "TaskGroup `%s' defined more than once" % name)
        self.tasks[name] = cls(self, self.cfg)

    def files_from_path(self, path):
        normed_path = normpath(join(self.dir, path))
        if "*" in path or "?" in path or "[" in path:
            normed_paths = glob(normed_path) or [normed_path]
            files = []
            for p in normed_paths:
                files += self.master.files.get(p)
        else:
            files = self.master.files.get(normed_path)
        return files

    def tasks_or_files_from_name(self, name):
        tasks = self.master.tasks.getns(self.ns, name)
        if tasks:
            return tasks
        return self.files_from_path(name)

    def _load(self):
        log.debug("reading `%s'", self.path)
        sys.path.insert(0, dirname(self.path))
        try:
            source = open(self.path).read()
            code = compile(source, self.path, 'exec')
            globs = {
                '__builtins__': sys.modules['__builtin__'],
                '__file__': str(self.path),
                '__name__': splitext(basename(self.path))[0],
                '_mk_makefile_': self,
                #TODO: is _mk_ns_ necessary?
                '_mk_ns_': self.ns,
            }
            mod = eval(code, globs)
        finally:
            sys.path.remove(dirname(self.path))

        self.doc = mod.__doc__
        default_tasks = [t for t in self.tasks.values() if t.default]
        if not default_tasks:
            self.default_task = None
        elif len(default_tasks) == 1:
            self.default_task = default_tasks[0]
        else:
            raise IllegalMakefileError("more than one default task: %s"
                                       % ', '.join(map(str, default_tasks)))


