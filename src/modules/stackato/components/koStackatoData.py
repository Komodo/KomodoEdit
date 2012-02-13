#!/usr/bin/env python
# Copyright (C) 2004-2011 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.
                        
"""koStackatoData - supply back-end for the stackato interface"""

import os, sys, re
from koTreeView import TreeView
import copy
import json
import logging
import time

import process
import which

from xpcom import components, COMException, ServerException, nsError
from xpcom.server import UnwrapObject

from koAsyncOperationUtils import koAsyncOperationBase 


log = logging.getLogger("koStackatoData")
log.setLevel(logging.INFO)

#---- globals
# These are init'ed in KoStackatoData.__init__
stackatoPath = None
gprefs = None

def _getJSON(cmd, args=None):
    argv = [stackatoPath, cmd]
    if args:
        argv += args
    argv.append("--json")
    p = process.ProcessOpen(argv, cwd=None, env=None, stdin=None)
    stdout, stderr = p.communicate()
    if stderr:
        if not stdout:
            if "Login Required" in stderr and "Please use 'stackato login'" in stderr:
                log.error(stderr)
                return None
            raise ServerException(nsError.NS_ERROR_FAILURE, "stackato %s failed: %s" % (cmd, stderr))
        else:
            log.error("stackato %s error message: %s" % (cmd, stderr))
    return json.loads(stdout)

class KoStackatoResultBlock(object):
    _com_interfaces_ = [components.interfaces.koIStackatoResultBlock]
    _reg_clsid_ = "{37c5cad5-31aa-4b93-ae12-98a7cc912bce}"
    _reg_contractid_ = "@activestate.com/KoStackatoResultBlock;1"
    _reg_desc_ = "contains raw results of running a command"
    
    def initialize(self, stdout, stderr):
        self.stdout = stdout
        self.stderr = stderr

def _runCommand(cmd, *args, **kwargs):
    argv = [stackatoPath, cmd]
    if args:
        argv += args
    if not kwargs.get('noJSON', False):
        argv.append("--json")
    #qlog.debug("_runCommand: <<%s>>", argv)
    p = process.ProcessOpen(argv, cwd=None, env=None, stdin=None)
    stdout, stderr = p.communicate()
    #qlog.debug("cmd: %s, stdout: %s, stderr: %s", argv, stdout, stderr)
    koResult = components.classes["@activestate.com/KoStackatoResultBlock;1"].\
        createInstance(components.interfaces.koIStackatoResultBlock)
    UnwrapObject(koResult).initialize(stdout, stderr)
    return koResult

class KoStackatoServices(object):
    _com_interfaces_ = [components.interfaces.koIStackatoServices]
    _reg_clsid_ = "{e15aec1e-6f38-477d-afca-1524b3e2ecb8}"
    _reg_contractid_ = "@activestate.com/koStackatoServices;1"
    _reg_desc_ = "backend handler for stackato"
    
    def __init__(self):
        self._target = None
        self._user = None
        self._processHelper = process.AbortableProcessHelper()
    
    def initialize(self): #pylint: disable=R0201
        #log.debug(">> KoStackatoData.initialize")
        global gprefs, stackatoPath #pylint: disable=W0603
        gprefs = components.classes["@activestate.com/koPrefService;1"].\
                                getService(components.interfaces.koIPrefService).prefs
        if gprefs.hasPref("stackato.location"):
            stackatoPath = gprefs.getStringPref("stackato.location")
            #qlog.debug("+1: stackatoPath: %s", stackatoPath)
        if not stackatoPath:
            try:
                stackatoPath = which.which('stackato')
                #log.debug("+ 2: stackatoPath: %s", stackatoPath)
            except which.WhichError:
                log.exception("+ 3: no stackato!")
                pass
        if not stackatoPath:
            #log.debug("stackatoPath: %s", "<NONE>")
            pass
        #log.debug("<< KoStackatoData.initialize")
    
    def get_target(self):
        if self._target is None:
            self._target = _getJSON('target')['target']
        return self._target
    
    def set_target(self, target):
        self._target = target
        # Stuff to refresh?

    def get_user(self):
        if self._user is None:
            user = _getJSON("user")[0]
            if user == "N/A":
                user = ""
            self._user = user
        return self._user
    
    def set_user(self, user):
        self._user = user
        # Stuff to refresh?
       
    def runCommandAsynchronously(self, cmd_name, run_function, async_callback,
                                 *args, **kwargs):
        # Run asynchronously
        async_svc = components.classes["@activestate.com/koAsyncService;1"].\
                        getService(components.interfaces.koIAsyncService)
        async_op = koAsyncOperationBase(run_function, *args, **kwargs)
        async_svc.run("Stackato %s" % (cmd_name),
                      async_op, async_callback, [], False)
        return async_op
        
    def login(self, user, password, async_callback):
        if not user:
            log.error("login called without a username")
            return False
        if password is None:
            password = ""
        return self.runCommandAsynchronously("login",
                                             self._login,
                                             async_callback,
                                             user, password)

    def _login(self, *args):
        try:
            result = _runCommand("login", args[0], "--passwd", args[1])
            #qlog.debug(" _login: result.stdout:%s, result.stderr:%s",
            #           result.stdout, result.stderr)
            if result.stdout and not result.stderr:
                self.set_user(result.stdout)
            return result
        except:
            log.exception("_login failed")
        
    def logout(self, async_callback):
        return self.runCommandAsynchronously("logout",
                                             self._logout,
                                             async_callback)

    def _logout(self):
        return _runCommand("logout", noJSON=True)

    def runCommand(self, async_callback, args):
        return self.runCommandAsynchronously("generic run command",
                                             self._doRunCommand,
                                             async_callback,
                                             args)

    def _doRunCommand(self, args):
        try:
            #qlog.debug(" _doRunCommand: cmd: %s", args)
            noJSON = "--json" not in args
            result = _runCommand(args[0], *args[1:], noJSON=noJSON)
            #qlog.debug(" _doRunCommand: result.stdout:%s, result.stderr:%s",
            #           result.stdout, result.stderr)
            return result
        except:
            log.exception("_doRunCommand failed")
        
    def getApplications(self, async_callback):
        return self.runCommandAsynchronously("getApplications",
                                             self._getApplications,
                                             async_callback)

    def _getApplications(self):
        return _runCommand("apps")

    def getServices(self, async_callback):
        return self.runCommandAsynchronously("getServices",
                                             self._getServices,
                                             async_callback)

    def _getServices(self):
        return _runCommand("services")

    def getFrameworks(self, async_callback):
        return self.runCommandAsynchronously("getFrameworks",
                                             self._getFrameworks,
                                             async_callback)

    def _getFrameworks(self):
        return _runCommand("frameworks")

    def getRuntimes(self, async_callback):
        return self.runCommandAsynchronously("getRuntimes",
                                             self._getRuntimes,
                                             async_callback)

    def _getRuntimes(self):
        return _runCommand("runtimes")

    def getTargets(self, async_callback):
        return self.runCommandAsynchronously("getTargets",
                                             self._getTargets,
                                             async_callback)

    def _getTargets(self):
        return _runCommand("targets")

    def runCommandInTerminal(self, async_callback, terminalHandler, args, env):
        # Run asynchronously
        self.terminalHandler = UnwrapObject(terminalHandler)
        import koprocessutils
        currentEnv = koprocessutils.getUserEnv()
        newEnvParts = env.split(";")
        for part in newEnvParts:
            parts = part.split("=")
            if len(parts) == 2:
                currentEnv[parts[0]] = parts[1]
            else:
                currentEnv[parts[0]] = ""
        self.env = currentEnv
        async_svc = components.classes["@activestate.com/koAsyncService;1"].\
                        getService(components.interfaces.koIAsyncService)
        async_op = koAsyncOperationBase(self._doRunCommandInTerminal, args)
        async_svc.run("Stackato %s" % (args[0]),
                      async_op, async_callback, [], False)
        return async_op

    def _doRunCommandInTerminal(self, args):
        argv = [stackatoPath] + args
        try:
            p = self._processHelper.ProcessOpen(cmd=argv,
                                                cwd=None,
                                                env=self.env,
                                                stdin=None,
                                                universal_newlines=True)
        except:
            log.exception("Failed to run: %s", argv)
            raise
        try:
            self.terminalHandler.hookIO(p.stdin, p.stdout, p.stderr, " ".join(args))
        except:
            log.exception("Failed to run: %s", argv)
            raise
        p.wait()
        p.close()
