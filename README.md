# Komodo Edit

This readme explains how to get started building, using and developing with
the Komodo Edit source base.

Whilst the main Komodo Edit source is hosted under this repository you may also
want to check out the individual component/addon repositories under
https://github.com/Komodo in case you only want to contribute to a specific
component. This'll save you some time and hassle as you would not have to build
the entire project.

## Table of Contents

- [Screenshot](#screenshot)
- [Download](#download)
- [Feedback](#feedback)
- [Building Komodo](#building-komodo)
    - [Building on Windows](#building-on-windows)
    - [Building on Mac](#building-on-mac)
    - [building on Linux](#building-on-linux)
    - [Building with Docker](#building-with-docker)
    - [Building Complications](#building-complications)

## Screenshot

![Screenshot](screenshot.png)

## Download

You can [download Komodo Edit here](https://www.activestate.com/komodo-ide/downloads/edit).

## Feedback

There are several ways to get in contact with the Komodo devs:

Github: <https://github.com/Komodo/KomodoEdit>

Forums: <http://forum.komodoide.com/>

Bug Tracker: <https://github.com/Komodo/KomodoEdit/issues>

IRC: <irc://irc.mozilla.org/#komodo>

Mailing Lists: [komodo-discuss](http://code.activestate.com/lists/komodo-discuss/) & [komodo-beta](http://code.activestate.com/lists/komodo-beta/) & [komodo-announce](http://code.activestate.com/lists/komodo-announce/)

## Building Komodo
Note that these are simplified steps of the building process, for a more in-depth
guide check (outdated) [BUILD.txt](docs/BUILD.txt). 

### Building on Windows

- [Prerequisites](#prerequisites)
- [Building Steps](#building-steps)

#### Prerequisites

 * Python >=2.7 (but not Python 3.x yet). You can [install ActivePython from here](http://downloads.activestate.com/ActivePython/releases).

 * Visual C++ 11.0 (aka Visual Studio 2012) and all the Platform SDKs for
   building Mozilla with vc11 [as described here](http://developer.mozilla.org/en/docs/Windows_Build_Prerequisites).
   
 * Install [version 1.9.0 of "MozillaBuild-$ver.exe"](http://ftp.mozilla.org/pub/mozilla.org/mozilla/libraries/win32/) package into *the default dir*
   (i.e. "C:\mozilla-build").

   * Once installed remove the wget and hg directories
   * Download version 2.2.0 and install it to a temp directory, then copy the wget directory from 2.2 to the 1.9 install directory

 * Install the Perl <= 5.22

 * Install Mercurial

See <http://developer.mozilla.org/en/docs/Windows_Build_Prerequisites> for
more details on Windows build prerequisites. However, following the above
steps is *meant to be sufficient* to get Komodo building.

#### Building Steps

 * Checkout Komodo Edit: `git clone https://github.com/Komodo/KomodoEdit.git`

 * Using the command line, enter your checkout directory and run:

   ```
    cd mozilla
    setenv-moz-msvc11.bat
    python build.py configure -k 11.10
    python build.py distclean all
   ```

   This will configure and build mozilla and can take anywhere from 30 minutes
   to several hours to complete (depending on your specs). For most modern
   machines it should be about an hour.

 * After mozilla is built successfully go back to the main repo directory and
   build komodo:

   ```
    cd ..
    set PATH=util\black;%PATH%
    bk configure -V 11.10.0-devel # --without-binary-dbgp-clients
    bk build
   ```

   This should take significantly less time than building Mozilla.

 * Once the build has completed you can simply run Komodo by executing `bk run`
   
Upon making any modifications to the source you will again have to run `bk build`,
or simply `bk build && bk run` to quickly get back into Komodo. Subsequent builds
should be a lot faster as much of the compiled data is cached.

### Building on Mac

- [Mac Prerequisites](#mac-prerequisites)
- [Building Steps](#building-steps-1)

#### Mac Prerequisites

 * Python >=2.7 (but not Python 3.x yet). You can
   [install ActivePython from here](http://downloads.activestate.com/ActivePython/releases).

   If you prefer the Python builds from python.org should be sufficient as well.

 * Xcode 6.4(SDK 10.9 & 10.10). For 8.0 see below. You can get version 6.4 from [the developer downloads site](https://developer.apple.com/downloads/).
  
  * MacOSX10.10.sdk or older  
  * *IDE ONLY* SDK 10.8 for Code Intel. Can be found in Xcode 5.1.1
  * If you have/need other versions of Xcode installed then you can use `xcode-select` to change the active Xcode:
  
     `$ xcode-select -s /Path/To/Xcode\ 6.4.app/`
 
 * Xcode Command Line Tools.

   Open the Xcode preferences, then in the Downloads tab, select and install the
   Command Line Tools.

 * [MacPorts](http://www.macports.org/). (Note: Fink may work too but most of the
   build testing and instructions is done with MacPorts.)

 * autoconf v2.13. Once you have MacPorts installed you need just run
   `sudo port install autoconf213`

 * ensure you are using clang or gcc 4.2 (or higher)

See <http://developer.mozilla.org/en/docs/Mac_OS_X_Build_Prerequisites>
for more details on Mac OS X build prerequisites. However, following the
above steps is *meant to be sufficient* to get Komodo building.

### Xcode 8 Prerequisites

Officially we do not support Xcode 8, however it is possible to build Komodo
under Xcode 8 using a new extra steps.

 * Copy over the 10.8 and 10.9 SDK's from an older XCode install, they should be in:
   Xcode.app/Contents/Developer/Platforms/macOSX.platform/
 * Set MinimumSDKVersion to 10.9 in Xcode.app/Contents/Developer/Platforms/macOSX.platform/Info.plist
 * Ensure you are using ccache 3.1 (later versions will break)
 * Configure Mozilla with `--options=disable-webrtc`


#### Building Steps

 * Checkout Komodo Edit: `git clone https://github.com/Komodo/KomodoEdit.git`

 * Using the terminal, enter your checkout directory and run:

   ```
    1) cd komodo/mozilla
    
    2) python build.py configure -k 10.10
    
    3) python build.py all
    
       or 
    
       python build.py distclean all
       (to delete and re-download Mozilla again)
   ```

   This will configure and build mozilla and can take anywhere from 30 minutes
   to several hours to complete (depending on your specs). For most modern
   machines it should be about an hour.
   
##### ** Building with GCC 5.0 and higher **
   If you are using GCC 5.0, the build may fail. If it does,
   there are changes that need to be made to two files. However, if you are running
   a clean build for the first time, you need to allow this part of the build to fail
   first. This is because the files are in the Mozilla part of the build which has to
   be downloaded first.
   
###### These files need to be changed:
   1) /KomodoEdit/mozilla/build/moz3500-ko9.10/mozilla/configure.in
   
   ```
    @@ -7509,8 +7509,6 @@
    eval $(CXX="$CXX" HOST_CXX="$HOST_CXX" $PYTHON -m mozbuild.configure.libstdcxx)
    AC_SUBST(MOZ_LIBSTDCXX_TARGET_VERSION)
    AC_SUBST(MOZ_LIBSTDCXX_HOST_VERSION)
+   CXXFLAGS="$CXXFLAGS -D_GLIBCXX_USE_CXX11_ABI=0"
+   HOST_CXXFLAGS="$HOST_CXXFLAGS -D_GLIBCXX_USE_CXX11_ABI=0"
 fi
   ```
   
   See [bug #1153109](https://bugzilla.mozilla.org/show_bug.cgi?id=1153109) in Mozilla's bug database for more information.
   
   2) /KomodoEdit/mozilla/build/moz3500-ko9.10/mozilla/dom/ipc/Blob.cpp

   ```
   @@ -3874,7 +3874,7 @@
   // Make sure we can't overflow.
   if (NS_WARN_IF(UINT64_MAX - aLength < aStart)) {
     ASSERT_UNLESS_FUZZING();
-    return nullptr;
+    return false;
   }
 
   ErrorResult errorResult;
   @@ -3883,7 +3883,7 @@
 
   if (NS_WARN_IF(aStart + aLength > blobLength)) {
     ASSERT_UNLESS_FUZZING();
-    return nullptr;
+    return false;
   }
   ```
   
   See [Porting to GCC 5](https://gcc.gnu.org/gcc-5/porting_to.html) for more information.

 * After mozilla is built successfully, go back to the main repo directory and
   build komodo:

   ```
    cd ..
    export PATH=`pwd`/util/black:$PATH   # Komodo's "bk" build tool
    git submodule update --init
    git submodule update --remote
    bk configure -V 10.10.0-devel
    bk build
   ```

   This should take significantly less time than building Mozilla.

 * Once the build has completed you can simply run Komodo by executing `bk run`

Upon making any modifications to the source you will again have to run `bk build`,
or simply `bk build && bk run` to quickly get back into Komodo. Subsequent builds
should be a lot faster as much of the compiled data is cached.

### Building on Linux
[Linux instructions](docs/Linux_build_guide.md)
<br />
<br />


### Building with Docker

The easiest way to get started is to use our Docker image, this will basically
provide you with a Ubuntu 12.04 based build of Komodo.

After cloning the repository simply navigate into `{repo}/util/docker` and check
out `./docklet --help`

To use the docker image you need to of course have Docker installed as well as
have X11 forwarding enabled in your SSH client (should work by default on most
linux distros).

#### Prepare Docker Image

 * Build the docker image: `./util/docker/docklet image`
 * Start your container: `./util/docker/docklet start`
 * SSH into your container to start working: `./util/docker/docklet ssh`

Your project files will be mounted at `/komodo/dev`

NOTE - if you are updating from a previous version where your project files were
at `/root/komodo` you will need to fix permissions on your Komodo project and
profile folders. Ie:

```
chown -R <my-username>:<my-group> <my-project-location>
chown -R <my-username>:<my-group> ~/.komodoide
```

You will also need to redo your build (distclean mozilla and komodo).

#### Building Steps

Once your image is prepared you can follow the building steps for linux as
described above. You will be running these from the docker container, so ssh into
it using the command above and then run the commands from `/komodo/dev`

#### Running

Once your build is complete you exit out of the container (`exit`) and can then
run Komodo with

`./util/docker/docklet run`

To rebuild Komodo (after making changes) and run it again you can use

`./util/docker/docklet build run`

If your changes are not being reflected you may need to clean your build, to do
this use

`./util/docker/docklet clean`

Or to do it all at once (clean, build and run)

`./util/docker/docklet clean build run`


### Building Complications

If any errors occur during your first built-time and it is not obvious how to fix
the issue on your own please refer to the [Feedback](#feedback) section on how to get in contact
with us.

Note that if building complications arise after you updated your repo with the latest
changes you might need to clear your local cache as it might be conflicting with the
new changes, to do this run `bk distclean` before running your build steps.

### Pro-Tips

**Build a single piece**

Sometimes ```bk build``` is too much and ```bk build quick``` isn't enough.  If ```bk build quick``` doesn't appear to pickup your changes, try pointing ```bk build``` at the piece in question.  

**Example**

```bk build build/release/modules/places #this will build the places module only```

**NOTE**: Do not rely on this method as ```bk build quick``` is faster and in some cases does some steps that the above example won't perform.  Use it as a last ditch effort before you try ```bk distclean && bk build```.

---
