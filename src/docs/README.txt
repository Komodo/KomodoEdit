Installing Komodo: 

     * Windows
          + Prerequisites
          + Installing the Komodo License
          + Upgrading from a Previous Komodo Version
          + Installing Komodo on Windows
          + Command Line Installation Options
          + Starting Komodo on Windows
          + Uninstalling Komodo on Windows
     * Mac OS X
          + Prerequisites
          + Installing the Komodo License
          + Upgrading from a Previous Komodo Version
          + Installing Komodo on OS X
          + Starting Komodo on OS X
          + Uninstalling Komodo on OS X
     * Linux
          + Prerequisites
          + Installing the Komodo License
          + Upgrading from a Previous Komodo Version
          + Installing Komodo on Linux
          + Starting Komodo on Linux
          + Uninstalling Komodo on Linux
     * Language and Debugging Prerequisites
     * Source Code Control Integration Prerequisites

Windows

Prerequisites

Hardware Requirements

     * Intel x86 processor, 500 MHz (or faster) with 256 MB RAM.
     * Up to 230 MB in your TMP directory (as indicated by the value of
       your 'TMP' environment variable) during installation, even if you
       plan to install Komodo to another drive. If you do not have the
       required space on this drive, manually set the 'TMP' environment
       variable to a directory on a drive with sufficient space.

Operating System Requirements

   Supported operating systems:

   The following platforms are officially supported. Current Critical
   Updates, Windows Updates, and Service Packs must be installed (see
   http://windowsupdate.microsoft.com).
     * Windows Vista
     * Windows XP
     * Windows Server 2003
     * Windows 2000

Software Prerequisites on Windows

   Installation Prerequisites:
     * Windows 98, Me and NT users: Microsoft Windows Installer (MSI)
       version 2.0 or greater ( MSI 2.0 for 9x and Me, MSI 2.0 for NT)
     * Windows 98/NT4 Users: Windows Scripting Host: Microsoft's Windows
       Scripting Host is required by the Microsoft Windows Installer.
       Older versions of Windows did not include the Windows Scripting
       Host. To check if your system has the Windows Scripting Host,
       select Run from the Windows Start menu, and enter wscript. If the
       Windows Script Host Setting dialog appears, WSH is installed on
       your system. If it doesn't, download the WSH from Microsoft
       website.

   Miscellaneous Prerequisites:
     * Perl Dev Kit: In order to build executable programs, ActiveX
       controls and Windows services in Perl, you must have ActiveState's
       Perl Dev Kit version 3.1 or greater installed on your system.

Installing the Komodo License on Windows

   Komodo IDE requires a 21-day Trial or Permanent license to run. For a
   21-day Trial, follow the license installation prompts when running
   Komodo for the first time. To install a Permanent license:
     * Download the license installer from the My Downloads page.
     * Double-click the downloaded installer.

Upgrading from Previous Komodo Versions

   Newer versions of Komodo should not be installed in the same directory
   as older versions. For major version upgrades (e.g. 3.5.3 to 4.0) the
   installer will automatically put Komodo in a new directory. However
   for "point" release upgrades (e.g. 3.5 to 3.5.3), you should
   completely uninstall the older version before installing the new one.

Installing Komodo on Windows

   Before you start:
     * If you intend to run the installation from a shared network drive,
       your system must have SYSTEM rights (or greater) to the directory
       from which the installation is run. Alternatively, run the
       installation from a local drive.

   To install Komodo on Windows:
    1. Ensure you have the prerequisite hardware and software.
    2. Download the Komodo installer file.
    3. Double-click the installer file and follow the instructions.

   When installation is complete, you will see an ActiveState Komodo icon
   on your desktop.

Command Line Installation Options

   Komodo can also be installed from the command line. For example:

    c:\> msiexec.exe /i Komodo-<version>.msi

   Komodo's installer uses Windows Installer technology, which allows you
   to partially control the install from the command line. For example:

Installing the MSI in Silent Mode

   You can have the Komodo installer run with a reduced user interface.
   For example, the following will install silently and only open a
   dialog when the installation is complete.
    c:\> msiexec.exe /i Komodo-<version>.msi /qn+

   The following will install with no dialog at all.

    c:\> msiexec.exe /i Komodo-<version>.msi /q

Turning on Logging

   You can generate a log of the Komodo installation with the following
   command:

    c:\> msiexec.exe /i Komodo-<version>.msi /L*v install.log

Controlling the Install Directory

   Command line options can be used to configure Komodo installation
   properties. The following will install Komodo to "E:\myapps\Komodo",
   instead of the default location:

    c:\> msiexec.exe /i Komodo-<version>.msi INSTALLDIR=D:\myapps\Komodo

Controlling Which Features Get Installed

   Komodo is divided into a number of distinct features. In the
   "Customize Setup" dialog you can select which features to install. You
   can also do this on the command line with the ADDLOCAL property. For
   example, the following command will install just the core Komodo
   functionality (i.e. not the PyWin32 extensions or the documentation.

    c:\> msiexec.exe /i Komodo-<version>.msi ADDLOCAL=core

   The current set of Komodo features are:
    core                 Komodo core
        env              Windows environment settings
            desktop      Desktop shortcut
            quicklaunch  Quick launch shortcut
            register     Register this as the default Komodo
        docs             Documentation

   The hierarchy denotes dependencies (i.e. to install quicklaunch you
   must install the env.

Uninstalling Komodo on Windows

   To install Komodo 4.2, you must first uninstall any
   other Komodo 4.2 installation. You may, however,
   install Komodo 4.2 side-by-side with other Komodo
   X.Y version (for example Komodo 3.1) as long as you install to a
   separate and unique directory. Komodo 4.2 will import
   settings from previous Komodo versions.

Starting Komodo on Windows

   To start Komodo on Windows, use one of the following methods:
     * Double-click the desktop icon.
     * Select Start|Programs|ActiveState Komodo|Komodo.
     * Add the Komodo install directory to your PATH environment
       variable, then from the command line prompt, enter komodo.

Uninstalling Komodo on Windows

   To uninstall Komodo, select Start|Programs|ActiveState Komodo|Modify
   or Uninstall Komodo.

   Alternatively, use the Add/Remove Programs menu (accessible from the
   Windows Control Panel).

Mac OS X

Prerequisites

Hardware Requirements

     * Architecture: PowerPC (G4 processor or faster) or Intel
     * 256 MB RAM or more
     * 90 MB hard disk space

Operating System Requirements

     * Mac OS X 10.3 (Panther) or later

Installing the Komodo License on OS X

   Komodo IDE requires a 21-day Trial or Permanent license to run. For a
   21-day Trial, follow the license installation prompts when running
   Komodo for the first time. To install a Permanent license:
     * Download the license installer from the My Downloads page.
     * Double-click the downloaded zip file to unpack it (this is done
       automatically if you are using Safari), and double-click the
       enclosed license installer.

Upgrading from Previous Komodo Versions

   Newer versions of Komodo should not be installed in the same directory
   as older versions. You must uninstall the older version (or rename the
   .app) before installing the new one.

Installing Komodo on Mac OS X

   To install Komodo:
     * Download the Komodo disk image
       (Komodo-Professional-<version>-macosx-<powerpc|x86>.dmg).
     * If the browser does not automatically mount the disk image and
       open the mounted folder in Finder, double-click the .dmg file to
       do so.
     * Open a new Finder window. Drag the Komodo icon from the mounted
       folder to the Applications folder.
     * If desired, drag the Komodo icon into the Dock.

Starting Komodo on OS X

   Click the Komodo icon in the Dock or the Applications folder.

Uninstalling Komodo on OS X

   Drag the Komodo icon into the Trash.

Linux

Prerequisites

Hardware Requirements

     * Intel x86 processor, 500 MHz (or faster) with 256 MB RAM (or
       greater)
     * 100 MB hard disk space
     * up to 200 MB of temporary hard disk space during installation

Operating System Requirements

   Supported operating systems:

   The following platforms are officially supported.
     * Red Hat Enterprise Linux 3 (WS, ES and AS)
     * SuSE 9.x
     * Ubuntu 5.10 or later

   Other operating systems:

   Komodo can also be run on the following platforms. This version of
   Komodo has not necessarily been tested on these platforms;
   platform-specific bugs may or may not be fixed.
     * Fedora Core 2
     * Red Hat 9.x
     * SuSE 8.2
     * Debian
     * FreeBSD (with Linux binary compatibility)
     * Gentoo

Software Prerequisites on Linux

   Installation Prerequisites:
     * glibc 2.1 (or higher) and libjpeg.so.62 (or higher): These
       libraries are included in standard Linux distributions.
     * libstdc++5 (or higher)

Adding Perl or Python to the PATH Environment Variable

   To add Perl or Python to the PATH environment variable, do one of the
   following:
     * Modify your PATH environment variable. For example, if you use the
       Bash shell, add the following line to your ~/.bashrc file:

          export PATH=<installdir>/bin:$PATH

       ...where <installdir> points to the directory where you installed
       ActivePerl or ActivePython.
     * Create a symbolic link to the Perl or Python executable. For
       example, for ActivePerl, enter:

          ln -s <installdir>/bin/perl /usr/local/bin/perl

       For ActivePython, enter:

          ln -s <installdir>/bin/python /usr/local/bin/python

       ...where <installdir> points to the directory where you installed
       ActivePerl or ActivePython.

Installing the Komodo License on Linux

   Komodo IDE requires a 21-day Trial or Permanent license to run. For a
   21-day Trial, follow the license installation prompts when running
   Komodo for the first time. To install a Permanent license:
     * Download the license installer from the My Downloads page.
     * Change the permissions on the downloaded file to allow execution
       (e.g. `chmod +x Komodo_<version>_<license#>.bin`)
     * Run the installer (e.g. `./Komodo_<version>_<license#>.bin`).

Upgrading from Previous Komodo Versions

   Newer versions of Komodo should not be installed in the same directory
   as older versions. For major version upgrades (e.g. 3.5.3 to 4.0) the
   installer will automatically put Komodo in a new directory. However
   for "point" release upgrades (e.g. 3.5 to 3.5.3), you should
   completely uninstall the older version before installing the new one.

Installing Komodo on Linux

   This version of Komodo allows non-root installation on Linux. Note,
   however, that the user who executes the license file will be the user
   who is licensed to use the software.

   To install Komodo on Linux:
    1. Download the Komodo installer (.tar.gz file) into a convenient
       directory.
    2. Unpack the tarball:

        tar -xvzf Komodo-<version>-<platform>.tar.gz

    3. Change to the new directory:

        cd Komodo-<version>-<platform>

    4. Run the install script ("install.sh"):

        ./install.sh

    5. Answer the installer prompts:
    6.
          + Specify where you want Komodo installed, or press 'Enter' to
            accept the default location
            (/home/<username>/Komodo-<IDE|Edit>-x.y).The -I option can be
            used to specify the install directory. For example:

              ./install.sh -I ~/opt/Komodo-IDE-4.2

            If multiple users are sharing the system and will be using
            the same installation, install Komodo in a location every
            user can access (e.g. /opt/Komodo-x.x/ or
            /usr/local/Komodo-x.x/).
            Note:
               o Each Komodo user requires their own license key.
               o Do not install Komodo in a path that contains spaces or
                 non-alphanumeric characters.
               o Be sure to install Komodo into its own directory (i.e.
                 not directly in an existing directory containing shared
                 files and directories such as /usr/local).
    7. Once the installer has finished, add Komodo to your PATH with one
       of the following:
          + Add Komodo/bin to your PATH directly:

              export PATH=<installdir>/bin;:$PATH

          + Add a symlink to Komodo/bin/komodo from another directory in
            your PATH:

              ln -s <installdir>/bin/komodo /usr/local/bin/komodo

            Note: Creating symlinks in system directories such as
            /usr/bin requires root access.

   After completing the installation, you can delete the temporary
   directory where the Komodo tarball was unpacked.

Starting Komodo on Linux

   To start Komodo on Linux enter `komodo` at the command line or create
   a shortcut on your desktop or in your toolbar using the full path to
   the komodo executable.

Uninstalling Komodo on Linux

   To uninstall Komodo on Linux:
    1. Delete the directory that Komodo created during installation.
    2. If you wish to delete your Komodo preferences, delete the
       ~/.komodo directory. If you do not delete this directory,
       subsequent installations of Komodo will use the same preferences.

   Note: You cannot relocate an existing Komodo installation to a new
   directory by simply moving it. You must uninstall Komodo from the
   existing location and reinstall it in the new location.

Language and Debugging Prerequisites

     * Debugging: If firewall software is installed on the system, it
       must be configured to allow Komodo to access the network during
       remote debugging.
     * Perl: Perl 5.6 or greater is required to debug Perl programs.
       Download the latest version of ActivePerl from the ActiveState
       website. Ensure that the directory location of the Perl
       interpreter (by default, C:\perl) is included in your system's
       PATH environment variable. Some advanced features, such as
       background syntax checking and remote debugging, require
       ActivePerl.
     * Python: Python 1.5.2 or greater is required to debug Python
       programs. You can download the latest version of ActivePython from
       the ActiveState website. Ensure that the directory location of the
       Python interpreter (by default C:\Pythonxx (where "xx" is the
       Python version)) is included in your system's PATH environment
       variable. Some advanced features, such as background syntax
       checking and remote debugging, require ActivePython. Python 1.5.2
       or greater and a fully configured Tkinter installation are
       required to create Python dialogs with the GUI Builder.
     * PHP: PHP 4.0.5 or greater is required for PHP syntax checking. PHP
       4.3.10 or greater is required to debug PHP programs. Debugging and
       syntax checking are also available for PHP 5.0.3 or greater.
       Download PHP from http://www.php.net/downloads.php. Ensure that
       the directory location of the PHP interpreter (by default C:\PHP)
       is included in your system's PATH environment variable. For
       complete instructions for configuring Komodo and PHP, see
       Configuring the PHP Debugger. PHP debugging extensions are
       available on ASPN, the ActiveState Programmer Network.
     * Tcl: Tcl 7.6 or greater is required to debug Tcl programs.
       Download the latest version of ActiveTcl from the ActiveState
       website.
     * Ruby: Ruby 1.8 or greater is required to debug Ruby programs.
       Download the latest version of Ruby from
       http://rubyinstaller.rubyforge.org/wiki/wiki.pl. Cygwin-based
       versions of Ruby are currently unsupported.

Source Code Control Integration Prerequisites

     * CVS Source Control Integration: Requires CVS, which is available
       from http://www.nongnu.org/cvs/, or the latest stable version of
       CVSNT, which is available from http://www.cvsnt.org/wiki/.
     * CVS Source Control Integration using Putty (Windows): Requires
       Putty version 0.52 or greater.
     * Perforce Source Control Integration: Requires a connection to a
       Perforce server with version 99.1 or later.
     * Subversion Source Code Control Integration: Requires the
       Subversion client, which is available from
       http://subversion.tigris.org/.
