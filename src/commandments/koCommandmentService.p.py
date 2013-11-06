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

"""
Komodo Commandment system service
"""

import os
import logging
import sys
import threading
import re
import getopt
import traceback
if sys.platform.startswith("win"):
    import glob
    import koWndWrapper
else:
    import fcntl

from xpcom import components, COMException


#---- exceptions

class CommandmentError(Exception):
    pass



#---- globals

if sys.platform.startswith("win"):
    # A handle to the Komodo main window for use by some of the commandments.
    _gHWnd = None

log = logging.getLogger('commandments')
#log.setLevel(logging.DEBUG)



#---- support routines

@components.ProxyToMainThreadAsync
def _sendStatusMessage(msg, timeout=3000, highlight=1):
    observerSvc = components.classes["@mozilla.org/observer-service;1"]\
         .getService(components.interfaces.nsIObserverService)
    sm = components.classes["@activestate.com/koStatusMessage;1"]\
         .createInstance(components.interfaces.koIStatusMessage)
    sm.category = "commandment"
    sm.msg = msg
    sm.timeout = timeout     # 0 for no timeout, else a number of milliseconds
    sm.highlight = highlight # boolean, whether or not to highlight
    try:
        observerSvc.notifyObservers(sm, 'status_message', None)
    except COMException, e:
        # do nothing: Notify sometimes raises an exception if (???)
        # receivers are not registered?
        pass

@components.ProxyToMainThreadAsync
def notifyObservers(subject, topic, data):
    observerSvc = components.classes["@mozilla.org/observer-service;1"]\
         .getService(components.interfaces.nsIObserverService)
    observerSvc.notifyObservers(subject, topic, data)

def _handleCommandment(commandment):
    # Parse the commandment string.
    parts = commandment.split('\t')
    name, args = parts[0], parts[1:]
    log.info("call %s(%s)", name, ', '.join(args))

    if name == "open":
        try:
            opts, args = getopt.getopt(args, "s:", ["selection="])
        except getopt.error, ex:
            log.error(str(ex))
            return 1
        selection = None
        for opt, optarg in opts:
            if opt in ("-s", "--selection"):
                # Validate this and put an error in the status bar and
                # carry on if invalid.
                # Good: 1  1,2  1-3  1,2-3  1,2-3,4  1-3,4
                #       A comma can be followed by a "p" (bug 86164)
                pattern = re.compile("^\d+(?:,p?\d+)?(?:-\d+(?:,p?\d+)?)?$")
                match = pattern.match(optarg)
                if not match:
                    if '-' in optarg:
                        _sendStatusMessage("Can't set selection (invalid range: %s)" % optarg)
                    else:
                        _sendStatusMessage("Can't set selection (invalid line and column: %s)" % optarg)
                else:
                    selection = optarg

        filename = args[0]

        if sys.platform.startswith("win"):
            try:
                koWndWrapper.set_foreground_window(_gHWnd)
            except RuntimeError, ex:
                # XXX This sporadically fails and I don't know why:
                # api_error: (0, 'SetForegroundWindow', 'No error message is available')
                log.error(str(ex))

        # Do file globbing on windows if necessary.
        if sys.platform.startswith("win")\
           and ('*' in filename or '?' in filename):
            filenames = glob.glob(filename)
        else:
            filenames = [filename]

        for f in filenames:
            # "open_file" notification allows position/selection optional
            # argument after the filename (tab-separated).
            try:
                f = f.decode("utf-8")
            except UnicodeDecodeError:
                pass # eh, assume Latin1
            if selection:
                f += "\t" + selection
            try:
                # TODO: Should send a multi-file open request.
                notifyObservers(None, "open_file", f)
            except COMException, e:
                log.warn("No one observing 'open_file' notification.")

    elif name == 'new_window':
        try:
            notifyObservers(None, "new_window", '')
        except COMException, e:
            log.warn("No one observing 'quit' notification.")

    elif name == 'quit':
        try:
            notifyObservers(None, "quit", '')
        except COMException, e:
            log.warn("No one observing 'quit' notification.")

    elif name in ("macro", "macro_file"):
        # Execute the given macro code/file.
        # Usage:
        #   macro [<options>...] <macro-code-repr>
        #   macro_file [<options>...] <filename>
        # Options:
        #   -l <lang>, --language=<lang>
        #       Specify the language of the macro code. This can
        #       currently be one of "python" (the default) or
        #       "javascript".
        # <macro-code-repr> is the repr'd macro code.
        try:
            opts, macro_args = getopt.getopt(args, "l:", ["language="])
        except getopt.error, ex:
            log.error(str(ex))
            return 1
        languages = ("python", "javascript")
        language = languages[0]
        for opt, optarg in opts:
            if opt in ("-l", "--language"):
                language = optarg
                if language not in languages:
                    raise CommandmentError("unknown macro language: '%s' "
                                           "not in %s"
                                           % (language, languages))
        if len(macro_args) != 1:
            raise CommandmentError("incorrect number of arguments: %s"
                                   % macro_args)

        macroSvc = components.classes["@activestate.com/koMacroService;1"]\
                             .getService();
        if name == "macro":
            macro = eval(macro_args[0])
            log.info("run %s macro: '%s'", language, macro)
            macroSvc.runString(language, macro);
        elif name == "macro_file":
            filename = macro_args[0]
            log.info("run %s macro file: '%s'", language, filename)
            macroSvc.runFile(language, filename);

    elif name == "testgui":
        # Run the GUI test suite.
        # Options:
        #   --smoke             Log test results in Smoke.
        #   -s <server>, --server=<server>
        #                       Smoke server to use.
        #   --project-id=<id>   Smoke project id to use. Defaults to the
        #                       given Smoke server's project_id for
        #                       "komodo".
        #   --build-id=<id>     Smoke build id to use. Defaults to a "dev
        #                       build id" for the current machine and Komodo
        #                       "build tree" build.
        try:
            opts, modules = getopt.getopt(args, "s:",
                ["smoke", "server=", "project-id=", "build-id="])
        except getopt.error, ex:
            raise CommandmentError("illegal 'testgui' option: "+str(ex))
        useSmoke = 0
        server = None
        project_id = 0
        build_id = 0
        for opt, optarg in opts:
            if opt == "--smoke":
                useSmoke = 1
            elif opt in ("-s", "--server"):
                server = optarg
            elif opt == "--project-id":
                try:
                    project_id = int(optarg)
                except ValueError, ex:
                    raise CommandmentError("invalid project id: %s" % ex)
            elif opt == "--build-id":
                try:
                    build_id = int(optarg)
                except ValueError, ex:
                    raise CommandmentError("invalid build id: %s" % ex)

        guiTestSvc = components.classes["@activestate.com/koTestSvc;1"]\
                               .getService()
        if useSmoke:
            guiTestSvc.setSmokeInfo(useSmoke, server, project_id,
                                    build_id)
        guiTestSvc.runAllTests()
        guiTestSvc.join()

    else:
        raise CommandmentError("unknown commandment name: '%s'" % name)


#---- main commandment reader thread
if sys.platform.startswith("win"):
    class _CommandmentsReader(threading.Thread):
        """Consume commandments from the commandments.txt file.
        
        The .txt file must by guarded by the appropriate mutex and an
        event is signalled when new commandments are added.
        """
        _product_type = "PRODUCT_TYPE"

        def __init__(self, dname, ver):
            """Create the commandments reader thread.

                "dname" is the directory in which to place files for the
                    commandment system mechanics.
                "ver" is a Komodo version string on which to key
                    commandment system resources (locks, event names, etc.)
            """
            self._commandmentsLockName \
                = "komodo-%s-%s-commandments-lock" % (self._product_type, ver)
            self._commandmentsEventName \
                = "komodo-%s-%s-new-commandments" % (self._product_type, ver)
            self._commandmentsFileName = os.path.join(dname, "commandments.txt")
            threading.Thread.__init__(self, name="CommandmentsReader")
            self.setDaemon(True)

        def run(self):
            lock = koWndWrapper.create_mutex(self._commandmentsLockName)
            # existing: are there commandments from the invoking command-line?
            existing = os.path.exists(self._commandmentsFileName)
            newCommandments = koWndWrapper.create_event(self._commandmentsEventName, None, 1, existing)

            while 1:
                # Wait for new commandments.
                rv = koWndWrapper.wait_for_single_object(newCommandments)
                if rv == koWndWrapper.WAIT_OBJECT_0:
                    retval = 1
                else:
                    raise CommandmentError("Error waiting for new "
                                           "commandments: %r" % rv)
                # Grab the lock.
                koWndWrapper.wait_for_single_object(lock)
                # Consume the commandments.
                f = open(self._commandmentsFileName, 'r')
                cmds = []
                for line in f.readlines():
                    if line[-1] == '\n':
                        line = line[:-1]
                    if line.strip(): # skip empty lines
                        cmds.append(line)
                f.close()
                os.unlink(self._commandmentsFileName)
                # Reset the "new commandments" event.
                koWndWrapper.reset_event(newCommandments)
                # Release the lock.
                koWndWrapper.release_mutex(lock)

                # Handle the commandments.
                exit = 0
                for cmd in cmds:
                    if cmd == "__exit__":
                        exit = 1
                        break
                    else:
                        try:
                            _handleCommandment(cmd)
                        except Exception, ex:
                            tb = ''.join(traceback.format_exception(
                                *sys.exc_info()))
                            log.error("'%s': %s:\n%s", cmd, str(ex), tb)
                            #XXX Dialog proxy's alert() is screwed up.
                            #    It misbehaves and leads to Jaguar
                            #    crash.
                            #dialogProxy = components\
                            #    .classes["@activestate.com/asDialogProxy;1"]\
                            #    .getService(components.interfaces.asIDialogProxy)
                            #msg = "Error handling commandment: '%s'\n\n%s"\
                            #      % (cmd, tb)
                            #dialogProxy.alert(msg)
                if exit:
                    break

            koWndWrapper.close_handle(newCommandments)
            koWndWrapper.close_handle(lock)

        def exit(self):
            # Grab the lock.
            lock = koWndWrapper.create_mutex(self._commandmentsLockName)
            koWndWrapper.wait_for_single_object(lock)
            # Send __exit__ commandment.
            f = open(self._commandmentsFileName, 'a')
            f.write("__exit__\n")
            f.close()
            # Signal that there are new commandments: to ensure worker
            # thread doesn't wedge.
            newCommandments = koWndWrapper.create_event(self._commandmentsEventName)
            koWndWrapper.set_event(newCommandments)
            koWndWrapper.close_handle(newCommandments)
            # Release the lock.
            koWndWrapper.release_mutex(lock)
            koWndWrapper.close_handle(lock)

            self.join()
            try:
                os.remove(self._commandmentsFileName)
            except EnvironmentError:
                pass

else:
    class _CommandmentsReader(threading.Thread):
        def __init__(self, dname, ver):
            """Create the commandments reader thread.

                "dname" is the directory in which to place files for the
                    commandment system mechanics.
                "ver" is a Komodo version string on which to key
                    commandment system resources (locks, event names, etc.)
            """
            self._commandmentsFileName = os.path.join(dname, "commandments.fifo")
            self._firstCommandmentsFileName = os.path.join(dname, "first-commandments.txt")
            threading.Thread.__init__(self, name="CommandmentsReader")
            self.setDaemon(True)

            self._pipe = os.open(self._commandmentsFileName, os.O_RDWR)
            if os.path.exists(self._firstCommandmentsFileName):
                # Commandments from the invoking process are necessarily
                # passed by a separate mechanism.
                cmds = open(self._firstCommandmentsFileName, 'r').read()
                os.remove(self._firstCommandmentsFileName)
                os.write(self._pipe, cmds)
    
        def run(self):
            buf = ""
            while 1:
                text = os.read(self._pipe, 4096)
                buf += text
                lines = buf.splitlines(1)
                # parse out commands
                cmds = []
                for line in buf.splitlines(1):
                    if line.endswith('\n'):
                        cmds.append( line[:-1] )
                    else:
                        buf = line
                        break
                else:
                    buf = ""
                # handle each command
                exit = 0
                for cmd in cmds:
                    if cmd == "__exit__":
                        exit = 1
                        break
                    else:
                        try:
                            _handleCommandment(cmd)
                        except CommandmentError, ex:
                            log.error("'%s': %s", cmd, str(ex))
                if exit:
                    break
    
        def exit(self):
            os.write(self._pipe, "__exit__\n")
            self.join()
            os.close(self._pipe)
            try:
                os.remove(self._commandmentsFileName)
                os.remove(self._firstCommandmentsFileName)
            except EnvironmentError:
                pass


#---- component implementation

class KoCommandmentService(object):
    _com_interfaces_ = [components.interfaces.koICommandmentService,
                        components.interfaces.nsIObserver]
    _reg_clsid_ = "{1ADBCE86-1AE4-4F90-AA85-B230B7510D7B}"
    _reg_contractid_ = "@activestate.com/koCommandmentService;1"
    _reg_desc_ = "Komodo commandment system service"
    _reg_categories_ = [
        ("komodo-delayed-startup-service", "koCommandmentService"),
    ]

    def __init__(self):
        observerSvc = components.classes["@mozilla.org/observer-service;1"]\
            .getService(components.interfaces.nsIObserverService)
        observerSvc.addObserver(self, 'xpcom-shutdown', False)

        # Platform-specific handle on object indicating Komodo is running.
        self._running = None
        # Commandment reader thread.
        self._reader = None

        if sys.platform.startswith("win"):
            global _gHWnd
            try:
                _gHWnd = koWndWrapper.get_active_window()
            except RuntimeError, ex:
                # XXX This sporadically fails:
                # api_error: (0, 'SetForegroundWindow', 'No error message is available')
                # it happens if you switch windows right at a certain
                # moment during startup.  The problem is then that
                # startup really fails in a lot of ways unless we
                # catch this problem here
                log.error(str(ex))

        # Start the commandment reader thread.
        koDirs = components.classes["@activestate.com/koDirs;1"]\
            .getService(components.interfaces.koIDirs)
        infoSvc = components.classes["@activestate.com/koInfoService;1"].getService()
        ver = infoSvc.version          # '1.9.0-devel'
        ver = re.split('\.|-', ver)    # ['1', '9', '0', 'devel']
        ver = "%s.%s" % tuple(ver[:2]) # '1.9'
        self._reader = _CommandmentsReader(koDirs.userDataDir, ver)
        self._reader.start()

    def finalize(self):
        # Shutdown handler thread.
        if self._reader is not None:
            self._reader.exit()

    def observe(self, subject, topic, data):
        if topic == 'xpcom-shutdown':
            self.finalize()
 
    def handleCommandment(self, commandment):
        # For testing only: this will be obselete when the commandment
        # system allows synchronous commandment calls.
        try:
            _handleCommandment(commandment)
        except CommandmentError, ex:
            log.error("'%s': %s", commandment, str(ex))
