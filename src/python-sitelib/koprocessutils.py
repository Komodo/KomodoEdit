
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
    if 'PWD' in userEnv:
        del userEnv['PWD']
    _gUserEnvCache = userEnv

def resetUserEnv():
    """Reset the user environment cache."""
    global _gUserEnvCache
    first_initialization = _gUserEnvCache is None
    initialize()
    if not first_initialization:
        # Notify that the user environment has changed.
        obsSvc = components.classes["@mozilla.org/observer-service;1"]. \
                        getService(components.interfaces.nsIObserverService)
        obsSvc.notifyObservers(None, "user_environment_changed", "")

def getUserEnv():
    """Return an environment dictionary representing the user's
    environment when Komodo was started.
    """
    if _gUserEnvCache is None:
        raise ServerException(nsError.NS_ERROR_NOT_INITIALIZED,
                              "koprocessutils module was not initialized")
    return dict(_gUserEnvCache)


