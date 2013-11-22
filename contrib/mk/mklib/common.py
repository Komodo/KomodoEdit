# Copyright (c) 2005-2007 ActiveState Software Ltd.

"""Shared bits of mklib."""

__all__ = ["log",
           "MkError", "MkUsageError", "MkTaskError",
           "IllegalMakefileError",
           "canon_path_from_path", "log_makefile_defn",
           "relpath",]

import os
import sys
from os.path import normcase, normpath, abspath, isabs, join
import logging



#---- logging

log = logging.getLogger("mk")



#---- exceptions

class MkError(Exception):
    pass

class MkUsageError(MkError):
    """An error resulting from usage."""
    pass

class MkTaskError(MkError):
    """Indicates an error running a task body.

    The "task" attribute is the name of the task in which the error
    occured.
    """
    def __init__(self, err, task=None):
        self.err = err
        self.task = task
    def __str__(self):
        if self.task is not None:
            return "[%s] %s" % (self.task, self.err)
        else:
            return str(self.err)

class IllegalMakefileError(MkError):
    """Semantic error in Makefile.
    
    'path' is the path to the Makefile.
    """
    def __init__(self, err, path=None):
        self.err = err
        self.path = path
    def __str__(self):
        if self.path is not None:
            return "%s: %s" % (self.path, self.err)
        else:
            return str(self.err)



#---- utility stuff

def canon_path_from_path(path, relto=None):
    """Path canonicalization so we can easily compare them."""
    if isabs(path):
        pass
    elif relto is None:
        path = abspath(path)
    else:
        path = abspath(join(relto, path))
    return normcase(normpath(path))

def log_makefile_defn(type, name, frame):
    at_str = ""
    ns_str = ""
    at_str = " at %s#%d" % (frame.f_code.co_filename, frame.f_lineno)
    ns = frame.f_locals.get("_mk_makefile_", None).ns
    if ns:
        ns_str = ":".join(ns) + ":"
    log.debug("define %s `%s%s'%s", type, ns_str, name, at_str)


# Recipe: relpath (0.2)
def relpath(path, relto=None):
    """Relativize the given path to another (relto).

    "relto" indicates a directory to which to make "path" relative.
        It default to the cwd if not specified.
    """
    if not os.path.isabs(path):
        path = os.path.abspath(path)
    if relto is None:
        relto = os.getcwd()
    else:
        relto = os.path.abspath(relto)

    if sys.platform.startswith("win"):
        def _equal(a, b): return a.lower() == b.lower()
    else:
        def _equal(a, b): return a == b

    pathDrive, pathRemainder = os.path.splitdrive(path)
    if not pathDrive:
        pathDrive = os.path.splitdrive(os.getcwd())[0]
    relToDrive, relToRemainder = os.path.splitdrive(relto)
    if not _equal(pathDrive, relToDrive):
        # Which is better: raise an exception or return ""?
        return ""
        #raise OSError("Cannot make '%s' relative to '%s'. They are on "\
        #              "different drives." % (path, relto))

    pathParts = splitall(pathRemainder)[1:] # drop the leading root dir
    relToParts = splitall(relToRemainder)[1:] # drop the leading root dir
    #print "_relpath: pathPaths=%s" % pathParts
    #print "_relpath: relToPaths=%s" % relToParts
    for pathPart, relToPart in zip(pathParts, relToParts):
        if _equal(pathPart, relToPart):
            # drop the leading common dirs
            del pathParts[0]
            del relToParts[0]
    #print "_relpath: pathParts=%s" % pathParts
    #print "_relpath: relToParts=%s" % relToParts
    # Relative path: walk up from "relto" dir and walk down "path".
    relParts = [os.curdir] + [os.pardir]*len(relToParts) + pathParts
    #print "_relpath: relParts=%s" % relParts
    relPath = os.path.normpath( os.path.join(*relParts) )
    return relPath

# Recipe: splitall (0.2)
def splitall(path):
    r"""Split the given path into all constituent parts.

    Often, it's useful to process parts of paths more generically than
    os.path.split(), for example if you want to walk up a directory.
    This recipe splits a path into each piece which corresponds to a
    mount point, directory name, or file.  A few test cases make it
    clear:
        >>> splitall('')
        []
        >>> splitall('a/b/c')
        ['a', 'b', 'c']
        >>> splitall('/a/b/c/')
        ['/', 'a', 'b', 'c']
        >>> splitall('/')
        ['/']
        >>> splitall('C:\\a\\b')
        ['C:\\', 'a', 'b']
        >>> splitall('C:\\a\\')
        ['C:\\', 'a']

    (From the Python Cookbook, Files section, Recipe 99.)
    """
    allparts = []
    while 1:
        parts = os.path.split(path)
        if parts[0] == path:  # sentinel for absolute paths
            allparts.insert(0, parts[0])
            break
        elif parts[1] == path: # sentinel for relative paths
            allparts.insert(0, parts[1])
            break
        else:
            path = parts[0]
            allparts.insert(0, parts[1])
    allparts = [p for p in allparts if p] # drop empty strings 
    return allparts

