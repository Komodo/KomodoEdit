#!python
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

# Initialization Services for Komodo

# mozilla sets LC_NUMERIC which messes up the python parser if the locale
# uses something other than a period for decimal seperator.  We reset it
# here to make all consecutive files get parsed correctly.
# bug 30327
import locale
locale.setlocale(locale.LC_NUMERIC, 'C')

import sys
import os
import re
from pprint import pprint

if sys.platform == "win32":
    # Force the import of the correct PyWin32 DLLs on Windows.
    # PyWin32 has special shims for importing pywintypes and pythoncom
    # directly to ensure that the right pywintypesXY.dll and pythoncomXY.dll
    # get found and loaded. If our Python attempts to load these DLLs via,
    # say, "import win32api" -- which will use LoadLibrary(DLLFILE) -- then
    # we are screwed: because an incompatible system one might get picked up.
    #
    import pywintypes
    import pythoncom

from xpcom import components, nsError, ServerException, COMException

import upgradeutils

import logging
log = logging.getLogger('koInitService')
## without calling basicConfig here, we do not get logging at all from
## the init service, and people get an error message about it.
#logging.basicConfig()
#log.setLevel(logging.DEBUG)

#---- support routines
# Always import timeline even if we don't use it - it already does nothing
# if disabled (but you still should check use_timeline so the figures are
# supressed if necessary.
import timeline

use_timeline = os.environ.has_key("KO_TIMELINE_PYOS") and timeline.getService() is not None
xpcom_profiler = os.environ.has_key("KO_PYXPCOM_PROFILE")

# #if BUILD_FLAVOUR == "dev"
if os.environ.has_key("KO_DEBUG_PORT"):
    try:
        from dbgp.client import brk
        brk(port=int(os.environ["KO_DEBUG_PORT"]))
    except Exception, e:
        log.exception(e)
        pass
# #endif

if use_timeline:
    def mktracer(callable, module, name):
        def proxy(*args, **kw):
            try:
                oldstat = os.stat
                os.stat = getattr(os, '_stat', os.stat)
                timer_name = "%s.%s" % (module.__name__, name)
                timeline.startTimer(timer_name)
                try:
                    return callable(*args, **kw)
                finally:
                    timeline.stopTimer(timer_name)
                    extra = "%s, %s" % (repr(args), repr(kw))
                    timeline.markTimer(timer_name, extra)
            finally:
                os.stat = oldstat

        setattr(module, name, proxy)
        setattr(module, '_'+name, callable)

    mktracer(os.listdir, os, 'listdir')
    mktracer(os.stat, os, 'stat')
    mktracer(os.popen, os, 'popen')
    mktracer(os.system, os, 'system')
    mktracer(os.getcwd, os, 'getcwd')

if xpcom_profiler:
    # insert the xpcom tracer
    import pyxpcomProfiler

# The following imports, two globals and two methods are used by the import
# timing stuff, which is enabled by uncommenting a line in the initialize()
# call of koInitService
import __builtin__, time
_old_import = __builtin__.__import__
_imported_modules = {}
def _timed_import(name, *args, **kw):
    t1 = time.clock()
    mod = _old_import(name, *args, **kw)
    dt = time.clock() - t1
    realname = mod.__name__
    if not _imported_modules.has_key(name):
        _imported_modules[name] = dt
        timeline.mark("%s\t%4.4f" % (realname, dt))
    else:
        _imported_modules[name] += dt
    return mod

module_tree = {}
current_module = module_tree
def _memory_import(name, *args, **kw):
    global current_module
    start = int(my_process_memory())
    current_module[name] = {}
    orig = current_module
    current_module = current_module[name]
    mod = _old_import(name, *args, **kw)
    end = int(my_process_memory())
    realname = mod.__name__
    if name.startswith(realname):
        realname = name
    mem = end-start
    if mem:
        timeline.mark("%s\t%s" % (realname, memoryrepr(mem)))
        current_module['memory'] = memoryrepr(mem)
    current_module = orig
    if not current_module[name]:
        del current_module[name]
    return mod


#----- interal support routines

def _isdir(dirname):
    """os.path.isdir() doesn't work for UNC mount points. Fake it."""
    if sys.platform[:3] == 'win' and dirname[:2] == r'\\':
        if os.path.exists(dirname):
            return os.path.isdir(dirname)
        try:
            os.listdir(dirname)
        except WindowsError:
            return 0
        else:
            return os.path.ismount(dirname)
    else:
        return os.path.isdir(dirname)


def _mkdir(newdir):
    """works the way a good mkdir should :)
        - already exists, silently complete
        - regular file in the way, raise an exception
        - parent directory(ies) does not exist, make them as well
    """
    if _isdir(newdir):
        pass
    elif os.path.isfile(newdir):
        raise OSError("a file with the same name as the desired " \
                      "dir, '%s', already exists." % newdir)
    else:
        head, tail = os.path.split(newdir)
        if head and not _isdir(head):
            _mkdir(head)
        #print "_mkdir %s" % repr(newdir)
        if tail:
            os.mkdir(newdir)


def _copy(src, dst):
    """works the way a good copy should :)
        - no source, raise an exception
        - destination directory, make a file in that dir named after src
        - source directory, recursively copy the directory to the destination
        - filename wildcarding allowed
    NOTE:
        - This copy CHANGES THE FILE ATTRIBUTES.
    """
    import string, glob, shutil

    assert src != dst, "You are try to copy a file to itself. Bad you! "\
                       "src='%s' dst='%s'" % (src, dst)
    # determine if filename wildcarding is being used
    # (only raise error if non-wildcarded source file does not exist)
    if string.find(src, '*') != -1 or \
       string.find(src, '?') != -1 or \
       string.find(src, '[') != -1:
        usingWildcards = 1
        srcFiles = glob.glob(src)
    else:
        usingWildcards = 0
        srcFiles = [src]

    for srcFile in srcFiles:
        if os.path.isfile(srcFile):
            if usingWildcards:
                srcFileHead, srcFileTail = os.path.split(srcFile)
                srcHead, srcTail = os.path.split(src)
                dstHead, dstTail = os.path.split(dst)
                if dstTail == srcTail:
                    dstFile = os.path.join(dstHead, srcFileTail)
                else:
                    dstFile = os.path.join(dst, srcFileTail)
            else:
                dstFile = dst
            dstFileHead, dstFileTail = os.path.split(dstFile)
            if dstFileHead and not _isdir(dstFileHead):
                _mkdir(dstFileHead)
            if _isdir(dstFile):
                dstFile = os.path.join(dstFile, os.path.basename(srcFile))
            #print "copy %s %s" % (srcFile, dstFile)
            mode = (os.access(srcFile, os.X_OK) and 0755 or 0644)
            if os.path.isfile(dstFile):
                # make sure 'dstFile' is writeable
                os.chmod(dstFile, mode)
            shutil.copy(srcFile, dstFile)
            # make the new 'dstFile' writeable
            os.chmod(dstFile, mode)
        elif _isdir(srcFile):
            srcFiles = os.listdir(srcFile)
            if not os.path.exists(dst):
                _mkdir(dst)
            for f in srcFiles:
                s = os.path.join(srcFile, f)
                d = os.path.join(dst, f)
                try:
                    _copy(s, d)
                except (IOError, os.error), why:
                    raise OSError("Can't copy %s to %s: %s"\
                          % (repr(s), repr(d), str(why)))
        elif not usingWildcards:
            raise OSError("Source file %s does not exist" % repr(srcFile))


def _rmtreeOnError(rmFunction, filePath, excInfo):
    if excInfo[0] == OSError:
        # presuming because file is read-only
        os.chmod(filePath, 0777)
        rmFunction(filePath)

def _rmtree(dirname):
    import shutil
    shutil.rmtree(dirname, 0, _rmtreeOnError)

def _splitall(path):
    r"""Split the given path into all constituent parts.

    Often, it's useful to process parts of paths more generically than
    os.path.split(), for example if you want to walk up a directory.
    This recipe splits a path into each piece which corresponds to a
    mount point, directory name, or file.  A few test cases make it
    clear:
        >>> _splitall('')
        []
        >>> _splitall('a/b/c')
        ['a', 'b', 'c']
        >>> _splitall('/a/b/c/')
        ['/', 'a', 'b', 'c']
        >>> _splitall('/')
        ['/']
        >>> _splitall('C:\\a\\b')
        ['C:\\', 'a', 'b']
        >>> _splitall('C:\\a\\')
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


def _diffFileAssociations(a, b):
    # Massage data for faster lookup.
    #       {'a': 1, 'b': 2}   ->   {('a', 1): True, ('b', 2): True}
    a_massaged = dict( ((k,v), True) for k,v in a.items() )
    b_massaged = dict( ((k,v), True) for k,v in b.items() )

    # Calculate the diffs. ('p' == pattern, 'ln' == language name)
    additions = [('+', p, ln) for (p, ln) in b_massaged.keys()
                               if (p, ln) not in a_massaged]
    deletions = [('-', p, ln) for (p, ln) in a_massaged.keys()
                               if (p, ln) not in b_massaged]
    diff = additions + deletions
    return diff



#---- main component implementation

class KoInitService:
    _com_interfaces_ = [components.interfaces.koIInitService]
    _reg_clsid_ = "{BAECC764-52AC-46dc-9428-D23F05247818}"
    _reg_contractid_ = "@activestate.com/koInitService;1"
    _reg_desc_ = "Komodo Init Service"

    def __init__(self):
        # We need this to make sure that logging handlers get registered before
        # we do _anything_ with loggers.
        loggingSvc = components.classes["@activestate.com/koLoggingService;1"].getService()
# #if BUILD_FLAVOUR == "dev"
        if sys.platform.startswith("win") and os.environ.has_key("KOMODO_DEBUG_BREAK"):
            print "KOMODO_DEBUG_BREAK in the environment - breaking into system debugger..."
            import win32api
            win32api.DebugBreak()
# #endif

        self._isInitialized = 0

    def setPlatformErrorMode(self):
        if sys.platform.startswith("win"):
            try:
                # Stop Windows displaying a dialog when removable
                # media is accessed, but not available
                # (eg, when a file from a floppy is on the MRU,
                # but no floppy is in the drive)
                from ctypes import windll
                SEM_FAILCRITICALERRORS = 1 # constant pulled from win32con to save memory
                windll.kernel32.SetErrorMode(SEM_FAILCRITICALERRORS)
            except ImportError:
                log.error("Could not import win32api/win32con to set the "\
                         "Win32 Error Mode.")

    def _safelyReloadSys(self):
        """Safely reload the sys module.

        Simply reloading the sys module will trounce the std handle
        directs that we have done in sitepyxpcom.py for output handling
        without a console.

        XXX Eventually all our setdefaultencoding should perhaps move
            out to our siloed Python's site.py (where
            sys.setdefaultencoding() is deleted) so that we don't have
            to reload(sys) at all.
        """
        savedStdout = sys.stdout
        savedStderr = sys.stderr
        reload(sys)
        sys.stdout = savedStdout
        sys.stderr = savedStderr

    def _setencoding(self,encoding=None):
        log.debug('in _setencoding, encoding=%r', encoding)
        try:
            if not encoding:
                encoding = locale.getdefaultlocale()
            if encoding is not None:
                #XXX Komodo code (specifically pref-intl.xul) requires
                #    the encoding name to be lowercase.
                encoding = (encoding[0], encoding[1].lower())

                self._safelyReloadSys()
                sys.setdefaultencoding(encoding[1])
                del sys.setdefaultencoding
                return encoding
        except ValueError, e:
            # XXX Also getting this error occassionaly (as reported on
            # Komodo-beta). Should handle that.
            #    LookupError: unknown encoding
            if encoding:
                log.error('Unsupported encoding for locale %s.%s'%\
                         (encoding[0],encoding[1]))
            else:
                log.error('Unable to set encoding for locale %s'%\
                         os.getenv('LANG'))
        except LookupError, e:
            # windows sets codepages into the locale without
            # the leading 'cp' that python wants.  If the encoding
            # we received is a number, try cp# and see if it works.
            # eg. 1252 should be turned into cp1252
            try:
                if sys.platform.startswith("win") and int(encoding[1]):
                    encoding[1] = 'cp'+encoding[1]
                    return self._setencoding(encoding)
            except ValueError,e:
                # not an int
                #XXX Change inherited (an untested) from bug 24439.
                # check if it has "cp"
                if encoding[1].startswith("cp"):
                    return encoding
            if encoding[0]:
                alias = locale.locale_alias.get(encoding[0].lower())
                if alias:
                    try:
                        return self._setencoding(locale._parse_localename(alias))
                    except ValueError, e:
                        pass
            log.debug('Unsupported encoding for locale %s.%s'%\
                     (encoding[0],encoding[1]))
        except TypeError, e:
            if not sys.platform.startswith("win") and os.getenv("LANG") == "C":
                return ("en_US","iso8859-1")
            else:
                log.debug('Unable to set encoding for locale %s'%\
                            os.getenv('LANG'))
        except Exception, e:
            log.debug('Unable to determine system locale settings')
        return None
    
    def _setlocale(self):
        log.debug('in _setlocale')
        try:
            locale.setlocale(locale.LC_ALL,'')
        except Exception, e:
            log.exception(e)
            log.warn('Unable to setlocale for %s'%os.getenv('LANG'))
            return None
        try:
            return self._setencoding()
        except Exception, e:
            log.exception(e)
            log.warn('Unable to set encoding for locale %s'%os.getenv('LANG'))
        return None

    def _removeEuroLocale(self):
        envvars = ['LC_ALL','LC_CTYPE','LANG','LANGUAGE']
        for var in envvars:
            orig_lang = os.getenv(var)
            if orig_lang and orig_lang.lower().endswith('@euro'):
                lang = orig_lang[:orig_lang.find('@euro')]
                os.environ[var] = lang
        
    def setEncoding(self):
        log.debug("in setEncoding")
        self._startup_locale = self._setlocale()
        if sys.platform.startswith("win"):
            # XXX - this is evil and should be dropped ASAP.
            # Changing the default encoding could impact other code.
            # Python 2.2 will have this support for all file system functions,
            # so as soon as that version is in Komodo, this MUST DIE.

            # On Windows, default python <=2.1 chokes on Unicode file
            # names.  If we change the encoding to "Latin-1", we can
            # at least support European chars transparently.
            # (and if we use "mbcs" we should be able to use
            # _any_ language supported by Windows, latin or otherwise.)
            self._safelyReloadSys()
            sys.setdefaultencoding("mbcs")
            del sys.setdefaultencoding
            log.debug("encoding set to '%s'" % sys.getdefaultencoding())
            if not self._startup_locale:
                log.warn("Unable to determine the current locale "+\
                            "settings, defaulting to en_US.cp1252")
                # set the locale to something that we can
                # least let komodo startup and run with
                self._startup_locale = ['en_US','cp1252']
        elif sys.platform.startswith('darwin'):
            # http://developer.apple.com/documentation/MacOSX/Conceptual/BPInternational/Articles/FileEncodings.html
            # on darwin, and possibly other BSD systems, filesystem is UTF8
            self._safelyReloadSys()
            sys.setdefaultencoding("utf-8")
            del sys.setdefaultencoding
            log.debug("encoding set to '%s'" % sys.getdefaultencoding())
            if not self._startup_locale:
                log.warn("Unable to determine the current locale "+\
                            "settings, defaulting to mac-roman")
                # set the locale to something that we can
                # least let komodo startup and run with
                self._startup_locale = ['','mac-roman']
        else: # Platforms other than Windows
            # Set the default encoding to that appropriate for the
            # current locale, except with UTF-8 support
            if not self._startup_locale:
                log.debug("we do not have _starup_locale")
                # XXX In python 2.2, setlocale fails if
                # the LANG envt variable has @euro at the end.
                # It's a bug in Python 2.2
                self._removeEuroLocale()
                self._startup_locale = self._setlocale()
            if not self._startup_locale:
                log.warn("Unable to determine the current locale "+\
                            "settings, please set LANG environment "+\
                            "variable. Defaulting to en_US.iso8859-1")
                # set the locale to something that we can
                # least let komodo startup and run with
                self._startup_locale = ['en_US','iso8859-1']
            elif self._startup_locale[1].lower() == 'utf':
                log.debug("It's a UTF-8 locale")
                # RH 8 likes to use 'utf' rather than UTF-8,
                # but it will accept UTF-8
                # we cannot modify _startup_locale directly, so reset it
                # completely (bug 28824)
                self._startup_locale = [self._startup_locale[0],'UTF-8']
                # we're already in utf mode, so don't bother doing
                # the settings below
                return
            if not self._startup_locale[0]:
                # OSX doesn't return this data.  Set it to C for now
                self._startup_locale = ['', self._startup_locale[1]]
                log.info("Setting LC_CTYPE to 'C'")
                locale.setlocale(locale.LC_CTYPE, "C")
                return
            # We have to set pythons encoding to utf-8 so that
            # we can have some hope of interpreting file paths
            # that are written in different encodings, and to
            # make GTK show UTF8 fonts correctly.  for instance
            # saving a file with a latin-1 filename, but starting
            # komodo with encoding ISO8859-1.  If we do not do
            # this, and a latin-1 filename is in mru, komodo fails
            # to load

            # XXX The above is not entirely correct across platforms,
            # notably breaking down on Solaris.  It would be best to
            # set the default encoding to the system encoding, but
            # that leads to conflicts with how other components (Gtk,
            # Mozilla, Scintilla) are operating.

            # XXX this will break on older unix systems that do not
            # support UTF-8 -- it would be nice to detect this and
            # let the user know.
            
            # XXX we may want to reimplement this with python 2.3, it affects
            # koDocument encoding issues.
            
            #try:
            #    # this bit is for file I/O
            #    self._safelyReloadSys()
            #    log.info("Setting default encoding to utf-8")
            #    sys.setdefaultencoding('utf-8')
            #    del sys.setdefaultencoding
            #except Exception,e:
            #    log.warn('cannot set encoding to utf-8: %s'%e)

            # this bit is the GTK important bit
            # if it's not done, GTK won't display correctly
            try:
                new_locale = self._startup_locale[0]+'.UTF-8'
                log.info("Setting LC_CTYPE to utf-8")
                locale.setlocale(locale.LC_CTYPE,new_locale)
            except Exception,e:
                log.warn("cannot reset LOCALE set to %s : %s" % (new_locale,e))

            if sys.platform.startswith("sunos"):
                # UTF-8 support on Solaris is not working correctly with
                # GTK.  If a user wishes to use non-latin-1 files (either
                # in file name or data) on Solaris, they will need to
                # ensure they have the correct language packs and fonts on
                # their machines, then export LANG=en_US.UTF-8 (or similar
                # utf-based encoding).
                # We add this LC_CTYPE call here to prevent Gdk fontset
                # warnings, improper titlebar behavior and related unicode
                # issues on Solaris. (Bug 28592, 29235)
                log.info("Setting LC_CTYPE to 'C'")
                locale.setlocale(locale.LC_CTYPE, "C")

    def getStartupLanguageCode(self):
        return self._startup_locale[0]
    def getStartupEncoding(self):
        return self._startup_locale[1]

    def initProcessUtils(self):
        import koprocessutils
        koprocessutils.initialize()

    def finishInitialization(self):
        pass

    def _upgradeFiles(self, dstNameFromSrcName, srcDir, dstDir):
        for srcName, dstName in dstNameFromSrcName.items():
            src = os.path.join(srcDir, srcName)
            dst = os.path.join(dstDir, dstName)
            if not os.path.exists(src):
                # It is not an error if some of the files to upgrade
                # don't exist. The user may just not have done much with
                # the previous Komodo version to have them generated.
                log.info("skipping '%s'" % src)
                continue
            try:
                log.info("upgrading '%s' from '%s'" % (dst, src))
                _copy(src, dst)
            except OSError, ex:
                log.error("Could not upgrade '%s' from '%s': %s"\
                         % (dst, src, ex))

    def _upgradeXREFiles(self, filesToUpgrade, prevUserDataDir, currUserDataDir):
        upgraded = False
        for oldFile, upgradeFunction in filesToUpgrade.items():
            src = os.path.join(prevUserDataDir, "XRE", oldFile)
            dst = os.path.join(currUserDataDir, "XRE", oldFile)
            #print "Checking file does not exist: %s" % (dst)
            if os.path.exists(dst):
                # Should not already exist, if it does, don't do anything
                continue
            #print "Checking file does exists: %s" % (src)
            if not os.path.exists(src):
                # It is not an error if some of the files to upgrade
                # don't exist. The user may just not have done much with
                # the previous Komodo version to have them generated.
                log.info("skipping '%s'" % src)
                continue
            # Else, upgrade from previous version
            try:
                #print "Upgrade function: %r" % (upgradeFunction)
                #apply(upgradeFunction, (self, src))
                upgradeFunction(src)
                upgraded = True
                log.info("upgraded '%s' from '%s'" % (dst, src))
            except OSError, ex:
                log.error("Could not upgrade '%s' from '%s': %s"\
                         % (dst, src, ex))
        return upgraded

    def _upgradeUserPrefs(self):
        """Upgrade any specific info in the user's prefs.xml.
        
        This is called after the new user data dir has been created.

        Dev note: This is also called every time Komodo is started.
        """
        prefs = components.classes["@activestate.com/koPrefService;1"]\
                .getService(components.interfaces.koIPrefService).prefs

        # Komodo 4.0 change: 'fileAssociations' was replaced with the
        # factoryFileAssociations/fileAssociationDiffs combo. This upgrade
        # ensures the user ends up with the appropriate 'fileAssociationDiffs'
        # and that 'fileAssociations' is removed (if any).
        if prefs.hasPrefHere("fileAssociations"):
            # Collect the old associations mapping.
            oldAssociations = {}
            fileAssociationsPref = prefs.getPref("fileAssociations")
            for i in range(fileAssociationsPref.length):
                p = fileAssociationsPref.getPref(i)
                oldAssociations[p.getStringPref(0)] = p.getStringPref(1)

            # The "appropriate" set of factory associations to which to compare
            # is the default "fileAssociations" value for Komodo 3.5.
            factoryAssociations = {
                '*.ada': 'Ada', '*.ant': 'Bullant', '*.asm': 'Assembler',
                '*.aux': 'LaTeX', '*.ave': 'Avenue', '*.bat': 'Batch',
                '*.bbl': 'LaTeX', '*.bc': 'Baan', '*.c': 'C++', '*.c++': 'C++',
                '*.cgi': 'Perl', '*.cix': 'XML', '*.cln': 'Baan',
                '*.cls': 'LaTeX', '*.clw': 'CLW', '*.cmd': 'Batch',
                '*.conf': 'Apache', '*.cpp': 'C++', '*.cron': 'nnCrontab',
                '*.cs': 'C#', '*.css': 'CSS', '*.cxx': 'C++', '*.diff': 'Diff',
                '*.e': 'Eiffel', '*.el': 'Lisp', '*.em': 'EScript',
                '*.erl': 'Erlang', '*.f': 'Fortran 77',
                '*.f90': 'Fortran', '*.f95': 'Fortran', '*.for': 'Fortran 77',
                '*.forth': 'Forth', '*.gc': 'Gui4Cli', '*.h': 'C++',
                '*.h++': 'C++', '*.hpp': 'C++', '*.htm': 'HTML', '*.html':
                'HTML', '*.hxx': 'C++', '*.idl': 'IDL', '*.inc': 'PHP',
                '*.java': 'Java', '*.js': 'JavaScript', '*.kix': 'Kix',
                '*.kpf': 'XML', '*.lis': 'Lisp', '*.lof': 'LaTeX', '*.lot':
                'Lot', '*.lt': 'Lout', '*.ltx': 'LaTeX', '*.lua': 'Lua',
                '*.m': 'Matlab', '*.mac': 'APDL', '*.mak': 'Makefile',
                '*.mixal': 'MMIXAL', '*.mp': 'Metapost', '*.nsi': 'Nsis',
                '*.pas': 'Pascal', '*.patch': 'Diff', '*.pb': 'PowerBasic',
                '*.php': 'PHP', '*.pl': 'Perl', '*.plex': 'Perl',
                '*.plx': 'Perl', '*.pm': 'Perl', '*.pov': 'POVRay',
                '*.ps': 'PostScript', '*.py': 'Python', '*.pyw': 'Python',
                '*.rb': 'Ruby', '*.sh': 'Bash', '*.sol': 'Scriptol',
                '*.spf': 'nnCrontab', '*.sql': 'SQL', '*.sty': 'LaTeX',
                '*.t': 'Perl', '*.tab': 'nnCrontab', '*.tcl': 'Tcl',
                '*.tex': 'LaTeX', '*.toc': 'LaTeX', '*.txt': 'Text',
                '*.v': 'Verilog', '*.vb': 'VisualBasic', '*.vbs': 'VisualBasic',
                '*.vh': 'Verilog', '*.xml': 'XML', '*.xs': 'C++',
                '*.xsl': 'XSLT', '*.xslt': 'XSLT', '*.xul': 'XML',
                '*.yaml': 'YAML', 'Conscript': 'Perl', 'Construct': 'Perl',
                'Makefile': 'Makefile', 'Makefile.*': 'Makefile',
                'makefile': 'Makefile', 'makefile.*': 'Makefile',
            }

            diff = _diffFileAssociations(factoryAssociations, oldAssociations)

            # The new UDL-based RHTML lexer is better than anything there was
            # before: override any previous setting.
            diff = [d for d in diff if d[:2] != ('+', '*.rhtml')]

            prefs.setStringPref("fileAssociationDiffs", repr(diff))
            prefs.deletePref("fileAssociations")

        if prefs.hasPrefHere("mappedPaths"):
            upgradeutils.upgrade_mapped_uris_for_prefset(prefs)

    def _upgradeUserDataDirFiles(self):
        """Upgrade files under the USERDATADIR if necessary.

        Note: For Komodo 4.0.2 the APPDATADIR changed to include the product
        type (IDE or Edit). Before:
            windows: C:\Documents and Settings\USER\Application Data\ActiveState\Komodo\X.Y
            macosx:  ~/Library/Application Support/Komodo/X.Y
            linux:   ~/.komodo/X.Y
        After:
            windows: C:\Documents and Settings\USER\Application Data\ActiveState\Komodo[IDE|Edit]\X.Y
            macosx:  ~/Library/Application Support/Komodo[IDE|Edit]/X.Y
            linux:   ~/.komodo[ide|edit]/X.Y

        If the upgrade is necessary, this method will upgrade from:
        - a previous version of Komodo (IDE, Edit, Personal, Pro); or
        - a Komodo of the same version but different flavour. E.g., if this
          is Komodo IDE 4.0 and the user has run Komodo Edit 4.0, this will
          upgrade from the user's Komodo Edit 4.0 settings.
        """
        from os.path import dirname, basename, join, exists

        koDirSvc = components.classes["@activestate.com/koDirs;1"].getService()
        currUserDataDir = koDirSvc.userDataDir
        currHostUserDataDir = koDirSvc.hostUserDataDir
        
        # These are the files/dirs that we upgrade.
        filesToUpgrade = {
            "komodo-user-prefs.xml": "prefs.xml",
            "prefs.xml": "prefs.xml",
            "templates": "templates",
            "project-templates": "project-templates",
            "schemes": "schemes",
            "toolbox.kpf": "toolbox.kpf",
            "doc-state.xmlc": "doc-state.xmlc", 
            "view-state.xmlc": "view-state.xmlc", 
            "apicatalogs": "apicatalogs",
            "dictionaries": "dictionaries",
        }
        hostFilesToUpgrade = {  # files under "host-$HOST" dir to upgrade
            "breakpoints.pickle": "breakpoints.pickle",
        }

        # First determine if we need to upgrade at all.
        # If any of the above exist in the current version's user data
        # dir then do NOT upgrade.
        for base in filesToUpgrade.keys():
            path = join(currUserDataDir, base)
            if exists(path):
                log.debug("not upgrading userdatadir files: '%s' exists", path)
                return
        for base in hostFilesToUpgrade.keys():
            path = join(currHostUserDataDir, base)
            if exists(path):
                log.debug("not upgrading userdatadir files: '%s' exists", path)
                return

        # Get the current version.
        infoSvc = components.classes["@activestate.com/koInfoService;1"].getService()
        currVer = infoSvc.version.split(".", 2)[:2]
        for i in range(len(currVer)):
            try:
                currVer[i] = int(currVer[i])
            except ValueError:
                pass
        currVer = tuple(currVer) # e.g. (2,3)

        # Determine from which Komodo userdatadir we should upgrade.
        base = dirname(dirname(currUserDataDir))
        if sys.platform in ("win32", "darwin"):
            datadirs = [join(base, d) for d in
                        ("Komodo", "KomodoIDE", "KomodoEdit")]
        else:
            datadirs = [join(base, d) for d in
                        (".komodo", ".komodoide", ".komodoedit")]
        ver_pat = re.compile(r"^\d+\.\d+$")
        vers_and_userdatadirs = []
        for datadir in datadirs:
            try:
                ver_strs = os.listdir(datadir)  # e.g. ["3.5", "4.0", "bogus"]
            except EnvironmentError, ex:
                continue
            for ver_str in ver_strs:
                if not ver_pat.match(ver_str):  # e.g. "bogus" doesn't match
                    continue
                ver = tuple(map(int, ver_str.split('.')))
                if ver > currVer:
                    continue # Skip future versions, we don't downgrade.
                userdatadir = join(datadir, ver_str)
                if userdatadir == currUserDataDir:
                    continue # Skip: can't upgrade from self.
                vers_and_userdatadirs.append(
                    (ver, _splitall(userdatadir), userdatadir))
        vers_and_userdatadirs.sort()
        # This now looks like, e.g.:
        #   [((3, 5), ['C:\\', ..., 'Komodo', '3.5'],     'C:\\...\\Komodo\\3.5'),
        #    ((4, 0), ['C:\\', ..., 'Komodo', '4.0'],     'C:\\...\\Komodo\\4.0'),
        #    ((4, 0), ['C:\\', ..., 'KomodoEdit', '4.0'], 'C:\\...\\KomodoEdit\\4.0')]
        # I.e., the last one in the list, if any, is the dir from which to
        # upgrade.
        if not vers_and_userdatadirs:
            log.debug("not upgrading userdatadir files: no userdatadirs "
                      "from which to upgrade")
            return
        prevVer, _, prevUserDataDir = vers_and_userdatadirs[-1]

        # Upgrade.
        log.info("upgrading user settings from '%s'" % prevUserDataDir)
        self._upgradeFiles(filesToUpgrade, prevUserDataDir, currUserDataDir)
        hostBaseName = basename(currHostUserDataDir)
        prevHostUserDataDir = join(prevUserDataDir, hostBaseName)
        if prevVer >= (4,0):
            # Upgrade from 4.0 or newer, this keeps the remote files server
            # preferences intact.
            hostFilesToUpgrade.update({
                join("XRE", "key3.db"): join("XRE", "key3.db"),
                join("XRE", "cert8.db"): join("XRE", "cert8.db"),
                join("XRE", "secmod.db"): join("XRE", "secmod.db"),
                join("XRE", "extensions"): join("XRE", "extensions"),
            })
            if prevVer >= (4,1):
                # In Komodo 4.1, the Mozilla nsIPasswordManager changed the
                # filename and format of the signons.txt, now calling it
                # "signons2.txt".
                hostFilesToUpgrade.update({
                    join("XRE", "signons2.txt"): join("XRE", "signons2.txt"),
                })
            else:
                hostFilesToUpgrade.update({
                    join("XRE", "signons.txt"): join("XRE", "signons.txt"),
                })
        self._upgradeFiles(hostFilesToUpgrade, prevHostUserDataDir,
                           currHostUserDataDir)

    def upgradeUserSettings(self):
        """Called every time Komodo starts up to initialize the user profile."""
        self._upgradeUserDataDirFiles()
        self._upgradeUserPrefs()

    def _isMozDictionaryDir(self, dictionaryDir):
        # Return true if dictionaryDir contains at least one pair of files
        # foo.aff and foo.dic
        
        if not os.path.isdir(dictionaryDir):
            return False
        from os.path import basename, join, splitext
        import glob
        aff_bases = set(splitext(basename(p))[0]
                        for p in glob.glob(join(dictionaryDir, "*.aff")))
        dic_bases = set(splitext(basename(p))[0]
                        for p in glob.glob(join(dictionaryDir, "*.dic")))
        return len(aff_bases.intersection(dic_bases)) > 0

    def initExtensions(self):
        """'pylib' subdirectories of installed extensions are appended
        to Komodo's runtime sys.path.
        """
        # Add the DictD property so the spellchecker can find
        # the user's own dictionaries.  Consider only directories
        # that contain the English dictionary, or the Komodo extension
        # will fail to startup.  (http://bugs.activestate.com/show_bug.cgi?id=74839)

        try:
            koDirSvc = components.classes["@activestate.com/koDirs;1"].getService()
            dictionaryDir = os.path.join(koDirSvc.userDataDir, "dictionaries")
            if self._isMozDictionaryDir(dictionaryDir):
                profDir_nsFile = components.classes["@mozilla.org/file/local;1"] \
                        .createInstance(components.interfaces.nsILocalFile)
                profDir_nsFile.initWithPath(dictionaryDir)
                directoryService = components.classes["@mozilla.org/file/directory_service;1"]\
                         .getService(components.interfaces.nsIProperties)
                directoryService.set("DictD", profDir_nsFile)
        except:
            log.exception("Failed to set the dictionary property")
            
        import directoryServiceUtils
        from os.path import join, exists
        for extDir in directoryServiceUtils.getExtensionDirectories():
            pylibDir = join(extDir, "pylib")
            if exists(pylibDir):
                sys.path.append(pylibDir)

    def installSamples(self, force):
        infoSvc = components.classes["@activestate.com/koInfoService;1"].getService()
        koDirSvc = components.classes["@activestate.com/koDirs;1"].getService()
        #XXX The best target directory might vary for other OSes.
        dstDir = os.path.join(koDirSvc.userDataDir, "samples")
        if os.path.exists(dstDir):
            if force:
                log.info("removing old samples directory: '%s'" % dstDir)
                _rmtree(dstDir) #XXX should handle error here
            else:
                log.info("samples already present at '%s'" % dstDir)
                return
        srcDir = os.path.join(koDirSvc.supportDir, "samples")
        log.info("installing Komodo samples to '%s'" % dstDir)
        _copy(srcDir, dstDir)
