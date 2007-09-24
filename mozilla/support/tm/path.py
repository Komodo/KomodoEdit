#!python
# Portions copyright (c) 2002-2003 Trent Mick
# 
# Various pieces from:
# - David Ascher (for the idea of class path)
# - submissions by Trent Mick and Tim Peters to the Python Cookbook
#

"""Some useful stuff for working with file paths.

    splitall(path)              splits a path into all of its dir components
    commonprefix([path1, ...])  a better os.path.commonprefix that will
                                only split on dir components
    relpath(path, relto=None)   make the path relative to the given (or
                                current) path

    class path(str)             a string subclass to represent a path
"""
# TODO:
#   - a class upath for unicode paths
#   - get class path to override == using os.samefile and
#     case-insensitive comparision as appropriate

import os
import sys


#---- globals

_version_ = (0, 3, 0)


#---- internal support routines

def _unique(s):
    """Return a list of the elements in s, in arbitrary order, but without
    duplicates.

    (From the Python Cookbook, Algorithms, Recipe 4.)
    """

    # get the special case of an empty s out of the way, very rapidly
    n = len(s)
    if n == 0:
        return []

    # Try using a dict first, as that's the fastest and will usually work.
    u = {}
    try:
        for x in s:
            u[x] = 1
    except TypeError:
        del u  # move on to the next method
    else:
        return u.keys()

    # Since we can't hash all elements, try sorting, to bring equal items
    # together and weed them out in a single pass.
    try:
        t = list(s)
        t.sort()
    except TypeError:
        del t  # move on to the next method
    else:
        assert n > 0
        last = t[0]
        lasti = i = 1
        while i < n:
            if t[i] != last:
                t[lasti] = last = t[i]
                lasti += 1
            i += 1
        return t[:lasti]

    # Brute force is all that's left.
    u = []
    for x in s:
        if x not in u:
            u.append(x)
    return u



#---- exported methods and classes

def splitall(path):
    r"""Return list of all split directory parts.

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


def commonprefix(paths):
    """An os.path.commonprefix() that splits only on path separators.
    
    It returns the common path prefix of the given paths or None, if there
    is no such common prefix.
        >>> commonprefix(["C:\\trentm\\apps", "C:\\foo"])
        "C:\\"
        >>> commonprefix(["/trentm/apps/bar", "/trentm/apps/baa"])
        "/trentm/apps"
        >>> commonprefix(["/trentm/apps", "/trentm/foo",
                          "/trentm/bar/spam/eggs"])
        "/trentm"
    """
    if not paths:
        return None
    #if sys.platform.startswith("win"):
    #    # Case-insensitive comparison on Windows.
    #    paths = [path.lower() for path in paths]
    splitpaths = [splitall(path) for path in paths]
    commonprefix = []
    for set in zip(*splitpaths):
        # This path element is part of the common prefix if it is the same
        # for every give path.
        elem = set[0]
        if sys.platform.startswith("win"):
            # Case-insensitive comparison on Windows.
            set = [p.lower() for p in set]
        if len(_unique(set)) == 1:
            commonprefix.append(elem)
        else:
            break
    if commonprefix:
        retval = os.path.join(*commonprefix)
    else:
        retval = None
    #print "commonprefix(%r) == %r" % (paths, retval)
    return retval


def relpath(path, relto=None):
    """Return a relative path of the given path.

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


class path(str):
    # Adapted from the Python Cookbook, Files section, Recipe 100.
    """A subclass of Python strings for manipulating paths.

    A path object does for the os.path module what string methods did
    for the string module (in Python 2.0) plus a little bit more:
    list-like semantics based on path parts rather than characters. Path
    objects, like strings, are immutable.

    Some of the things you can do:
        >>> root = path(sys.prefix)
        >>> root
        'C:\\Python22'
        >>> sitepkgs = root / 'Lib' / 'site-packages'
        >>> sitepkgs
        'C:\\Python22\\Lib\\site-packages'
        >>> libdir = sitepkgs / '..'
        >>> libdir
        'C:\\Python22\\Lib\\site-packages\\..'
        >>> libdir.norm()
        'C:\\Python22\\Lib'
        >>> libdir.isdir()
        1
        >>> sitepkgs[:-1]
        'C:\\Python22\\Lib'

    """
    #XXX s/_translate/_translation/g
    _translate = { '.': os.curdir, '..': os.pardir }
    _caseInsensitive = sys.platform.startswith("win")

    def __new__(cls, *args):
        """Accept various contruction calls:
            path()            ->  ''
            path("a/b")       ->  'a/b'
            path("a", "b")    ->  'a/b'
            path(["a", "b"])  ->  'a/b'
            path(("a", "b"))  ->  'a/b'
        """
        if len(args) == 0:
            result = str.__new__(cls, "")
        elif len(args) == 1 and isinstance(args[0], (tuple, list)):
            result = str.__new__(cls, os.path.join(*args[0]))
        else:
            for arg in args:
                if not isinstance(arg, (str, unicode)):
                    raise TypeError("illegal arguments for 'path' object "\
                                    "construction: %r" % (args,))
            result = str.__new__(cls, os.path.join(*args))
        result.parts = splitall(str(result))
        return result
    def __str__(self):
        return str.__str__(self)
    def __div__(self, other):
        other = self._translate.get(other, other)
        return path( os.path.join(str(self), str(other)) )
    def __rdiv__(self, other):
        other = self._translate.get(other, other)
        return path( os.path.join(str(other), str(self)) )
    def __len__(self):
        return len(self.parts)
    def __getslice__(self, start, stop):
        # Cannot just ignore this deprecated method in favour of
        # __getitem__ because (guessing here) str.__getslice__ gets in
        # the way.
        return path( os.path.join(*self.parts[start:stop]) )
    def __getitem__(self, key):
        # Still not properly supporting extended slices here (XXX is
        # this even a Py2.2 feature?).
        return path( self.parts[key] )
    def __eq__(self, other):
        if hasattr(os.path, "samefile") and\
           os.path.samefile(str(self), str(other)):
            return 0
        else:
            #XXX Will not properly handle LONGNAME == SHORTNAME on Windows.
            normself  = os.path.normpath(str(self))
            normother = os.path.normpath(str(other))
            if self._caseInsensitive:
                normself  = normself.lower()
                normother = normother.lower()
            return str.__eq__(normself, normother)
    #XXX Figure out how to override ==.
    #def __cmp__(self, other):
    #    #print "XXX cmp(self=%r, other=%r)" % (str(self), str(other))
    #    if hasattr(os.path, "samefile"):
    #        if os.path.samefile(str(self), str(other)):
    #            return 0
    #        else:
    #            return cmp(str(self), str(other))
    #    elif self._caseInsensitive:
    #        #XXX Will not properly handle LONGNAME == SHORTNAME on Windows.
    #        return cmp( os.path.normpath(str(self)) .lower(),
    #                    os.path.normpath(str(other)).lower() )
    #    else:
    #        return cmp( os.path.normpath(str(self)),
    #                    os.path.normpath(str(other)) )
    def __iter__(self):
        # Note that this returns the "parts" of the path as strings and
        # NOT as paths themselves. Is this a problem?
        return iter(self.parts)
    if 0:   # + is not allowed
        def __add__(self, other):
            raise TypeError("unsupported operand type(s) for +: '%s' and '%s'"\
                            % (self.__class__.__name__,
                               other.__class__.__name__))
        def __radd__(self, other):
            raise TypeError("unsupported operand type(s) for +: '%s' and '%s'"\
                            % (self.__class__.__name__,
                               other.__class__.__name__))
    elif 0: # + adds path parts
        def __add__(self, other):
            return path( self.parts + splitall(str(other)) )
        def __radd__(self, other):
            return path( splitall(str(other)) + self.parts )
    else:   # + just does normal string addition
        pass
    def __mul__(self, other):
        if not isinstance(other, (int, long)):
            raise TypeError("unsupported operand type(s) for *: '%s' and '%s'"\
                            % (self.__class__.__name__,
                               other.__class__.__name__))
        return path( self.parts * other )
    def __rmul__(self, other):
        return path( other * self.parts )

    # Boolean methods.
    def exists(self):
        return os.path.exists(self)
    def isdir(self):
        return os.path.isdir(self)
    def isfile(self):
        return os.path.isfile(self)
    def islink(self):
        return os.path.islink(self)
    def ismount(self):
        return os.path.ismount(self)
    def isabs(self):
        return os.path.isabs(str(self))

    # stat-result properties
    def _get_atime(self):
        return os.path.getatime(str(self))
    atime = property(_get_atime, None, None, "path last access time")
    def _get_mtime(self):
        return os.path.getmtime(str(self))
    mtime = property(_get_mtime, None, None, "path last modification time")
    def _get_size(self):
        return os.path.getsize(str(self))
    size = property(_get_size, None, None, "file size")

    # split methods and properties
    def split(self):
        return self.parts
    def splitdrive(self):
        return tuple( map(path, os.path.splitdrive(str(self))) )
    def _get_drive(self):
        return path(os.path.splitdrive(str(self))[0])
    drive = property(_get_drive, None, None, "this path's drive")
    def splitext(self):
        return tuple( map(path, os.path.splitext(str(self))) )
    def _get_ext(self):
        return path(os.path.splitext(str(self))[0])
    ext = property(_get_ext, None, None, "this path's extension")
    if hasattr(os.path, "splitunc"):
        def splitunc(self):
            return tuple( map(path, os.path.splitunc(str(self))) )
        def _get_uncmount(self):
            return path(os.path.splitunc(str(self))[0])
        uncmount = property(_get_uncmount, None, None, "UNC mount point")

    # Other methods.
    def abs(self):
        return path( os.path.abspath(str(self)) )
    def commonprefix(self, *others):
        #XXX Does commonprefix() like 'path' objects?
        return path( commonprefix([str(self)] + others) )
    def norm(self):
        return path( os.path.normpath(str(self)) )
    def rel(self, relto=None):
        return path( relpath(str(self), relto) )
    def expanduser(self):
        return path( os.path.expanduser(str(self)) )
    def expandvars(self):
        return path( os.path.expandvars(str(self)) )
    def real(self):
        return path( os.path.realpath(str(self)) )


##if 0:
##    class path(tuple):
##        """A subclass of Python strings for manipulating paths.
##
##        A path object does for the os.path module what string methods did
##        for the string module (in Python 2.0) plus a little bit more:
##        list-like semantics based on path parts rather than characters. Path
##        objects, like strings, are immutable.
##
##        Some of the things you can do:
##            >>> root = path(sys.prefix)
##            >>> root
##            'C:\\Python22'
##            >>> sitepkgs = root / 'Lib' / 'site-packages'
##            >>> sitepkgs
##            'C:\\Python22\\Lib\\site-packages'
##            >>> libdir = sitepkgs / '..'
##            >>> libdir
##            'C:\\Python22\\Lib\\site-packages\\..'
##            >>> libdir.norm()
##            'C:\\Python22\\Lib'
##            >>> libdir.isdir()
##            1
##            >>> sitepkgs[:-1]
##            'C:\\Python22\\Lib'
##
##        (From the Python Cookbook, Files section, Recipe 100.)
##        """
##        _translate = { '.': os.curdir, '..': os.pardir }
##        _caseInsensitive = sys.platform.startswith("win")
##
##        def __new__(cls, *args):
##            """Accept various contruction calls:
##                path()            ->  ''
##                path("a/b")       ->  'a/b'
##                path("a", "b/c")  ->  'a/b/c'
##            """
##            parts = []
##            for arg in args:
##                if isinstance(arg, (str, unicode)):
##                    parts += splitall(arg)
##                elif isinstance(arg, path):
##                    parts += list(arg)
##                else:
##                    raise TypeError("illegal arguments for 'path' object "\
##                                    "construction: %r" % (args,))
##            result = tuple.__new__(cls, parts)
##            return result
##
####        def __coerce__(self, other):
####            print "XXX path.__coerce__"
####            if isinstance(other, str):
####                return (str(self), other)
####            elif isinstance(other, str):
####                return (str(self), other)
####            else:
####                return None
##        def __str__(self):
##            return os.path.join('', *self)
##        def __repr__(self):
##            return repr(str(self))
##        def __div__(self, other):
##            if isinstance(other, (str, unicode)):
##                other = self._translate.get(other, other)
##                return path( os.path.join(str(self), other) )
##            elif isinstance(other, path):
##                return path( os.path.join(str(self), str(other)) )
##            else:
##                raise TypeError("unsupported operand type(s) for /: '%s' and '%s'"\
##                                % (self.__class__.__name__,
##                                   other.__class__.__name__))
##        def __rdiv__(self, other):
##            if isinstance(other, (str, unicode)):
##                other = self._translate.get(other, other)
##                return path( os.path.join(other, str(self)) )
##            elif isinstance(other, path):
##                return path( os.path.join(str(other), str(self)) )
##            else:
##                raise TypeError("unsupported operand type(s) for /: '%s' and '%s'"\
##                                % (self.__class__.__name__,
##                                   other.__class__.__name__))
##        def __getslice__(self, start, stop):
##            # XXX Cannot just ignore this deprecated method in favour of
##            #     __getitem__ because (guessing here) tuple.__getslice__
##            #     gets in the way.
##            return path( *tuple.__getslice__(self, start, stop) )
##        def __cmp__(self, other):
##            if hasattr(os.path, "samefile"):
##                if os.path.samefile(str(self), str(other)):
##                    return 0
##                else:
##                    return cmp(str(self), str(other))
##            elif self._caseInsensitive:
##                #XXX Will not properly handle LONGNAME == SHORTNAME on Windows.
##                return cmp( os.path.normpath(str(self)) .lower(),
##                            os.path.normpath(str(other)).lower() )
##            else:
##                return cmp( os.path.normpath(str(self)),
##                            os.path.normpath(str(other)) )
##        def __add__(self, other):
##            raise TypeError("unsupported operand type(s) for +: '%s' and '%s'"\
##                            % (self.__class__.__name__,
##                               other.__class__.__name__))
##        def __mul__(self, other):
##            if not isinstance(other, (int, long)):
##                raise TypeError("unsupported operand type(s) for *: '%s' and '%s'"\
##                                % (self.__class__.__name__,
##                                   other.__class__.__name__))
##            return path( *tuple.__mul__(self, other) )
##        def __rmul__(self, other):
##            if not isinstance(other, (int, long)):
##                raise TypeError("unsupported operand type(s) for *: '%s' and '%s'"\
##                                % (self.__class__.__name__,
##                                   other.__class__.__name__))
##            return path( *tuple.__rmul__(self, other) )
##
##        # Boolean methods.
##        def exists(self):
##            return os.path.exists(str(self))
##        def isdir(self):
##            return os.path.isdir(str(self))
##        def isfile(self):
##            return os.path.isfile(str(self))
##        def islink(self):
##            return os.path.islink(str(self))
##        def ismount(self):
##            return os.path.ismount(str(self))
##        def isabs(self):
##            return os.path.isabs(str(self))
##        
##        # Other methods.
##        def norm(self):
##            return path( os.path.normpath(str(self)) )
##        def abs(self):
##            return path( os.path.abspath(str(self)) )
##        def rel(self, relto=None):
##            return path( relpath(str(self), relto) )
##        def expanduser(self):
##            return path( os.path.expanduser(str(self)) )
##        def split(self):
##            return tuple(self)


