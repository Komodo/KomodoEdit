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

# some useful system utilities

import sys, os, operator
from xpcom import components, nsError, ServerException, COMException
import which
import logging
import shutil

log = logging.getLogger("koSysUtils")
#log.setLevel(logging.DEBUG)

if sys.platform.startswith('win'):
    colorDialog = None
    customColors = [0] * 16
    def _adjustWindow(hwnd, msg, wp, lp):
        global colorDialog
        pos = colorDialog.GetCursorPos()
        #log.debug("pos = (%d, %d)", pos[0], pos[1])
        colorDialog.SetWindowPos(pos[0], pos[1])
            
class koSysUtils:
    _com_interfaces_ = [components.interfaces.koISysUtils,
                        components.interfaces.koIColorPickerAsync]
    _reg_clsid_ = "{56F686E0-A989-4714-A5D6-D77BC850C5C0}"
    _reg_contractid_ = "@activestate.com/koSysUtils;1"
    _reg_desc_ = "System Utilities Service"

    def __init__(self):
        self.F_OK = os.F_OK
        self.R_OK = os.R_OK
        self.W_OK = os.W_OK
        self.X_OK = os.X_OK
        # XXX Should just cache the user env locally. It ain't changin'.
        self._userEnvSvc = components.classes["@activestate.com/koUserEnviron;1"].\
            getService(components.interfaces.koIUserEnviron)
        self._manager = None

    def _SameFile(self, fname1, fname2):
        return ( os.path.normpath(os.path.normcase(fname1)) ==\
            os.path.normpath(os.path.normcase(fname2)) )

    def _GetRegisteredExecutable(self, exe):
        if sys.platform.startswith('win'):
            # If on Windows, look up the Path in the "App Paths" registry
            import _winreg
            try:
                #XXX might have to be smart enough to handle HKCU too
                return _winreg.QueryValue(_winreg.HKEY_LOCAL_MACHINE,
                    "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths"\
                    "\\" + exe + ".exe")
            except _winreg.error:
                pass
        return None

    def FastCheckIfHaveExecutable(self, exe):
        if sys.platform.startswith("win"):
            path = self._userEnvSvc.get("PATH")
            from ctypes import windll, create_unicode_buffer, c_wchar_p, pointer
            kernel32 = windll.kernel32
            import os
            pathw = unicode(os.environ["PATH"])
            appw = unicode(exe)
            exew = unicode(".exe")
            buf_size = 1024
            p = create_unicode_buffer(buf_size)
            res_ptr = c_wchar_p()
            try:
                res = kernel32.SearchPathW(pathw, appw, exew, buf_size, p, pointer(res_ptr))
                if res:
                    return 1
            except WindowsError:
                pass
            return self._GetRegisteredExecutable(exe) is not None
        # Fast check - dont go a searching down PATHEXT etc on Windows.
        return operator.truth(self.Which(exe))

    def Which(self, exeName):
        """Return the full path to the given executable using the user's PATH.
        Return the empty string if the executable could not be found.
        ** NOTE: The *user's* environment is reproduced by checking
                 <user-data-dir>/startup-env.tmp for any changes to the PATH
                 that komodo.exe might have made.
        """
        path = self._userEnvSvc.get("PATH", "").split(os.pathsep)
        try:
            return which.which(exeName, path=path)
        except which.WhichError, ex:
            return ""

    def WhichAll(self, exeName):
        path = self._userEnvSvc.get("PATH", "").split(os.pathsep)
        return which.whichall(exeName, path=path)

    def IsFile(self, filename):
        try:
            return os.path.isfile(filename)
        except OSError, e:
            raise ServerException, (nsError.NS_ERROR_FILE_NOT_FOUND, str(e))

    def IsDir(self, dirname):
        try:
            return os.path.isdir(dirname)
        except OSError, e:
            raise ServerException, (nsError.NS_ERROR_FILE_NOT_FOUND, str(e))

    def Stat(self, filename):
        try:
            return os.stat(filename)[:10]
        except OSError, e:
            raise ServerException, (nsError.NS_ERROR_FILE_NOT_FOUND, str(e))

    def Access(self, filename, mode):
        return os.access(filename, mode)

    def Touch(self, filename):
        if os.path.exists(filename):
            os.utime(filename, None)
        else:
            f = open(filename, 'w')
            f.close()

    def FlushStdout(self):
        if sys.stdout:
            sys.stdout.flush()

    def FlushStderr(self):
        if sys.stderr:
            sys.stderr.flush()

    def _getManager(self):
        if self._manager:
            return self._manager
        manager = self._userEnvSvc.get("DESKTOP_SESSION")
        if manager in ["gnome", "kde"]:
            self._manager = manager
            return manager
        manager = self._userEnvSvc.get("WINDOWMANAGER")
        if manager:
            self._manager = os.path.basename(manager)
            return self._manager
        return "unknown"
        
    def MoveToTrash(self, filename):
        if sys.platform.startswith("win"):
            import ctypesutils
            ctypesutils.move_to_trash(filename)
            return
        if sys.platform.startswith("darwin"):
            import Carbon.Folder
            kUserDomain = 0
            trashfolder = Carbon.Folder.FSFindFolder(kUserDomain, 'trsh', 0)
            trash = trashfolder.as_pathname()
            toTrash = os.path.join(trash, os.path.basename(filename))
        else:
            # Gnome:
            #   Newer Ubuntu and gnome systems use the "gvfs-trash", storing
            #   under the "~/.local/share/Trash" directory in a way that can
            #   be reversed (restore from trash).
            #   For older Gnome platforms, just use "~/.Trash".
            # KDE:
            #   it might be better to use kfmclient.
            manager = self._getManager()
            if manager != "kde" and os.path.exists("/usr/bin/gvfs-trash"):
                os.system('/usr/bin/gvfs-trash "%s"' % (filename, ))
                if not os.path.exists(filename):
                    return
            trash = os.path.expanduser("~/.Trash")
            if not os.path.exists(trash):
                trash = os.path.expanduser("~/.local/share/Trash")
                if not os.path.exists(trash):
                    trash = os.path.expanduser("~/.Trash")
                    os.mkdir(trash)
            toTrash = os.path.join(trash, os.path.basename(filename))
            if manager == "kde":
                os.system('kfmclient move "%s" "%s"' % (filename, toTrash))

        if os.path.exists(filename):
            # Platform-specific ways of moving the item to the trash either
            # weren't applicable, or failed, so use a generic method.
            if not os.path.exists(trash):
                try:
                    os.mkdir(trash)
                except:
                    log.exception("Can't create directory %s", trash)
                    return
            elif os.path.exists(toTrash):
                try:
                    # shutil.move doesn't overwrite existing items
                    if os.path.isdir(toTrash):
                        shutil.rmtree(toTrash, ignore_errors=False)
                    else:
                        os.unlink(toTrash)
                except:
                    log.exception("Can't remove existing file/dir %s", toTrash)
                    return
            # Finally, try either moving the source to the trash, or
            # do a copy & rename
            try:
                shutil.move(filename, toTrash)
            except OSError, ex:
                if ex.errno == 18:
                    # OSError: [Errno 18] Invalid cross-device link
                    # Try to copy the file and then remove the original,
                    # see bug 81138.
                    shutil.copy(filename, toTrash)
                    os.remove(filename)
                else:
                    raise

    def ShowFileInFileManager(self, filename):
        # nsILocalFile handles some of this
        localFile = components.classes["@mozilla.org/file/local;1"].createInstance(components.interfaces.nsILocalFile)
        localFile.initWithPath(filename)
        try:
            localFile.reveal()
            return
        except COMException, e:
            # reveal is not implemented, try the old stuff
            pass
        if sys.platform not in ['win32','darwin']:
            manager = self._getManager()
            if os.path.isfile(filename):
                filename = os.path.dirname(filename)
            if manager == "gnome":
                os.system('nautilus "%s" &' % filename)
            elif manager == "kde":
                os.system('konqueror --profile filemanagement "%s" &' % filename)
            else:
                # see if nautilus or konqueror exists, and use them
                nautilus = self.Which("nautilus")
                if nautilus:
                    os.system('nautilus "%s" &' % filename)
                    return
                konqueror = self.Which("konqueror")
                if konqueror:
                    os.system('konqueror --profile filemanagement "%s" &' % filename)
                    return
                raise "NOT IMPLEMENTED"

    def OpenFile(self, filename):
        """OpenFile
           given a filename, launch the file as if you had double clicked on it
           in the file viewer (eg. Explorer, Finder, etc)
        """
        # nsILocalFile handles some of this
        localFile = components.classes["@mozilla.org/file/local;1"].createInstance(components.interfaces.nsILocalFile)
        localFile.initWithPath(filename)
        try:
            localFile.launch()
            return
        except COMException, e:
            # launch is not implemented, try the old stuff
            pass
        if sys.platform not in ['win32','darwin']:
            if manager == "gnome":
                os.system('gnome-open "%s" &' % filename)
            elif manager == "kde":
                os.system('kfmclient exec "%s" &' % filename)
            else:
                # see if nautilus or konqueror exists, and use them
                gnome = self.Which("gnome-open")
                if gnome:
                    os.system('gnome-open "%s" &' % filename)
                    return
                kfmclient = self.Which("kfmclient")
                if kfmclient:
                    os.system('kfmclient exec "%s" &' % filename)
                    return
                
                #XXX There has got to be a better way to do this on Linux.
                currDir = os.getcwd()
                os.chdir(filename);
                os.system('xterm &');
                os.chdir(currDir);

    def joinargv(self, argv):
        return _joinArgv(argv)

    def _getAppropriateEOF(self, lines):
        eof = None

        try:
            # Try to infer from first given line.
            line = lines[0]
            if line.endswith("\r\n"):
                eof = "\r\n"
            elif line.endswith("\n"):
                eof = "\n"
            elif line.endswith("\r"):
                eof = "\r"
        except IndexError, ex:
            pass

        if eof is None:
            # Fallback to setting for this platform.
            prefSvc = components.classes["@activestate.com/koPrefService;1"]\
                      .getService(components.interfaces.koIPrefService)
            eofCode = prefSvc.prefs.getStringPref("endOfLine")
            eofCode2eof = {"CRLF": "\r\n", "LF": "\r", "CR": "\n"}
            try:
                eof = eofCode2eof[eofCode]
            except KeyError, ex:
                log.warn("unexpected 'endOfLine' pref value: '%s'", eofCode)
                # Paranoia: Fallback to a reasonable platform default.
                if sys.platform.startswith("win"):
                    eof = "\r\n"
                elif sys.platform.startwith("mac"):
                    eof = "\r"
                else:
                    eof = "\n"

        return eof

    def diff_files(self, fname1, fname2):
        # XXX upgrade to deal with remote files someday?
        import difflib
        try:
            lines1 = open(fname1, 'rb').readlines()
            lines2 = open(fname2, 'rb').readlines()
        except IOError, ex:
            lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"]\
                           .getService(components.interfaces.koILastErrorService)
            lastErrorSvc.setLastError(0, str(ex))
            raise ServerException(nsError.NS_ERROR_UNEXPECTED, str(ex))

        if (lines1 == lines2):
            diff = ""
        else:
            difflines = list(difflib.ndiff(lines1, lines2))

            # ndiff() uses UNIX-style line terminators for its added
            # "?..." lines. Correct those to the line terminator used in
            # the first file.
            eof = self._getAppropriateEOF(lines1)
            if eof != "\n":
                for i in range(len(difflines)):
                    if difflines[i].startswith("? "):
                        difflines[i] = difflines[i][:-1] + eof
            
            diff = "".join(difflines)

        return diff

    def pickColor(self, startingcolor):
        return self.pickColorWithPositioning(startingcolor, -1, -1)

    def pickColorWithPositioning(self, startingcolor, screenX, screenY):
        prefSvc = components.classes["@activestate.com/koPrefService;1"]\
                  .getService(components.interfaces.koIPrefService)
        cid = prefSvc.prefs.getStringPref("colorpicker_cid")
        try:
            cpSvc = components.classes[cid].\
                        getService(components.interfaces.koIColorPicker)
        except COMException, ex:
            # Only log an exception if a cid has been explicitly set.
            if cid:
                log.exception("Unable to load the colorpicker with CID: %r", cid)
            if sys.platform.startswith("win") or sys.platform.startswith("darwin"):
                # Default to the system color picker.
                cid = "@activestate.com/koSystemColorPicker;1"
            else:
                # Default to the Komodo JavaScript color picker.
                cid = "@activestate.com/koColorPicker;1"
            cpSvc = components.classes[cid].\
                        getService(components.interfaces.koIColorPicker)
        return cpSvc.pickColorWithPositioning(startingcolor, screenX, screenY)

    def pickColorAsync(self, callback, color, alpha, screenX=None, screenY=None):
        prefSvc = components.classes["@activestate.com/koPrefService;1"]\
                  .getService(components.interfaces.koIPrefService)
        cid = prefSvc.prefs.getStringPref("colorpicker_cid")
        try:
            cpSvc = components.classes[cid].\
                        getService(components.interfaces.koIColorPickerAsync)
        except COMException, ex:
            # Only log an exception if a cid has been explicitly set.
            if cid:
                log.exception("Unable to load the colorpicker with CID: %r", cid)
            if sys.platform.startswith("win") or sys.platform.startswith("darwin"):
                # Default to the system color picker.
                cid = "@activestate.com/koSystemColorPicker;1"
            else:
                # Default to the Komodo JavaScript color picker.
                cid = "@activestate.com/koColorPicker;1"
            cpSvc = components.classes[cid].\
                        getService(components.interfaces.koIColorPickerAsync)
        return cpSvc.pickColorAsync(callback, color, alpha, screenX, screenY)

    def byteLength(self, unicodestr):
        utf8 = unicodestr.encode('utf-8')
        return len(utf8)

    def charIndexFromPosition(self, unicodestr, pos):
        utf8 = unicodestr.encode('utf-8')
        return len(utf8[:pos].decode('utf-8'))

if sys.platform.startswith("win"):
    _bundle = components.classes["@mozilla.org/intl/stringbundle;1"]\
             .getService(components.interfaces.nsIStringBundleService)\
             .createBundle("chrome://komodo/locale/library.properties")
    class WindowsSystemColorPicker:
        _com_interfaces_ = [components.interfaces.koIColorPicker,
                            components.interfaces.koIColorPickerAsync]
        _reg_clsid_ = "{a482cb10-823b-4142-9f39-65991a94f0fa}"
        _reg_contractid_ = "@activestate.com/koSystemColorPicker;1"
        _reg_desc_ = _bundle.GetStringFromName("windowsColorPicker.desc")
        _reg_categories_ = [
             ("colorpicker", "windows_system_color_picker"),
        ]

        def __init__(self):
            self._sysUtilsSvc = None

        def pickColor(self, startingcolor):
            return self.pickColorWithPositioning(startingcolor, -1, -1)

        def pickColorWithPositioning(self, startingcolor, screenX, screenY):
            from wnd.dlgs.choosecolor import ChooseColor
            global colorDialog
            global customColors
            
            if colorDialog is None:
                colorDialog = ChooseColor()
            r,g,b = startingcolor[1:3], startingcolor[3:5], startingcolor[5:]
            bgr = int(b+g+r, 16)
            #log.debug("bgr in = %x (%r)", bgr, bgr)
            colorDialog.onINIT = _adjustWindow
            res = colorDialog.Run(None, 'fullopen', 'hook',
                                  customcolors=customColors, initcolor=bgr)
            if res is not None:
                bgr = "%06x" % res
                #log.debug("bgr out = %r", bgr)
                b,g,r = bgr[:2], bgr[2:4], bgr[4:]
                for i, x in enumerate(colorDialog._dlgs_colors):
                    customColors[i] = int(x)
                return '#'+r+g+b

        def pickColorAsync(self, callback, startingcolor, startingalpha, screenX=None, screenY=None):
            from wnd.dlgs.choosecolor import ChooseColor
            global colorDialog
            global customColors

            def _adjustWindow(hwnd, msg, wp, lp):
                #log.debug("pos = (%d, %d)", pos[0], pos[1])
                colorDialog.SetWindowPos(screenX, screenY)

            if not callback or not hasattr(callback, "handleResult"):
                raise COMException(nsError.NS_ERROR_INVALID_ARG,
                                   "pickColorAsync got invalid callback %r" % (callback,))

            # parse the starting colors
            try:
                startingcolor = startingcolor.lstrip("#")
                colors = [int(startingcolor[x:x+2], 16) for x in range(0, 6, 2)]
            except Exception:
                raise COMException(nsError.NS_ERROR_INVALID_ARG,
                                   "pickColorAsync: invalid starting color %r" % (startingcolor,))

            if colorDialog is None:
                colorDialog = ChooseColor()
            bgr = colors[2] * 2**16 + colors[1] * 2**8 + colors[0]
            #log.debug("bgr in: %r -> %x (%r)", colors, bgr, bgr)
            if screenX or screenY:
                colorDialog.onINIT = _adjustWindow
            res = colorDialog.Run(None, 'fullopen', 'hook',
                                  customcolors=customColors, initcolor=bgr)
            if res is not None:
                b, g, r = [(res & (2**x-1)) >> (x - 8) for x in range(24, 0, -8)]
                #log.debug("bgr out: %r -> %x (%r)", [r,g,b], res, res)
                for i, x in enumerate(colorDialog._dlgs_colors):
                    customColors[i] = int(x)
                callback.handleResult("#%02x%02x%02x" % (r, g, b), startingalpha)
            else:
                callback.handleResult(None, startingalpha)

elif sys.platform.startswith("darwin"):
    import ctypes
    _bundle = components.classes["@mozilla.org/intl/stringbundle;1"]\
             .getService(components.interfaces.nsIStringBundleService)\
             .createBundle("chrome://komodo/locale/library.properties")
    class MacOSXSystemColorPicker:
        _com_interfaces_ = [components.interfaces.koIColorPicker,
                            components.interfaces.koIColorPickerAsync]
        _reg_clsid_ = "{434c3a68-5485-4b27-a852-e220358333f3}"
        _reg_contractid_ = "@activestate.com/koSystemColorPicker;1"
        _reg_desc_ = _bundle.GetStringFromName("macosxColorPicker.desc")
        _reg_categories_ = [
             ("colorpicker", "macosx_system_color_picker"),
        ]

        def _mac_get_color_from_process(self, startingcolor="", startingalpha="",
                                        callback=None, originalThread=None):
            koDirSvc = components.classes["@activestate.com/koDirs;1"].getService()
            colorpicker_exe = os.path.join(koDirSvc.supportDir, "colorpicker", "osx_colorpicker")
            import process
            cmd = [colorpicker_exe]
            if startingcolor:
                # remove hash
                if startingcolor.startswith("#"):
                    startingcolor = startingcolor[1:]
                cmd += ["-startColor", startingcolor]
            p = process.ProcessOpen(cmd, stdin=None, stdout=process.PIPE, stderr=None)
            stdout, stderr = p.communicate()

            newcolor = stdout.strip()
            if newcolor:
                newcolor = "#" + newcolor

            if callback and originalThread:
                def run_callback():
                    callback.handleResult(newcolor, startingalpha)
                originalThread.dispatch(run_callback,
                                        components.interfaces.nsIThread.DISPATCH_NORMAL)

            return newcolor

        def pickColor(self, startingcolor):
            return self.pickColorWithPositioning(startingcolor, -1, -1)

        def pickColorWithPositioning(self, startingcolor, screenX, screenY):
            self._mac_get_color_from_process()

        def pickColorAsync(self, callback, startingcolor, startingalpha, screenX=0, screenY=0):
            if not callback or not hasattr(callback, "handleResult"):
                raise COMException(nsError.NS_ERROR_INVALID_ARG,
                                   "pickColorAsync got invalid callback %r" % (callback,))

            # remember the calling thread
            tm = components.classes["@mozilla.org/thread-manager;1"]\
                           .getService(components.interfaces.nsIThreadManager)
            originalThread = tm.currentThread

            import threading
            t = threading.Thread(name="color picker processs",
                                 target=self._mac_get_color_from_process,
                                 kwargs={ "startingcolor": startingcolor,
                                          "startingalpha": startingalpha,
                                          "callback": callback,
                                          "originalThread": originalThread })
            t.setDaemon(True)
            t.start()

def _escapeArg(arg):
    """Escape the given command line argument for the shell."""
    #XXX There is a probably more that we should escape here.
    return arg.replace('"', r'\"')


def _joinArgv(argv):
    r"""Join an arglist to a string appropriate for running.

        >>> import os
        >>> _joinArgv(['foo', 'bar "baz'])
        'foo "bar \\"baz"'
    """
    cmdstr = ""
    specialChars = [';', ' ', '=']
    for arg in argv:
        for ch in specialChars:
            if ch in arg:
                cmdstr += '"%s"' % _escapeArg(arg)
                break
        else:
            cmdstr += _escapeArg(arg)
        cmdstr += ' '
    if cmdstr.endswith(' '): cmdstr = cmdstr[:-1]  # strip trailing space
    return cmdstr

