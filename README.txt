Open Komodo Development README
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Introduction
============

This README.txt tells you how to get started building, using and
developing with the Open Komodo source base. Currently this basically
means building Komodo Edit (the once free-as-in-beer, now also
free-as-in-speech Komodo editor).

Komodo is based on Mozilla, so prepare yourself for some serious build
time. If you have trouble with any of the following instructions please
log a bug:
<http://bugs.activestate.com/enter_bug.cgi?product=OpenKomodo&component=Documentation>



I'm lazy, just show me how to build it
======================================

If any of these steps break, please first look at the full instructions
below (especially the "prerequisites" sections).

Build steps on Windows:

    REM ---- Build Mozilla
    cd openkomodo\mozilla
    setenv-moz-msvc6.bat
    python build.py configure -k 5.0 --moz-src=cvs --release --no-strip --tools --moz-objdir=ko-obj
    python build.py distclean all
    cd ..
    REM ---- Build Komodo
    set PATH=util\black;%PATH%
    bk configure
    bk build
    REM ---- Run Komodo
    bk run

Build steps on Linux and Mac OS X:

    #---- Build Mozilla
    cd openkomodo/mozilla
    python build.py configure -k 5.0 --moz-src=cvs --release \
        --no-strip --tools
    python build.py distclean all
    cd ..
    #---- Build Komodo
    export PATH=`pwd`/util/black:$PATH   # Komodo's "bk" build tool
    bk configure
    bk build
    #---- Run Komodo
    bk run



Getting the Source
==================

If you are reading this, you probably already have it, but for the record:
The Open Komodo sources are kept in a Subversion repository hosted
at the openkomodo.com site. Read-only public access is available via:

    svn co http://svn.openkomodo.com/repos/openkomodo/trunk openkomodo

Read/write developer access is available via:

    svn co https://svn.openkomodo.com/repos/openkomodo/trunk openkomodo



Build Prerequisites for Windows
===============================

- Python 2.5. You can install ActivePython 2.5 from here:
  <http://downloads.activestate.com/ActivePython/windows/2.5/ActivePython-2.5.1.1-win32-x86.msi>

- Visual C++ 8.0 (aka Visual Studio 2005) and all the Platform SDKs for
  building Mozilla with vc8 as described here:
    http://developer.mozilla.org/en/docs/Windows_Build_Prerequisites  
  
- Install the latest "MozillaBuild-$ver.exe" package into *the default dir*
  (i.e. "C:\mozilla-build").
  <http://ftp.mozilla.org/pub/mozilla.org/mozilla/libraries/win32/>

- Install ActivePerl 5.8.

  <http://downloads.activestate.com/ActivePerl/Windows/5.8/ActivePerl-5.8.8.822-MSWin32-x86-280952.msi>

  ActivePerl is currently required for the Komodo-part of the build
  (where the "Mozilla-part of the build" is the other part). The
  MozillaBuild package (previous step) *does* include a Perl 5.6 build,
  but it is a mingw-built Perl that the Komodo build system cannot use.
  
  (Eventually this dependency will go away when the curent Komodo
  Cons/Black-based system is replaced (hopefully late 2007 or early 2008.)



Build Prerequisites for Mac OS X
================================

- Python **2.6**. You can install ActivePython 2.6 from here:

  <http://downloads.activestate.com/ActivePython/macosx/2.6/>

  If you prefer the Python builds from python.org should be sufficient
  as well.

- Xcode. Install the latest one (avoid Xcode 2.0, though).
  <http://developer.apple.com/tools/download/>
  Be sure to install the Cross-Development SDKs, which is
  only available by choosing a Customized build in the Xcode installer.

- MacPorts (<http://www.macports.org/>).

  (Note: Fink works too but most of the build testing and instructions is
  done with MacPorts.)

- libIDL-2.0 >= 0.8.0. Once you have MacPorts installed you need just run::

    sudo port sync
    sudo port install libidl

- autoconf v2.13. Once you have MacPorts installed you need just run::

    sudo port install autoconf213

- ensure you are using gcc 4.0::

    gcc --version
  
  Gcc 4.0 is require to build for x86, and it works to build for powerpc
  (just limits to 10.3.9 compatibility -- which is sufficient for Komodo).
  TODO: check this at build/configure-time.
 
See <http://developer.mozilla.org/en/docs/Mac_OS_X_Build_Prerequisites>
for more details on Mac OS X build prerequisites. However, following the
above steps is *meant to be sufficient* to get building Komodo.


Build Prerequisites for Linux
=============================

- Python 2.5 or greater. Your distro's Python 2.5 should be sufficient, or
  you can install ActivePython from here:
  
    <http://downloads.activestate.com/ActivePython/linux/2.5/>

- Everything mentioned in the Mozilla Linux build prerequisites:

    <http://developer.mozilla.org/en/docs/Linux_Build_Prerequisites>


Prerequisite packages by Distro
-------------------------------

This section is intended to give Linux distro-specific package manager steps
for installing all build prerequisites. If you have info for distros not
listed here and/or corrections, please start a Documentation bug for this:

    <http://bugs.activestate.com/enter_bug.cgi?product=OpenKomodo&component=Documentation>


- Ubuntu 7.10 & 8.04:
  
    apt-get install g++ patch libgtk2.0-dev libidl-dev libcurl4-gnutls-dev

- Others ...




Building
========

Komodo is made up of:

- a Python build for the Mozilla PyXPCOM extension
- a Mozilla build (with a number of Komodo-specific patches)
- the Komodo-specific build bits: mostly chrome (XUL, JS, ...) and
  PyXPCOM components (Python)


Step 1: Building Python
-----------------------

Currently the Komodo source tree includes *prebuilt* Python binaries
in `mozilla/prebuilt/python2.5`. Basically these are vanilla Python 2.5.1
builds with the following tweaks:

- [Windows] a patch to disable looking in the registry for sys.path info
- [Windows] built with VC6 (atypical of all current Python distros)
- [Mac OS X] a patch to the Python frameworks bin/python stub to allow
  running `python` in this framework without it having to be installed
  in one of the standard "/Library/Frameworks",
  "/System/Library/Frameworks" locations.
- The builds are shared (atypical of some Linux Python builds)

Currently these are ActivePython builds. However, the plan is to update
the Open Komodo build system (in late 2007) to support building its own
Python from sources rather than relying on a prebuilt ActivePython. This
was just the quickest way to get the Open Komodo sources out in 2 f*@&ing
months (<http://blogs.activestate.com/shanec/2007/09/holy-komodo.html>).


Step 2: Building Mozilla
------------------------

This'll take a while but, unless you are doing some lower-level hacking
for Komodo, you should only need to do this once (in a while).

1. Get into the correct dir:

        cd mozilla

2. (Windows-only) Setup your environment for building.

   - If you installed MozillaBuild into a directory other than
     "c:\mozilla-build", shame on you. Tell the build where it is:
     
        set MOZILLABUILD=...\path\to\your\mozillabuild\base

   - If you have cygwin installed, shame on you (consider MSYS instead).
     Ensure that your PATH does not contain any cygwin executables or
     DLLs.

   - Setup your Mozilla environment:

        setenv-moz-msvc6.bat

3. Configure for the mozilla build. On Windows you currently want
   something like:

        python build.py configure -k 5.0 --moz-src=cvs --release --no-strip --tools --moz-objdir=ko-obj

   On other platforms:
   
        python build.py configure -k 5.0 --moz-src=cvs --release \
            --no-strip --tools

   What this configure-step does is create a "config.py" file that guides
   the build step (next). This is akin to the "./configure" in the common
   "./configure; make; make install" build trinity.
   
   What this configuration is saying is:
   - configure for a Komodo Edit 5.0.x build
   - use the latest Mozilla CVS HEAD sources
   - do a release (i.e. non-debug) build
   - don't strip symbol information from binaries (i.e. *don't* put
     --enable-strip in .mozconfig)
   - also build some extra tools-parts of the Mozilla tree (
     venkman, inspector, cview)
     
   Run `python build.py -h configure` for more details.

4. Build away:

        python build.py all
    
   This will take a long time, but you should have a usable Mozilla
   build when it is done.



Step 3: Building Komodo
-----------------------

1. Get the in-house `bk` (a.k.a. Black -- ask trentm for the history if
   you are curious) tool on you PATH (or a symlink or alias is fine):
   
        cd ..    # move back up from the "mozilla" dir
        export PATH=`pwd`/util/black:$PATH
        
   or, on Windows:
   
        set PATH=path\to\sourcedir\util\black;%PATH%

2. Configure you Komodo build.

   In general the default configuration is fine for a development build:
   
        bk configure
    
   If you built Mozilla above for a Komodo version other than the version
   mentioned in "src/version.txt", then you may have to specify your
   version. E.g. if you configured above with
   "python configure.py -k 5.0 ..." then you'd want something like:
   
        bk configure -V 5.0.0-devel

   Run `bk help configure` for a (somewhat sparse) listing of available
   options.

3. Build away:

        bk build

4. Run Komodo:

        bk run [-v]



The Typical Komodo Build Cycle
==============================

The typical build cycle for Komodo development is:

- edit some files under "src/..."
- `bk build`
- `bk run -v`
- test

While "bk build" should always build everything necessary, it can be a
little slow. For a quicker development cycle you can do:

    bk build quick

This will appropriately rebuild *most* changes to interpreted sources: JS,
Python, CSS, XUL, XBL, DTD. For certain things -- C/C++ changes, new files,
IDL changes -- you still need to run the slower "bk build".



Build Troubleshooting Notes
===========================

- [Linux] On my Ubuntu Dapper install I had to install "automake1.9" to
  get "aclocal"::
  
    sudo apt-get install automake1.9

- [Linux] On my Ubuntu Dapper box /usr/bin/autoconf is a wrapper that
  defaults to autoconf2.13. PHP 4.3's "phpize" requires autoconf 2.50. I
  had to tweak "~/opt/php/4.3.11/bin/phpize" to use "autoconf2.50" instead
  of bare "autoconf".

- "bk configure" fails.

  If "bk configure" fails, here is how to go about trying to help fix it.
  Background: "bk configure" is doing an autoconf-like thing: gathering a
  bunch of information (guided by command-line options) that is then
  written out to a config file (current "bkconfig.py", "bkconfig.pm" and
  "bkconfig.bat|sh") for use by subsequent build steps. The list of
  config vars being determined is in the "configuration" dict in
  "Blackfile.py" ("bk" == Black, hence make is to Makefile as "bk" is to
  Blackfile.py). The implementation logic for most configuration vars
  is in "bklocal.py" -- one Python class definition per configuration var.
  
  Process to help find the problem:
  1. Look at the "bk configure" output. The error will be after output
     that says "determining BLAH...". Look for that "BLAH" string in
     "bklocal.py" to find the corresponding config var class.
  2. The awkwardly named "_Determine_Do()" method for that class is where
     the value is determined. The failure is probably in there. Feel
     free to put some print statements in there and re-run your
     "bk configure ..." call to try to suss out the problem.
  3. Log a bug:
     <http://bugs.activestate.com/enter_bug.cgi?product=OpenKomodo&component=InternalBuild>
  


Setup to Build a Komodo Installer
=================================

TODO



