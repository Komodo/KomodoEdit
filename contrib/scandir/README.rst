scandir, a better directory iterator
====================================

**UPDATE: I've written a Python Enhancement Proposal (PEP) that proposes
including scandir() in the standard library.** Please read
`PEP 471 <http://legacy.python.org/dev/peps/pep-0471/>`_ for details.

scandir is a module which provides a generator version of ``os.listdir()`` that
also exposes the extra file information the operating system returns when you
iterate a directory. scandir also provides a much faster version of
``os.walk()``, because it can use the extra file information exposed by the
scandir() function.

scandir is intended to work on Python 2.6+ and Python 3.2+ (and it has been
tested on those versions).

Note that this module is currently beta software -- working and used
to some extent, and more than a proof-of-concept, but not
battle-tested or extremely widely used. It's my hope that scandir
will be included in Python 3.5 as ``os.scandir()``.


Background
----------

Python's built-in ``os.walk()`` is significantly slower than it needs to be,
because -- in addition to calling ``listdir()`` on each directory -- it calls
``stat()`` on each file to determine whether the filename is a directory or not.
But both ``FindFirstFile`` / ``FindNextFile`` on Windows and ``readdir`` on Linux/OS
X already tell you whether the files returned are directories or not, so
no further ``stat`` system calls are needed. In short, you can reduce the number
of system calls from about 2N to N, where N is the total number of files and
directories in the tree.

**In practice, removing all those extra system calls makes ``os.walk()`` about
7-20 times as fast on Windows, and about 4-5 times as fast on Linux and Mac OS
X.** So we're not talking about micro-optimizations. See more benchmarks
in the "Benchmarks" section below.

Somewhat relatedly, many people have also asked for a version of
``os.listdir()`` that yields filenames as it iterates instead of returning them
as one big list. This improves memory efficiency for iterating very large
directories.

So as well as a faster ``walk()``, scandir adds a new ``scandir()`` function.
They're pretty easy to use, but see "The API" below for the full docs.


Why you should care
-------------------

I'd love for these incremental (but significant!) improvements to be added to
the Python standard library. This scandir module was released to help test the
concept and get it in shape for inclusion in the standard ``os`` module.

There are various third-party "path" and "walk directory" libraries available,
but Python's ``os`` module isn't going away anytime soon. So we might as well
speed it up and add small improvements where possible.

**So I'd love it if you could help test scandir, report bugs, suggest
improvements, or comment on the API.**


Benchmarks
----------

Below are results showing how many times as fast ``scandir.walk()`` is than
``os.walk()`` on various systems, found by running ``benchmark.py`` with no
arguments as well as with the ``-s`` argument (which totals the directory size)::

    System version          Python version  Speed ratio    With -s
    --------------------------------------------------------------
    Windows 7 64-bit        2.7.5 64-bit    7.5            14.2
    Windows 7 64-bit SSD    2.7.6 64-bit    10.0           18.5
    Windows 7 64-bit NFS    2.7.6 64-bit    23.2           46.4
    Windows 7 64-bit        3.4.1 64-bit    TODO

    CentOS 6.5 64-bit       2.7.6 64-bit    5.5            2.3
    Ubuntu 12.04 32-bit     2.7.3 32-bit    4.3            2.2

    Mac OS X 10.9.3         2.7.5 64-bit    5.3            2.1

All of the above tests were done using the version of scandir with the fast C
``scandir_helper()`` function.

Note that the gains are less than the above on smaller directories and greater
on larger directories. This is why ``benchmark.py`` creates a test directory
tree with a standardized size.

Another quick benchmark I've done (on Windows 7 64-bit) is running Eli
Bendersky's `pss <https://github.com/eliben/pss>`_ source code searching tool
across a fairly large code tree (4938 files, 598 dirs, 200 MB). Using pss out
of the box with ``os.walk()`` on a not-found string takes 0.91 seconds. But
after monkey-patching in ``scandir.walk()`` it takes only 0.34 seconds -- 2.7
times as fast.


The API
-------

walk()
~~~~~~

The API for ``scandir.walk()`` is exactly the same as ``os.walk()``, so just
`read the Python docs <http://docs.python.org/2/library/os.html#os.walk>`_.

scandir()
~~~~~~~~~

The ``scandir()`` function is the scandir module's main workhorse. It's defined
as follows::

    scandir(path='.') -> generator of DirEntry objects

Like ``listdir``, ``scandir`` calls the operating system's directory
iteration system calls to get the names of the files in the given
``path``, but it's different from ``listdir`` in two ways:

* Instead of returning bare filename strings, it returns lightweight
  ``DirEntry`` objects that hold the filename string and provide
  simple methods that allow access to the additional data the
  operating system may have returned.

* It returns a generator instead of a list, so that ``scandir`` acts
  as a true iterator instead of returning the full list immediately.

``scandir()`` yields a ``DirEntry`` object for each file and
sub-directory in ``path``. Just like ``listdir``, the ``'.'``
and ``'..'`` pseudo-directories are skipped, and the entries are
yielded in system-dependent order. Each ``DirEntry`` object has the
following attributes and methods:

* ``name``: the entry's filename, relative to the scandir ``path``
  argument (corresponds to the return values of ``os.listdir``)

* ``path``: the entry's full path name (not necessarily an absolute
  path) -- the equivalent of ``os.path.join(scandir_path, entry.name)``

* ``is_dir(*, follow_symlinks=True)``: similar to
  ``pathlib.Path.is_dir()``, but the return value is cached on the
  ``DirEntry`` object; doesn't require a system call in most cases;
  don't follow symbolic links if ``follow_symlinks`` is False

* ``is_file(*, follow_symlinks=True)``: similar to
  ``pathlib.Path.is_file()``, but the return value is cached on the
  ``DirEntry`` object; doesn't require a system call in most cases; 
  don't follow symbolic links if ``follow_symlinks`` is False

* ``is_symlink()``: similar to ``pathlib.Path.is_symlink()``, but the
  return value is cached on the ``DirEntry`` object; doesn't require a
  system call in most cases

* ``stat(*, follow_symlinks=True)``: like ``os.stat()``, but the
  return value is cached on the ``DirEntry`` object; does not require a
  system call on Windows (except for symlinks); don't follow symbolic links
  (like ``os.lstat()``) if ``follow_symlinks`` is False

Here's a very simple example of ``scandir()`` showing use of the
``DirEntry.name`` attribute and the ``DirEntry.is_dir()`` method::

    def subdirs(path):
        """Yield directory names not starting with '.' under given path."""
        for entry in os.scandir(path):
            if not entry.name.startswith('.') and entry.is_dir():
                yield entry.name

This ``subdirs()`` function will be significantly faster with scandir
than ``os.listdir()`` and ``os.path.isdir()`` on both Windows and POSIX
systems, especially on medium-sized or large directories.

See `PEP 471 <http://legacy.python.org/dev/peps/pep-0471/>`_ for more
details on caching and error handling.


Further reading
---------------

* `Thread I started on the python-ideas list about speeding up os.walk() <http://mail.python.org/pipermail/python-ideas/2012-November/017770.html>`_
* `Python Issue 11406, original proposal for scandir(), a generator without the dirent/stat info <http://bugs.python.org/issue11406>`_
* `Further thread I started on python-dev that refined the scandir() API <http://mail.python.org/pipermail/python-dev/2013-May/126119.html>`_
* `Question on StackOverflow about why os.walk() is slow and pointers to fix it <http://stackoverflow.com/questions/2485719/very-quickly-getting-total-size-of-folder>`_
* `Question on StackOverflow asking about iterating over a directory <http://stackoverflow.com/questions/4403598/list-files-in-a-folder-as-a-stream-to-begin-process-immediately>`_
* `BetterWalk, my previous attempt at this, on which this code is based <https://github.com/benhoyt/betterwalk>`_
* `Info about Win32 reparse points / symbolic links <http://mail.python.org/pipermail/python-ideas/2012-November/017794.html>`_


To-do
-----

* Finish the C extension version (_scandir.c)
* Get PEP 471 accepted and ``scandir()`` included in the Python 3.5
  standard library! :-)


Flames, comments, bug reports
-----------------------------

Please send flames, comments, and questions about scandir to Ben Hoyt:

http://benhoyt.com/

File bug reports or feature requests at the GitHub project page:

https://github.com/benhoyt/scandir
