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

# timeline - a Python interface into the Mozilla "timeline" service.
#
# To enable the timeline service in Mozilla:
# * Configure and build with "--enable-timeline" (I did it
#   by adding "ac_add_options --enable-timeline" to .mozconfig)
# * Set NS_TIMELINE_ENABLE=1
# * Set NS_TIMELINE_LOG_FILE=filename - default is stdout
#   which includes lots of noise.
#
# These functions are designed to be as fast as possible
# when the timeline is not available, so should be capable
# of being called in "production" code (although we do still
# incur the standard Python call overhead.)

from xpcom import components, COMException, _xpcom
import xpcom

import warnings
warnings.warn("'timeline' module is deprecated and will soon be removed.",
              DeprecationWarning)

enabled = None
timeline_service = None

def _setup():
    global enabled, timeline_service
    if enabled is None:
        try:
            timeline_service = components.classes["@mozilla.org;timeline-service;1"] \
                               .createInstance() \
                               .queryInterface(components.interfaces.nsITimelineService)
            enabled = 1
        except COMException:
            enabled = 0
    if enabled:
        # See if we can use it - returns errors if we can't
        try:
            timeline_service.indent()
            timeline_service.outdent()
        except Exception:
            enabled = 0
            timeline_service = None
        except COMException:
            enabled = 0
            timeline_service = None
    return enabled

# We need to make the strings "immortal", as their raw address is
# used by the timeline service.
_keys={}
def _intern(name):
    _keys[name] = 1
    return name

def getService():
    _setup()
    return timeline_service

def startTimer(name):
    if enabled == 0 or not _setup(): return # quick exit
    # _intern the name to ensure the exact same pointer passed to xpcom
    timeline_service.startTimer(_intern(name))

def stopTimer(name):
    if enabled == 0 or not _setup(): return # quick exit
    # _intern the name to ensure the exact same pointer passed to xpcom
    timeline_service.stopTimer(_intern(name))

def resetTimer(name):
    if enabled == 0 or not _setup(): return # quick exit
    # _intern the name to ensure the exact same pointer passed to xpcom
    timeline_service.resetTimer(_intern(name))

def markTimer(name, text=None):
    if enabled == 0 or not _setup(): return # quick exit
    # _intern the name to ensure the exact same pointer passed to xpcom
    if text is None:
        timeline_service.markTimer(_intern(name))
    else:
        timeline_service.markTimerWithComment(_intern(name), text)

def mark(text):
    if enabled == 0 or not _setup(): return # quick exit
    timeline_service.mark(_intern(text))

def indent():
    if enabled == 0 or not _setup(): return # quick exit
    timeline_service.indent()

def outdent():
    if enabled == 0 or not _setup(): return # quick exit
    timeline_service.outdent()

# enter/leave bracket code with "<text>..." and "...<text>" as
# well as indentation.
def enter(text):
    if enabled == 0 or not _setup(): return # quick exit
    timeline_service.enter(_intern(text))
    startTimer(text)


def leave(text):
    if enabled == 0 or not _setup(): return # quick exit
    stopTimer(text)
    markTimer(text)
    resetTimer(text)
    timeline_service.leave(_intern(text))

# A helper to cleanup our namespace as xpcom shuts down.
class _ShutdownObserver:
    _com_interfaces_ = components.interfaces.nsIObserver
    def observe(self, service, topic, extra):
        global timeline_service, _shutdownObserver
        timeline_service = _shutdownObserver = None


svcMgr = _xpcom.GetServiceManager()
if hasattr(svcMgr,'getServiceByContractID'):
    _shutdownObserver = xpcom.server.WrapObject(_ShutdownObserver(), components.interfaces.nsIObserver)
    svcMgr.getServiceByContractID("@mozilla.org/observer-service;1", components.interfaces.nsIObserverService) \
            .addObserver(_shutdownObserver, "xpcom-shutdown", 1)
    # Observers will be QI'd for a weak-reference, so we must keep the
    # observer alive ourself, and must keep the COM object alive,
    # _not_ just the Python instance!!!
    # Say we want a weak ref due to an assertion failing.  If this is fixed, we can pass 0,
    # and remove the lifetime hacks above!  See http://bugzilla.mozilla.org/show_bug.cgi?id=99163
    del _ShutdownObserver
