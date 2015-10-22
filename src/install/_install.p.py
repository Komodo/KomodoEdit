#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
# 
# The contents of this file are subject to the Mozilla Public License
# Version 1.1 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
# 
# Software distributed under the License is distributed on an "AS IS"
# basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
# License for the specific language governing rights and limitations
# under the License.
# 
# The Original Code is Komodo code.
# 
# The Initial Developer of the Original Code is ActiveState Software Inc.
# Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
# ActiveState Software Inc. All Rights Reserved.
# 
# Contributor(s):
#   ActiveState Software Inc
# 
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
# 
# ***** END LICENSE BLOCK *****
#
#********************************************************************
# WARNING: Do not run this script directly. Run the main 
#          "__MAIN_INSTALL_SCRIPT__" which will launch this script
#          properly.
#********************************************************************

"""
    __MAIN_INSTALL_SCRIPT__ - ActiveState Komodo "AS Package" install script

    Usage:
        __MAIN_INSTALL_SCRIPT__ [options...]

    General Options:
        -h, --help          print this help and exit
        -v, --verbose       verbose output

        -I, --install-dir <dir>     specify install directory
        -s, --suppress-shortcut     do NOT install desktop shortcut

    When called without arguments this script will interactively install
    Komodo. If the install dir is specified then Komodo will be
    installed without interaction.
"""

import sys
import os
from os.path import (abspath, expanduser, normpath, join, dirname, basename,
                     isdir, islink, exists, relpath)
import shutil
import tempfile
import getopt
import logging
import pprint
import re
import subprocess
from glob import glob

import which

class Error(Exception):
    pass



#---- globals

log = logging.getLogger("install")
gKomodoVer = "__KOMODO_MAJOR_MINOR__"
gDefaultInstallDir = "__DEFAULT_INSTALLDIR__"
gInstallLog = "koinstall.log"



#---- internal support routines

def _rmtreeOnError(rmFunction, filePath, excInfo):
    if excInfo[0] == OSError:
        # presuming because file is read-only
        os.chmod(filePath, 0777)
        rmFunction(filePath)

def _rmtree(dname):
    shutil.rmtree(dname, 0, _rmtreeOnError)

# Recipe: banner (1.0) in /Users/trentm/tm/recipes/cookbook
def _banner(text, ch='=', length=78):
    """Return a banner line centering the given text.

        "text" is the text to show in the banner. None can be given to have
            no text.
        "ch" (optional, default '=') is the banner line character (can
            also be a short string to repeat).
        "length" (optional, default 78) is the length of banner to make.

    Examples:
        >>> banner("Peggy Sue")
        '================================= Peggy Sue =================================='
        >>> banner("Peggy Sue", ch='-', length=50)
        '------------------- Peggy Sue --------------------'
        >>> banner("Pretty pretty pretty pretty Peggy Sue", length=40)
        'Pretty pretty pretty pretty Peggy Sue'
    """
    if text is None:
        return ch * length
    elif len(text) + 2 + len(ch)*2 > length:
        # Not enough space for even one line char (plus space) around text.
        return text
    else:
        remain = length - (len(text) + 2)
        prefix_len = remain / 2
        suffix_len = remain - prefix_len
        if len(ch) == 1:
            prefix = ch * prefix_len
            suffix = ch * suffix_len
        else:
            prefix = ch * (prefix_len/len(ch)) + ch[:prefix_len%len(ch)]
            suffix = ch * (suffix_len/len(ch)) + ch[:suffix_len%len(ch)]
        return prefix + ' ' + text + ' ' + suffix


if sys.platform.startswith("win"):
    def _getSystemDrive():
        try:
            return os.environ["SystemDrive"]
        except KeyError:
            raise Error("'SystemDrive' environment variable is not set")


def _getDefaultInstallDir():
    default = gDefaultInstallDir
    if sys.platform.startswith("win") and\
       default.lower().find("%systemdrive%") != -1:
        default = re.compile("%SystemDrive%", re.I).sub(_getSystemDrive(),
                                                        default)
    return default

def _askYesNo(question, default="yes"):
    """Ask the user the given question and their answer.
    
    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is one of "yes" or "no".
    """
    valid = {"yes":"yes",   "y":"yes",  "ye":"yes",
             "no":"no",     "n":"no"}
    if default == None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise Error("invalid default answer: '%s'" % default)

    while 1:
        sys.stdout.write(question + prompt)
        choice = raw_input().lower()
        #sys.stdout.write('\n')
        if default is not None and choice == '':
            return default
        elif choice in valid.keys():
            return valid[choice]
        else:
            sys.stdout.write("Please repond with 'yes' or 'no' "\
                             "(or 'y' or 'n').\n")


def _validateInstallDir(installDir):
    if exists(installDir) and not isdir(installDir):
        raise Error("cannot install to '%s': exists and is not a directory"
                    % installDir)


# Recipe: run (0.5.3) in C:\trentm\tm\recipes\cookbook
_RUN_DEFAULT_LOGSTREAM = ("RUN", "DEFAULT", "LOGSTREAM")
def __run_log(logstream, msg, *args, **kwargs):
    if not logstream:
        pass
    elif logstream is _RUN_DEFAULT_LOGSTREAM:
        try:
            log
        except NameError:
            pass
        else:
            if hasattr(log, "debug"):
                log.debug(msg, *args, **kwargs)
    else:
        logstream(msg, *args, **kwargs)

def _run(cmd, logstream=_RUN_DEFAULT_LOGSTREAM):
    """Run the given command.

        "cmd" is the command to run
        "logstream" is an optional logging stream on which to log the 
            command. If None, no logging is done. If unspecifed, this 
            looks for a Logger instance named 'log' and logs the command 
            on log.debug().

    Raises OSError is the command returns a non-zero exit status.
    """
    __run_log(logstream, "running '%s'", cmd)
    retval = os.system(cmd)
    if hasattr(os, "WEXITSTATUS"):
        status = os.WEXITSTATUS(retval)
    else:
        status = retval
    if status:
        #TODO: add std OSError attributes or pick more approp. exception
        raise OSError("error running '%s': %r" % (cmd, status))

def _run_in_dir(cmd, cwd, logstream=_RUN_DEFAULT_LOGSTREAM):
    """Run the given command in the given working directory.

        "cmd" is the command to run
        "cwd" is the directory in which the commmand is run.
        "logstream" is an optional logging stream on which to log the 
            command. If None, no logging is done. If unspecifed, this 
            looks for a Logger instance named 'log' and logs the command 
            on log.debug().

    Raises OSError is the command returns a non-zero exit status.
    """
    old_dir = os.getcwd()
    try:
        os.chdir(cwd)
        __run_log(logstream, "running '%s' in '%s'", cmd, cwd)
        _run(cmd, logstream=None)
    finally:
        os.chdir(old_dir)

def _run_and_capture(argv):
    log.debug("running '%s'", ' '.join(argv))
    p = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    return stdout, stderr, p.returncode

def _ensure_executable(filename):
    try:
        filestat = os.stat(filename)
        perms = 0700 | (filestat.st_mode & (0077))
        os.chmod(filename, perms)
    except Exception, ex:
        log.warn("could not set exec permissions on path %r - %s", filename, ex)

def _install_desktop_shortcut(absInstallDir, suppressShortcut):
    """Install a desktop shortcut as appropriate.

        "absInstallDir" is the absolute path to which Komodo was
            just installed
        "suppressShortcut" is a boolean indicating if creation
            of the desktop shortcut is to be suppressed.

    - If we are install under $HOME then look for and install the
      desktop shortcut to $HOME/Desktop, if it exists.
    - Otherwise, attempt to add the .desktop shortcut to shared
      applications shortcuts dir.
    (See bug 32351 for details).
    """
    # Put together the shortcut content.
    content = """\
[Desktop Entry]
Encoding=UTF-8
Name=__GNOME_DESKTOP_NAME__
GenericName=__GNOME_DESKTOP_GENERIC_NAME__
Comment=__PRODUCT_TAG_LINE__
Exec=%s/lib/mozilla/komodo %%F
Icon=%s/share/icons/komodo48.png
Terminal=false
Type=Application
MimeType=text/plain;
Categories=__GNOME_DESKTOP_CATEGORIES__
""" % (absInstallDir, absInstallDir)
    shortcutName = "__GNOME_DESKTOP_SHORTCUT_NAME__"

    class ShortcutInstallError(Exception):
        pass

    # Write desktop file to a temporary file.
    tempDir = tempfile.mkdtemp()
    try:
        tempPath = join(tempDir, shortcutName)
        file(tempPath, "w").write(content)

        if suppressShortcut:
            raise ShortcutInstallError("shortcut suppressed by user")

        # Use 'xdg-desktop-menu' and 'xdg-desktop-icon' if it's available.
        xdg_exe_name = 'xdg-desktop-menu'
        try:
            xdg_exe = which.which(xdg_exe_name)
        except which.WhichError:
            pass
        else:
            try:
                _run("xdg-desktop-menu install --novendor %s" % (tempPath))
                _run("xdg-desktop-icon install --novendor %s" % (tempPath))
                log.info("%r created successfully", shortcutName)
                return
            except OSError:
                # Fallback to manual install.
                pass

        # Determine if installing under HOME or to shared area.
        HOME = os.environ.get("HOME", None)
        if not HOME:
            raise ShortcutInstallError("no HOME environment variable")
        elif absInstallDir.startswith(HOME):
            shortcutDir = join(HOME, "Desktop")
        else:
            shortcutDir = "/usr/share/applications"
        shortcutPath = join(shortcutDir, shortcutName)

        # Attempt to write the Komodo shortcut.
        # (We DO overwrite an existing such shortcut.)
        if not exists(shortcutDir):
            raise ShortcutInstallError("'%s' does not exist" % shortcutDir)
        else:
            shutil.copy(tempPath, shortcutPath)
            # Ensure the desktop shortcut has executable permissions.
            _ensure_executable(shortcutPath)
    except (EnvironmentError, ShortcutInstallError), ex:
        fallbackDir = join(absInstallDir, "share", "desktop")
        fallbackPath = join(fallbackDir, shortcutName)
        try:
            if not exists(fallbackDir):
                os.makedirs(fallbackDir)
            shutil.copy(tempPath, fallbackPath)
            # Ensure the backup desktop shortcut has executable permissions.
            _ensure_executable(fallbackPath)
        except EnvironmentError, ex2:
            log.warn("unexpected error creating fallback .desktop file "
                     "'%s': %s", fallbackPath, ex2)
        else:
            log.warn("did not install desktop shortcut: %s "
                     "(a Komodo .desktop file has been created in '%s' "
                     "that you may install manually)",
                     ex, fallbackPath)
    else:
        log.info("'__GNOME_DESKTOP_NAME__' desktop shortcut created at '%s'",
                 shortcutPath)
    finally:
        try:
            _rmtree(tempDir)
        except:
            pass

def _gen_so_paths(basedir):
    for dirpath, dirnames, filenames in os.walk(basedir):
        for filename in filenames:
            if filename.endswith(".so"):
                yield join(dirpath, filename)

def _selinux_prepare(absInstallDir):
    """If this is Linux and SELinux is installed and enabled,
    then we need to set the security context on the SciMoz plugin
    to allow shared object text relocation.

    See bug 43260 and bug 46275 for details.
    """
    if not sys.platform.startswith("linux"):
        return

    import selinuxlib
    selinux = selinuxlib.SELinux()
    
    if not selinux.is_installed():
        log.debug("SELinux is not installed.")
        return
    log.debug("SELinux is installed.")

    # We must allow Komodo to have stack execution privileges, which is
    # required by certain Python modules (ssl, hashlib), otherwise Komodo
    # will fail to register some core PyXPCOM components - bug 85504.
    komodoBin = join(absInstallDir, "lib", "mozilla", "komodo")
    selinux.allow_stack_execution(komodoBin)

    for so_path in _gen_so_paths(absInstallDir):
        if not selinux.is_path_labeled(so_path):
            log.debug("%s: setting context just won't work, skipping", 
                      so_path)
            continue
        # Trying these covers RHEL (texrel_shlib_t), FC5 (textrel_shlib_t)
        # and CentOS (shlib_t).
        contexts_to_try = ["texrel_shlib_t", "textrel_shlib_t", "shlib_t"]
        context = selinux.context_from_path(so_path)
        if context is not None:
            context_to_try = context.split(':')[-1]
            if context_to_try not in contexts_to_try:
                contexts_to_try.append(context_to_try)
        for context_to_try in contexts_to_try:
            log.debug("trying chcon(%r, %r)", so_path, context_to_try)
            try:
                selinuxlib.chcon(so_path, context_to_try)
            except selinuxlib.SELinuxError, ex:
                pass
            else:
                break
        else:
            msg = ("could not set SELinux security context for "
                   "'%s': '%s' contexts failed"
                   % (so_path, "', '".join(contexts_to_try)))
            if selinux.is_enabled():
                raise Error(msg)
            else:
                log.warn(msg + " (this can be safely ignored if you do "
                               "not use SELinux on your system)")
                break

def _symlink_komodo_executable(absInstallDir):
    # Komodo comes with a stub shell script that will execute the main
    # Komodo executable, we often don't need the stub and can instead use
    # a symlink to the main executable. The stub is just uses as a backup
    # for when we cannot use symlinks.
    komodoBin = join("..", "lib", "mozilla", "komodo")  # relative path
    komodoStub = join(absInstallDir, "bin", "komodo")
    komodoStubBackup = komodoStub+".sh"
    os.rename(komodoStub, komodoStubBackup)
    try:
        os.symlink(komodoBin, komodoStub)
        os.remove(komodoStubBackup)
    except:
        # Couldn't make a symlink - keep using the stub.
        os.rename(komodoStub, komodoStubBackup)

def _install(installDir, userDataDir, suppressShortcut, destDir=None):
    normInstallDir = normpath(expanduser(installDir))
    absInstallDir = abspath(normInstallDir)
    pyInstallDir = join(absInstallDir, "lib", "python")
    mozInstallDir = join(absInstallDir, "lib", "mozilla")
    log.info("Installing ActiveState Komodo to '%s'...", normInstallDir)
    _validateInstallDir(absInstallDir)
    log.debug("redirect userDataDir to '%s'", userDataDir)
    log.debug("user environment: %s", pprint.pformat(dict(os.environ)))

    # "destDir", if defined, is the ultimate final install location. We
    # want to relocate to that dir.
    if destDir is None:
        absRelocDir = absInstallDir
        pyRelocDir = pyInstallDir
    else:
        absRelocDir = abspath(normpath(expanduser(destDir)))
        pyRelocDir = join(absRelocDir, "lib", "python")

    # copy the entire "Komodo" tree to the installDir
    if not exists(absInstallDir):
         os.makedirs(absInstallDir)
    for path in glob(join(dirname(dirname(__file__)), "INSTALLDIR", "*")):
        if isdir(path):
            shutil.copytree(path, join(absInstallDir, basename(path)),
                            symlinks=True)
        else:
            shutil.copy2(path, absInstallDir)

    log.debug("Preparing internal Python...")
    import activestate
    activestate.relocate_python(pyRelocDir,
                                verbose=log.isEnabledFor(logging.DEBUG))

    # Make sure that we use symlinks for libpython.so, bug 98337
    pyLibName = "libpython%s.%s.so" % sys.version_info[:2]
    pyLibReal = abspath(join(pyInstallDir, "lib", "%s.1.0" % (pyLibName,)))
    pyLibs = set(abspath(join(libdir, libname))
                 for libdir in (mozInstallDir, join(pyInstallDir, "lib"))
                 for libname in (pyLibName, "%s.1.0" % (pyLibName,)))
    pyLibs.discard(pyLibReal)
    if not exists(pyLibReal) or islink(pyLibReal):
        # we don't have the real file? See if we can grab one of the others
        log.warning("%s is not a file; trying to find alternative...", pyLibReal)
        for pyLib in pyLibs:
            if not exists(pyLib) or islink(pyLib):
                continue
            if exists(pyLibReal):
                os.unlink(pyLibReal)
            os.rename(pyLib, pyLibReal)
            break
        else:
            log.error("Could not find a valid libpython; your Komodo is broken."
                      "  Please try re-downloading the installer.")
            sys.exit(1)
    for pyLib in pyLibs:
        if exists(pyLib):
            os.unlink(pyLib)
        try:
            os.symlink(relpath(pyLibReal, dirname(pyLib)), pyLib)
        except OSError:
            log.error("Failed to create a symlink at %s; Komodo will be broken."
                      "  Komodo needs to be installed on a filesystem that "
                      "supports symlinks.", pyLib)
            sys.exit(1)

    log.debug("pre-compile .py files in siloed Python")
    pyLibDir = join(pyInstallDir, "lib", "python%s.%s" % sys.version_info[:2])
    # Skip .pyc's only, just .pyo's are necessary because we always run
    # Python in optimized mode.
    cmds = ['"%s" -W "ignore:hex/oct constants" -O "%s/compileall.py" '
            '-q -x test/ "%s"'
            % (sys.executable, pyLibDir, pyLibDir)]
    for cmd in cmds:
        log.debug("running '%s'" % cmd)
        retval = os.system(cmd)
        if retval:
            log.warn("error running '%s'" % cmd)

    # Configure siloed GTK2 libs (if any).
    log.debug("Configuring GTK2...")
    files = [join(mozInstallDir, "pango", "pangorc"),
             join(mozInstallDir, "pango", "pango.modules"),
             join(mozInstallDir, "gdk-pixbuf", "gdk-pixbuf.loaders")]
    token = "__PATH_TO_INSTALLED_KOMODO__"
    for file in files:
        if not exists(file):
            continue
        log.debug("fixing up '%s'", file)
        fin = open(file, 'r')
        try:
            content = fin.read()
        finally:
            fin.close()
        content = content.replace(token, absInstallDir)
        os.chmod(file, 0644)
        fout = open(file, 'w')
        try:
            fout.write(content)
        finally:
            fout.close()

    _symlink_komodo_executable(absInstallDir)
    _install_desktop_shortcut(absInstallDir, suppressShortcut)
    _selinux_prepare(absInstallDir)

    print """
%s
__GNOME_DESKTOP_NAME__ has been successfully installed to:
    %s
    
You might want to add 'komodo' to your PATH by adding the 
install dir to you PATH. Bash users can add the following
to their ~/.bashrc file:

    export PATH="%s/bin:$PATH"

Or you could create a symbolic link to 'komodo', e.g.:

    ln -s "%s/bin/komodo" /usr/local/bin/komodo

Documentation is available in Komodo or on the web here:
    http://docs.activestate.com/komodo

Please send us any feedback you have through one of the
channels below:
    komodo-feedback@activestate.com
    irc://irc.mozilla.org/komodo
    https://github.com/Komodo/KomodoEdit/issues

Thank you for using Komodo.
%s
""" % (_banner(None), absInstallDir, absInstallDir, absInstallDir,
       _banner(None))



#---- main public functions

def interactiveInstall(suppressShortcut):
    default = _getDefaultInstallDir()
    sys.stdout.write("""\
Enter directory in which to install Komodo. Leave blank and
press 'Enter' to use the default [%s].
Install directory: """ % default)
    installDir = raw_input().strip()
    if not installDir:
        installDir = default

    norm = normpath(expanduser(installDir))
    if isdir(norm):
        sys.stdout.write("""
'%s' already exists. Installing over an existing
Komodo installation may have unexpected results. Are you
sure you would like to proceed with the installation?
""" % installDir)
        choice = _askYesNo("Proceed?", default="no")
        if choice == "yes":
            pass
        elif choice == "no":
            print "Aborting install."
            return
    elif exists(norm):
        raise Error("'%s' exists and is not a directory" % installDir)

    print
    install(installDir, suppressShortcut)

def install(installDir, suppressShortcut, destDir=None):
    # Redirect the "user data dir" to a temp location to avoid
    # the problem described in bug 32270 ("sudo ./install.sh" results in
    # interfering root-owned stuff in ~/.komodo).
    tempDir = join(tempfile.gettempdir(), "koinstall.%s" % os.getpid())
    try:
        return _install(installDir, tempDir, suppressShortcut,
                        destDir=destDir)
    finally:
        if exists(tempDir):
            log.debug("removing temp user data dir: '%s'", tempDir)
            _rmtree(tempDir)



#---- mainline

# Recipe: pretty_logging (0.1.1) in C:\trentm\tm\recipes\cookbook
class _PerLevelFormatter(logging.Formatter):
    """Allow multiple format string -- depending on the log level.
    
    A "fmtFromLevel" optional arg is added to the constructor. It can be
    a dictionary mapping a log record level to a format string. The
    usual "fmt" argument acts as the default.
    """
    def __init__(self, fmt=None, datefmt=None, fmtFromLevel=None):
        logging.Formatter.__init__(self, fmt, datefmt)
        if fmtFromLevel is None:
            self.fmtFromLevel = {}
        else:
            self.fmtFromLevel = fmtFromLevel
    def format(self, record):
        record.levelname = record.levelname.lower()
        if record.levelno in self.fmtFromLevel:
            #XXX This is a non-threadsafe HACK. Really the base Formatter
            #    class should provide a hook accessor for the _fmt
            #    attribute. *Could* add a lock guard here (overkill?).
            _saved_fmt = self._fmt
            self._fmt = self.fmtFromLevel[record.levelno]
            try:
                return logging.Formatter.format(self, record)
            finally:
                self._fmt = _saved_fmt
        else:
            return logging.Formatter.format(self, record)


def main(argv):
    # Setup logging.
    root = logging.getLogger() # root logger

    hdlr = logging.FileHandler(gInstallLog, mode='w')
    formatter = logging.Formatter('%(asctime)s: %(levelname)s: %(name)s: %(message)s')
    hdlr.setFormatter(formatter)
    root.setLevel(logging.WARN)
    root.addHandler(hdlr)

    console = logging.StreamHandler()
    defaultFmt = "%(name)s: %(levelname)s: %(message)s"
    infoFmt = "%(name)s: %(message)s"
    fmtr = _PerLevelFormatter(fmt=defaultFmt,
                              fmtFromLevel={logging.INFO: infoFmt})
    console.setFormatter(fmtr)
    # Specifically don't log selinux messages on the console (bug 45757).
    onlyInstallFilter = logging.Filter("install")
    console.addFilter(onlyInstallFilter)
    console.setLevel(logging.INFO)
    root.addHandler(console)

    # Parse options.
    try:
        opts, args = getopt.getopt(argv[1:], "vhI:s",
            ["verbose", "help", "install-dir=", "suppress-shortcut",
             "dest-dir="])
    except getopt.GetoptError, ex:
        log.error(str(ex))
        log.error("Try `__MAIN_INSTALL_SCRIPT__ --help'.")
        return 1
    installDir = None
    destDir = None
    suppressShortcut = False
    for opt, optarg in opts:
        if opt in ("-h", "--help"):
            sys.stdout.write(__doc__)
            return
        elif opt in ("-v", "--verbose"):
            console.setLevel(logging.DEBUG)
        elif opt in ("-I", "--install-dir"):
            installDir = optarg
        elif opt in ("-s", "--suppress-shortcut"):
            suppressShortcut = True
        elif opt in ("--dest-dir",):
            destDir = optarg
    if destDir and not installDir:
        log.error("must use -I|--install-dir to use --dest-dir")
        return 1

    try:
        if installDir is None:
            interactiveInstall(suppressShortcut)
        else:
            install(installDir, suppressShortcut, destDir=destDir)
    except (EnvironmentError, Error), ex:
        log.error(str(ex))
        log.debug("exception info:", exc_info=True)
        return 1
    except KeyboardInterrupt:
        log.debug("user abort")
        pass

if __name__ == "__main__":
    __file__ == sys.argv[0]
    sys.exit( main(sys.argv) )

