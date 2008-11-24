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

# Launch a URL in the user's "default" browser.
#   We used to use "webbrowser.py" here but it does netscape magic and
#   allows for command line browsers, both of which can cause Komodo to hang.

from xpcom import components
from xpcom import components, nsError, ServerException
import process, koprocessutils
import sys, os
import re
import logging
import which

log = logging.getLogger('koWebbrowser')

class KoWebbrowser:
    _com_interfaces_ = [components.interfaces.koIWebbrowser]
    _reg_clsid_ = "{7B361CD6-4426-4d23-86D6-B6F8E0FCDA20}"
    _reg_contractid_ = "@activestate.com/koWebbrowser;1"
    _reg_desc_ = "Komodo Default Webbrowser Service"

    def _spawn(self, command):
        """Spawn the given command (or argv) and return true iff successful"""
        try:
            env = koprocessutils.getUserEnv()
        except ServerException, ex:
            log.error(str(ex))
            return 1
        try:
            process.ProcessOpen(command, env=env, stdin=None, stdout=None,
                                stderr=None)
            return 1
        except process.ProcessError, ex:
            log.error(str(ex))
            return 0

    def _cmdInterpolate(self, command, filename, *args):
        """Interpolate the given command and args.
        
        "help ftype" says:
            Within an open command string %0 or %1 are substituted with the
            file name being launched through the assocation. %* gets all the
            parameters and %2 gets the 1st parameter, %3 the second, etc. %~n
            gets all the remaining parameters starting with the nth
            parameter, where n may be between 2 and 9, inclusive.
        """
        pattern = re.compile(r"(%\d|%\*|%~[2-9])")
        if pattern.search(command):
            parts = pattern.split(command)
            LITERAL, CODE = range(2)
            state = LITERAL
            interpolated = ""
            for part in parts:
                if state == LITERAL:
                    interpolated += part
                    state = CODE
                elif state == CODE:
                    if part == "%0" or part == "%1":
                        interpolated += filename
                    elif part == "%*":
                        interpolated += ' '.join(args)
                    elif part.startswith("%~"):
                        num = int(part[2:])-2
                        interpolated += ' '.join(args[num:])
                    if re.match("%([2-9])", part):
                        num = int(part[1:])-2
                        try:
                            interpolated += args[num]
                        except IndexError,ex:
                            pass
                    state = LITERAL
        else:
            argv = [command, filename] + list(args)
            interpolated = ' '.join(argv)  #XXX is this desired?
        return interpolated

    def _winStartURL(self, url):
        """'start' the given URL.
        
        Typically this just means running os.startfile(). However that
        drops HTML anchors (i.e. foo.html#anchor -> foo.html), so if it
        looks like the URL has an anchor we try to do better.
        """
        import wininteg
        if url.find("#") != -1:
            # Attempt to find the associated default action for this file
            # and run that. If cannot, then fallback to just running
            # os.startfile().
            #
            #XXX Note that we are not doing this perfectly. There are some
            #    some registered action mechanisms that we are not handling.
            #    As well we don't handle any of the ddeexec keys in the
            #    registry.
            page, anchor = url.split("#", 1)
            ext = os.path.splitext(page)[1]
            try:
                type, name, actions = wininteg.getFileAssociation(ext)
            except wininteg.WinIntegError:
                pass
            else:
                if actions:
                    command = actions[0][2]
                    # See "help ftype" in cmd.exe for description of %-codes.
                    command = self._cmdInterpolate(command, url)
                    return self._spawn(command)

        try:
            os.startfile(url)
            return 1
        except WindowsError, e:
            # I don't know who is at fault here but if Netscape 6 (and
            # presumable, therefore, some versions of Mozilla) is set as
            # the default then (1) the browser successfully loads the
            # file *and* (2) this is raised:
            #    Traceback (most recent call last):
            #      File "C:\mozilla_source\moz.09apr.trentm.winnt.release.komodo5\mozilla\dist\WIN32_O.OBJ\bin\components\koWebbrowser.py", line 27, in open_new
            #        os.startfile(url)
            #    WindowsError: [Errno 2] The system cannot find the file specified: 'http://www.ActiveState.com/ASPN/Downloads/Komodo/NeedLicense?os=Windows2000v.5.0.2195&build=19520&version=1.1.0-devel'
            #
            if e.errno == 2:
                return 1
            else:
                return 0
        except:
            return 0

    def _escapeUrl(self, url):
        """Escape this URL so Mac OS X's 'open' command can deal with it.

        Mainly this is to escape spaces.
        """
        import urllib
        return urllib.quote(url, safe="/:\\#?&= ")
        
    def open_new(self, url):
        """Open the given URL in the user's default browser.
        Return true iff successful.
        """
        prefs = components.classes["@activestate.com/koPrefService;1"].\
                getService(components.interfaces.koIPrefService).prefs
        browser = prefs.getStringPref("browser")
        if not browser:
            if sys.platform.startswith("win"):
                return self._winStartURL(url)
            elif sys.platform == "darwin":
                return self._spawn(["open", self._escapeUrl(url)])
            else:
                # On Linux/Solaris we expect the browser preference to
                # have been set before calling into koWebbrowser.
                # Typically this is done by
                # browse.js::browse_OpenUrlInDefaultBrowser()
                msg = "cannot open URL '%s' because 'browser' preference is not set" % url
                log.error(msg)
                raise ServerException(nsError.NS_ERROR_FAILURE, msg)
        else:
            return self.open_new_browser(url, browser)

    def open_new_browser(self, url, browser):
        # process will quote args with spaces, make sure it's
        # not already quoted
        if browser[0] == '"':
            browser = browser[1:-1]
        if sys.platform == 'darwin':
            return self._spawn(["open", "-a", browser, self._escapeUrl(url)])
        else:
            return self._spawn([browser, url])

    def _SameFile(self, fname1, fname2):
        return ( os.path.normpath(os.path.normcase(fname1)) ==\
            os.path.normpath(os.path.normcase(fname2)) )

    def _parseAssociationAction(self, command):
        """Parse a Windows file association action command into an argv."""
        # Examples:
        #   'C:\\PROGRA~1\\MOZILL~1\\FIREFOX.EXE -url "%1"'
        #   '"C:\\Program Files\\Microsoft Office\\Office\\msohtmed.exe" %1'
        #   '"C:\\Program Files\\ActiveState Komodo 3.0\\komodow.exe" "%1" %*'
        #   '"C:\\Program Files\\Microsoft Office\\Office\\msohtmed.exe" /p %1'
        #   '"C:\\Program Files\\Internet Explorer\\iexplore.exe" -nohome'
        WHITESPACE = " \t\r\n"
        argv = []
        i = 0
        while 1:
            # Eat whitespace to the start of the next argument.
            while i < len(command) and command[i] in WHITESPACE:
                i += 1
            if i >= len(command):
                break
            # Parse one argument
            arg = ""
            if command[i] == '"':
                i += 1 # skip leading '"'
                while i < len(command) and command[i] != '"':
                    arg += command[i]
                    i += 1
                i += 1 # skip closing '"'
            else:
                while i < len(command) and command[i] not in WHITESPACE:
                    arg += command[i]
                    i += 1
            if not arg:
                raise ValueError("Windows assoc action parsing error: "
                                 "arg=%r, i=%r, command=%r"
                                 % (arg, i, command))
            argv.append(arg)
        #print "PARSE: %r -> %r" % (command, argv)
        return argv

    def get_possible_browsers(self):
        matches = []
        # If on Windows, add the browser(s) assigned as the default handlers
        # for .html, .htm, etc. (i.e. for common browser-y filetypes).
        if sys.platform.startswith("win"):
            import wininteg
            for ext in (".html", ".htm"):
                try:
                    type, name, actions = wininteg.getFileAssociation(ext)
                except wininteg.WinIntegError:
                    pass
                else:
                    if actions:
                        command = actions[0][2]
                        argv = self._parseAssociationAction(command)
                        if argv:
                            matches.append(argv[0])

        # Search the PATH as it was when Komodo started, otherwise Komodo's
        # internal mozilla.exe might be listed as a possible browser.
        #   http://bugs.activestate.com/show_bug.cgi?id=26373
        path = koprocessutils.getUserEnv()["PATH"]
        path = path.split(os.pathsep)
        if sys.platform.startswith('win'):
            matches += (
                which.whichall("iexplore", exts=['.exe'], path=path) +
                which.whichall("firefox", exts=['.exe'], path=path) +
                which.whichall("mozilla", exts=['.exe'], path=path) +
                which.whichall("MozillaFirebird", exts=['.exe'], path=path) +
                which.whichall("opera", exts=['.exe'], path=path) +
                which.whichall("flock", exts=['.exe'], path=path) +
                which.whichall("netscape", exts=['.exe'], path=path)
            )
        elif sys.platform == 'darwin':
            path = ['/Applications','/Network/Applications']+path
            matches += (
                which.whichall("Firefox.app", path=path) +
                which.whichall("Mozilla.app", path=path) +
                which.whichall("Opera.app", path=path) +
                which.whichall("Netscape.app", path=path) +
                which.whichall("Camino.app", path=path) +
                which.whichall("Flock.app", path=path) +
                which.whichall("Safari.app", path=path)
            )            
        else:
            matches += (
                which.whichall("firefox", path=path) +
                which.whichall("mozilla", path=path) +
                which.whichall("MozillaFirebird", path=path) +
                which.whichall("konqueror", path=path) +
                which.whichall("opera", path=path) +
                which.whichall("netscape", path=path) +
                which.whichall("netscape-communicator", path=path) +
                which.whichall("kfm", path=path)
            )

        # check for duplicates
        matchesWithoutDups = []
        for i in range(len(matches)):
            for j in range(i+1, len(matches)):
                if self._SameFile(matches[i], matches[j]):
                    break
            else:
                matchesWithoutDups.append(matches[i])
        return matchesWithoutDups

    def get_firefox_paths(self):
        firefoxes = []
        # If on Windows, add the browser(s) assigned as the default handlers
        # for .html, .htm, etc. (i.e. for common browser-y filetypes).
        if sys.platform.startswith("win"):
            import wininteg
            for ext in (".html", ".htm"):
                try:
                    type, name, actions = wininteg.getFileAssociation(ext)
                except wininteg.WinIntegError:
                    pass
                else:
                    if actions:
                        command = actions[0][2]
                        argv = self._parseAssociationAction(command)
                        if argv and "firefox" in argv[0].lower():
                            firefoxes.append(argv[0])

        # Search the PATH as it was when Komodo started, otherwise Komodo's
        # internal mozilla.exe might be listed as a possible browser.
        #   http://bugs.activestate.com/show_bug.cgi?id=26373
        path = koprocessutils.getUserEnv()["PATH"]
        path = path.split(os.pathsep)
        if sys.platform.startswith('win'):
            firefoxes += which.whichall("firefox", exts=['.exe'], path=path)
        elif sys.platform == 'darwin':
            path = ['/Applications', '/Network/Applications'] + path
            firefoxes += which.whichall("Firefox.app", path=path)
        else:
            firefoxes += which.whichall("firefox", path=path)

        # check for duplicates
        firefoxesWithoutDups = []
        for i in range(len(firefoxes)):
            for j in range(i+1, len(firefoxes)):
                if self._SameFile(firefoxes[i], firefoxes[j]):
                    break
            else:
                firefoxesWithoutDups.append(firefoxes[i])
        return firefoxesWithoutDups

    def install_firefox_xpis(self, firefox_path, xpi_paths):
        #print "install the following xpis to '%s':\n\t%s"\
        #      % (firefox_path, "\n\t".join(xpi_paths))
        if sys.platform == "darwin":
            argv = ["open", "-a", "Firefox"] + xpi_paths
        else:
            argv = [firefox_path] + xpi_paths
        retval = self._spawn(argv)


