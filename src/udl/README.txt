README for UDL (User Defined Languages)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

UDL provides a system for multilanguage syntax lexing in Komodo (and for
user-defined syntax highlighting). "Luddite" is the name of a tool for
compiling lexer definition files (.udl files) to the resources that Komodo
needs to use them. Luddite also provides functionality for package these
resources into a Komodo extension and for install that.



Installation
============

1. To install luddite you first need a Python installation (minimum version
   2.3). If you do not have that, you can get the latest ActivePython from
   here::

        http://www.activestate.com/Products/ActivePython/

2. Unzip the luddite source package::

        unzip luddite.zip       # Windows
        tar xzf luddite.tar.gz  # Linux, Mac OS X

3. Install luddite into your Python::

        cd luddite-$VERSION
        python setup.py install

4. Ensure luddite is on your PATH and working. The following command should
   print luddite's main help.

        luddite

   If that worked, then you are done with installation. If not, then read the
   `Installation Troubleshooting`_ section below.



Overview of adding a custom language for Komodo
===============================================

The basic usage of luddite to add a custom language to Komodo is as follows:

1. Write the lexer definition: one or more .udl files. Resources for writing
   UDL files include:
   
   - using `udl/*.udl` as examples
   - `the spec <http://specs.tl.activestate.com/kd/kd-0149.html>`_
   - Eric's blogged `UDL tutorial adding Kid as a Komodo language
     <http://blogs.activestate.com/ericp/2007/01/kid_adding_a_ne.html>`_

   There currently is no real user documentation.

2. Compile the lexer::

    python luddite.py help compile
    python luddite.py compile UDL_PATH

3. Build a Komodo extension with the built resources::

    python luddite.py help package
    python luddite.py package LANG

4. Install that extension in your Komodo. You can do this either by opening
   that extension (FOO.xpi) in Komodo or via::

    python luddite.py install LANG


Note: The luddite.py script requires a zip executable in the path.
Info-Zip, a free implementation of zip for Windows can be found here:

  http://www.info-zip.org/Zip.html#Win32


Installation Troubleshooting
============================


Windows. `python setup.py install` worked, but running `luddite` does not work.
-------------------------------------------------------------------------------

The problem might be one of two things. Either (a) you do not have ".py" on
your PATHEXT environment variable or, more likely, (b) you do not have
Python's "Scripts" directory on your PATH.

(a) If you do not have ".py" on your PATHEXT environment variable, then
Windows does not know to look for `luddite.py` when you try to run
`luddite`. Try running::

    luddite.py

or add ".py" to your PATHEXT. For example::

    set PATHEXT=%PATHEXT%;.py

Note: To change PATHEXT permanently your will need to make the change in
your Windows' System Properties dialog box:

- right-click on "My Computer" and select "Properties"
- click the "Advanced" tab
- click "Environment Variables"
- edit the PATHEXT environment variable

(b) On Windows, Python *scripts* installed with 'setup.py' are installed to
a "Scripts" subdirectory of your Python installation. For example::

    C:\Python24\Scripts\luddite.py

Typically this directory is *not* automatically on your PATH. You will
either need to manually put it on your PATH or manually specify the full
path to run 'luddite', e.g.::

    python C:\Python24\Scripts\luddite.py


My install on Linux fails with "error: invalid Python installation: unable to open /usr/lib/python2.4/config/Makefile"
----------------------------------------------------------------------------------------------------------------------

The install instructions for many of the Python packages on trentm.com have you run::

    python setup.py install

This has been known to fail on some Linux distributions (e.g. Ubuntu) when
using the system Python (/usr/bin/python)::

    $ /usr/bin/python setup.py install
    running install
    error: invalid Python installation: unable to open /usr/lib/python2.4/config/Makefile (No such file or directory)

``setup.py`` is a Python setup script using Python's standard `distutils
system`_. To install a Python module it needs to use the Makefile with which
Python was built. This is typically in a Linux distro's Python development
package -- which may not be installed by default.

On Ubuntu, if you get this failure, you need to install the "python-dev"
package::

    sudo apt-get install python-dev


.. _distutils system: http://docs.python.org/inst/inst.html



Internal build maintenance
==========================

- 'ludditelib/constants.py' is generated from 'LexUDL.cxx' and
  'Scintilla.iface'. If those update significantly then 'gen_constants.py'
  should be run as per its docstring.

