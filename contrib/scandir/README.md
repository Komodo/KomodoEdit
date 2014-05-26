scandir, a better directory iterator that returns all file info the OS provides
===============================================================================

scandir is a module which provides a generator version of `os.listdir()` that
also exposes the extra file information the operating system returns when you
iterate a directory. scandir also provides a much faster version of
`os.walk()`, because it can use the extra file information exposed by the
scandir() function.


Background
----------

Python's built-in `os.walk()` is significantly slower than it needs to be,
because -- in addition to calling `listdir()` on each directory -- it calls
`stat()` on each file to determine whether the filename is a directory or not.
But both `FindFirstFile` / `FindNextFile` on Windows and `readdir` on Linux/OS
X/BSD already tell you whether the files returned are directories or not, so
no further `stat` system calls are needed. In short, you can reduce the number
of system calls from about 2N to N, where N is the total number of files and
directories in the tree.

**In practice, removing all those extra system calls makes `os.walk()` about
8-9 times as fast on Windows, and about 2-3 times as fast on Linux and Mac OS
X.** So we're not talking about micro-optimizations. [See more benchmarks
below.](#benchmarks)

Somewhat relatedly, many people have also asked for a version of
`os.listdir()` that yields filenames as it iterates instead of returning them
as one big list. This improves memory efficiency for iterating very large
directories.

So as well as a faster `walk()`, scandir adds a new `scandir()` function.
They're pretty easy to use, but [see below](#the-api) for the full API docs.


Why you should care
-------------------

I'd love for these incremental (but significant!) improvements to be added to
the Python standard library. This scandir module was released to help test the
concept and get it in shape for inclusion in the standard `os` module.

There are various third-party "path" and "walk directory" libraries available,
but Python's `os` module isn't going away anytime soon. So we might as well
speed it up and add small improvements where possible.

**So I'd love it if you could help test scandir, report bugs, suggest
improvements, or comment on the API.**


Benchmarks
----------

Below are results showing how many times as fast `scandir.walk()` is than
`os.walk()` on various systems, found by running `benchmark.py` with no
arguments as well as with the `-s` argument (which totals the directory size).

```
System version              Python version    Speed ratio    With -s
--------------------------------------------------------------------
Windows 7 64 bit            2.7 64 bit        8.4            15.7
Windows XP 32 bit           2.7 32 bit        TODO

Ubuntu 10.04 32 bit         2.7 32 bit        TODO           TODO

Mac OS X 10.7.5             2.7 64 bit        TODO
```

All of the above tests were done using the version of scandir with the fast C
`scandir_helper()` function.

Note that the gains are less than the above on smaller directories and greater
on larger directories. This is why `benchmark.py` creates a test directory
tree with a standardized size.

Another quick benchmark I've done (on Windows 7 64-bit) is running Eli
Bendersky's [pss](https://github.com/eliben/pss) source code searching tool
across a fairly large code tree (4938 files, 598 dirs, 200 MB). Using pss out
of the box with `os.walk()` on a not-found string takes 0.91 seconds. But
after monkey-patching in `scandir.walk()` it takes only 0.34 seconds -- 2.7
times as fast.


The API
-------

### walk()

The API for `scandir.walk()` is exactly the same as `os.walk()`, so just [read
the Python docs](http://docs.python.org/2/library/os.html#os.walk).

### scandir()

The `scandir()` function is the scandir module's main workhorse. It's defined
as follows:

```python
scandir(path='.', windows_wildcard='*.*') -> iterator of DirEntry objects
```

It yields a DirEntry for each file and directory in `path`. Like os.listdir(),
`.` and `..` are skipped, and the entries are yielded in system-dependent
order. Each DirEntry object has the following attributes and methods:

* `name`: filename, relative to path (like that returned by os.listdir)
* `is_dir()`: like os.path.isdir(), but requires no OS calls on most systems
  (Linux, Windows, OS X)
* `is_file()`: like os.path.isfile(), but requires no OS calls on most systems
  (Linux, Windows, OS X)
* `is_symlink()`: like os.path.islink(), but requires no OS calls on most
  systems (Linux, Windows, OS X)
* `lstat()`: like os.lstat(), but requires no OS calls on Windows

Obviously `windows_wildcard` is only available on Windows. It allows Windows
power users to pass a custom wildcard to FindFirstFile, which may avoid the
need to use `fnmatch` on the resulting names.

Here's a good usage pattern for `scandir`. This is in fact almost exactly how
the faster `os.walk()` implementation uses it:

```python
dirs = []
nondirs = []
for entry in scandir(path):
    if entry.is_dir():
        dirs.append(entry)
    else:
        nondirs.append(entry)
```


Further reading
---------------

* [Thread I started on the python-ideas list about speeding up os.walk()](http://mail.python.org/pipermail/python-ideas/2012-November/017770.html)
* [Python Issue 11406, original proposal for scandir(), a generator without the dirent/stat info](http://bugs.python.org/issue11406)
* [Further thread I started on python-dev that refined the scandir() API](http://mail.python.org/pipermail/python-dev/2013-May/126119.html)
* [Question on StackOverflow about why os.walk() is slow and pointers to fix it](http://stackoverflow.com/questions/2485719/very-quickly-getting-total-size-of-folder)
* [Question on StackOverflow asking about iterating over a directory](http://stackoverflow.com/questions/4403598/list-files-in-a-folder-as-a-stream-to-begin-process-immediately)
* [BetterWalk, my previous attempt at this, on which this code is based](https://github.com/benhoyt/betterwalk)
* [Info about Win32 reparse points / symbolic links](http://mail.python.org/pipermail/python-ideas/2012-November/017794.html)


To-do
-----

* Finish the C extension version (_scandir.c)
* Get `scandir()` included in the Python 3.5 standard library! :-)


Flames, comments, bug reports
-----------------------------

Please send flames, comments, and questions about scandir to Ben Hoyt:

http://benhoyt.com/

File bug reports or feature requests at the GitHub project page:

https://github.com/benhoyt/scandir
