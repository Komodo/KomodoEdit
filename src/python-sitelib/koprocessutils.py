
# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

"""
    Some utility routines for using Komodo's process control facilities.

    Note: This file should be initialized from the main thread by calling
    its "initialize" method.    

    HOWTO spawn a process with the user's (pre-komodo-mucking)
    environment:

      import process
      import koprocessutils

      env = koprocessutils.getUserEnv()
      # make any desired changes to 'env'...
      #   - Only insert unicode strings because: Win32's CreateProcess
      #     requires that all strings in 'env' either be plain strings
      #     or all unicode strings and getUserEnv() just converts
      #     everything to unicode. (XXX This conversion is obselete since
      #     _SaferCreateProcess in process.py.)

      p = process.ProcessOpen(cmd, env=env)
"""

from xpcom import components, nsError, ServerException

#---- globals

_gUserEnvCache = None


#---- public methods

def initialize():
    """Startup and use required services from the main thread.
    
    This implies that this method must be called from the main thread.
    """
    global _gUserEnvCache
    userEnvSvc = components.classes["@activestate.com/koUserEnviron;1"].getService()
    userEnv = {}
    for piece in userEnvSvc.GetEnvironmentStrings():
        key, val = piece.split('=', 1)
        #XXX This unicode conversion is not necessary since
        #    _SaferCreateProcess in process.py. Keeping it for Komodo 2.0
        #    release though.
        userEnv[unicode(key)] = unicode(val)
    _gUserEnvCache = userEnv

def resetUserEnv():
    """Reset the user environment cache."""
    global _gUserEnvCache
    _gUserEnvCache = None
    initialize()

def getUserEnv():
    """Return an environment dictionary representing the user's
    environment when Komodo was started.
    """
    if _gUserEnvCache is None:
        raise ServerException(nsError.NS_ERROR_NOT_INITIALIZED,
                              "koprocessutils module was not initialized")
    return dict(_gUserEnvCache)


