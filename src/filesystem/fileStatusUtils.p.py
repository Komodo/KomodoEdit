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

import os
import sys
import time
import types
import logging
import copy
from urllib import unquote as unescapeURL

from xpcom import components
from xpcom.server import UnwrapObject

# Pref names each checker should have, will be monitored when the checker
# is first added and gets automatically updated through a pref observer.
monitoredPrefNames = { "enabledPrefName": { 'type': types.BooleanType,
                                            'default': True },
                       "executablePrefName": { 'type': types.StringType,
                                               'default': None },
                       "backgroundEnabledPrefName": { 'type': types.BooleanType,
                                                      'default': True },
                       "backgroundDurationPrefName": { 'type': types.LongType,
                                                       'default': 15 },
                       "recursivePrefName": { 'type': types.BooleanType,
                                              'default': False },
}

class KoFileCheckerBase(object):

    name = 'unknown'
    _com_interfaces_ = [components.interfaces.nsIObserver,
                        components.interfaces.koIFileStatusChecker,
                        components.interfaces.koIPythonMemoryReporter]

    # Save have to look this up all over the status checker code.
    _is_windows = sys.platform.startswith("win")

    def __init__(self, type):
        self.type = type

        # Dictionary of when a URI was last checked.
        # Note: On Windows, the URI must be lowered, because it's a case
        #       insensitive filesystem and we never can be sure which case
        #       styling will be used. You should use the "_norm_uri_cache_key"
        #       method for this (below).
        #       http://bugs.activestate.com/show_bug.cgi?id=74339
        self._lastChecked = {}

        # How prefName and matching attribute values work:
        #  When a checker is initialized, the prefName(s) are checked and the
        #  pref value is stored into the correctponding attribute name. A pref
        #  observer is added on the preference and when/if this preference ever
        #  changes, then the checker's value will be automatically updated.
        # Example for CVS:
        #    backgroundDurationPrefName = "cvsBackgroundMinutes"
        #    backgroundDuration = 10

        self.enabled = True
        self.enabledPrefName = None
        self.backgroundEnabled = False
        self.backgroundEnabledPrefName = None
        # We store the duration in seconds.
        self.backgroundDuration = 15 * 60   # 15 minutes
        self.backgroundDurationPrefName = None
        self.recursive = 0
        self.recursivePrefName = None
        self.executable = None
        self.executablePrefName = None

        self.log = logging.getLogger('Ko%sChecker.%s' % (self.type.capitalize(), self.name))
        self._globalPrefs = components.classes["@activestate.com/koPrefService;1"].\
            getService(components.interfaces.koIPrefService).prefs
        # Global observer service.
        self._observerSvc = components.classes["@mozilla.org/observer-service;1"].\
            getService(components.interfaces.nsIObserverService)

        # Copy across names from the interface in to the local instance.
        self.REASON_BACKGROUND_CHECK = components.interfaces.koIFileStatusChecker.REASON_BACKGROUND_CHECK
        self.REASON_ONFOCUS_CHECK = components.interfaces.koIFileStatusChecker.REASON_ONFOCUS_CHECK
        self.REASON_FILE_CHANGED = components.interfaces.koIFileStatusChecker.REASON_FILE_CHANGED
        self.REASON_FORCED_CHECK = components.interfaces.koIFileStatusChecker.REASON_FORCED_CHECK

    def reportMemory(self, reportHandler, closure):
        self.log.info("reportMemory")

        process = ""
        kind_other = components.interfaces.nsIMemoryReporter.KIND_OTHER
        units_count = components.interfaces.nsIMemoryReporter.UNITS_COUNT

        amount = len(self._lastChecked)
        if amount > 0:
            reportHandler.callback(process,
                                   "komodo scc-%s-checked-directories" % (self.name, ),
                                   kind_other,
                                   units_count,
                                   amount, # amount
                                   "The number of directories this checker was asked to check.", # tooltip description
                                   closure)
        return 0

    ##
    # Helper function to ensure the cache key "uri" is consistently the same,
    # no matter how the platform handles filename case sensitivity or
    # whether the uri has been escaped.
    def _norm_uri_cache_key(self, uri):
        uri = unescapeURL(uri)
        if self._is_windows:
            return uri.lower()
        return uri

    ##
    # Helper function to check if the nsIURI object has a UNC path.
    def _is_nsURI_UNC(self, nsUri):
        return (self._is_windows and nsUri.scheme == 'file' and nsUri.host)

    ##
    # Helper function to ensure the cache is completely cleared.
    def _invalidateAllCaches(self):
        self._lastChecked = {}

    #  Interface method
    def initialize(self):
        prefObserverSvc = self._globalPrefs.prefObserverService
        for prefSetting, prefData in monitoredPrefNames.items():
            prefType = prefData['type']
            prefDefault = prefData['default']
            prefName = getattr(self, prefSetting)
            if prefName:
                variableName = prefSetting.replace("PrefName", "")
                # Update from the preference
                if prefType == types.BooleanType:
                    setattr(self, variableName,
                            self._globalPrefs.getBoolean(prefName, prefDefault))
                elif prefType == types.SliceType:
                    setattr(self, variableName,
                            self._globalPrefs.getString(prefName, prefDefault))
                elif prefType == types.LongType:
                    value = self._globalPrefs.getLong(prefName, prefDefault)
                    if variableName == "backgroundDuration":
                        # Convert from minutes to seconds.
                        value *= 60
                    setattr(self, variableName, value)

                # Listen for pref changes
                prefObserverSvc.addObserver(self, prefName, 0)
        # Register for a shutdown notification.
        self._observerSvc.addObserver(self, 'xpcom-shutdown', False)

    def _xpcom_shutdown(self):
        prefObserverSvc = self._globalPrefs.prefObserverService
        for prefSetting in monitoredPrefNames:
            prefName = getattr(self, prefSetting)
            if prefName:
                prefObserverSvc.removeObserver(self, prefName)
        self._observerSvc.removeObserver(self, 'xpcom-shutdown')

    ##
    # nsIObserver interface: listens for preference changes
    # @private
    def observe(self, subject, topic, data):
        self.log.debug("observing event %s:%s" % (topic, data))
        if not topic:
            return

        if topic == 'xpcom-shutdown':
            self._xpcom_shutdown()
        elif topic == self.executablePrefName:
            # data is actually the pref name that was changed.
            executable = self._globalPrefs.getStringPref(topic)
            if executable != self.executable:
                self.setExecutable(executable)
                self._invalidateAllCaches()
                fileStatusSvc = components.classes["@activestate.com/koFileStatusService;1"].\
                                    getService(components.interfaces.koIFileStatusService)
                fileStatusSvc.updateStatusForAllFiles(self.REASON_ONFOCUS_CHECK)
        elif topic == self.enabledPrefName:
            enabled = self._globalPrefs.getBoolean(self.enabledPrefName, True)
            if enabled != self.enabled:
                self.enabled = enabled
                self._invalidateAllCaches()
                fileStatusSvc = components.classes["@activestate.com/koFileStatusService;1"].\
                                    getService(components.interfaces.koIFileStatusService)
                fileStatusSvc.updateStatusForAllFiles(self.REASON_ONFOCUS_CHECK)
        elif topic == self.backgroundEnabledPrefName:
            backgroundEnabled = self._globalPrefs.getBoolean(topic, True)
            if backgroundEnabled != self.backgroundEnabled:
                self.backgroundEnabled = backgroundEnabled
        elif topic == self.backgroundDurationPrefName:
            backgroundDuration = self._globalPrefs.getLong(topic, 15) * 60
            if backgroundDuration != self.backgroundDuration:
                self.backgroundDuration = backgroundDuration
        elif topic == self.recursivePrefName:
            self.recursive =  self._globalPrefs.getBoolean(topic, False)

    #  Interface method
    def shutdown(self):
        # Remove pref listeners
        prefObserverSvc = self._globalPrefs.prefObserverService
        for prefSetting in monitoredPrefNames:
            prefName = getattr(self, prefSetting)
            if prefName:
                try:
                    prefObserverSvc.removeObserver(self, prefName, 0)
                except:
                    # prefs shutdown already?
                    self.log.debug("Unable to remove prefs observers")

    #  Interface method
    def isActive(self):
        return self.enabled

    #  Interface method
    def isBackgroundCheckingEnabled(self):
        return False

    #  Interface method
    def needsToReCheckFileStatus(self, koIFile, reason):
        return True

    #  Interface method
    def updateFileStatus(self, koIFile, reason):
        return None

    def setExecutable(self, executable):
        self.executable = executable

class KoDiskFileChecker(KoFileCheckerBase):

    name = 'disk'
    _reg_clsid_ = "{4871ae1f-edb2-4e2b-b35f-85109aea68ef}"
    _reg_contractid_ = "@activestate.com/koFileStatusChecker?type=disk;1"
    _reg_desc_ = "Komodo Disk Status Checker"
    #_reg_categories_ = [
    #     ("category-komodo-file-status",      "disk"),
    #     ]

    ranking_weight = 5

    def __init__(self):
        KoFileCheckerBase.__init__(self, 'disk')
        self.enabledPrefName = 'diskStatusEnabled'
        self.backgroundEnabledPrefName = 'diskBackgroundCheck'
        self.backgroundDurationPrefName = 'diskBackgroundMinutes'

    def isBackgroundCheckingEnabled(self):
        return True

    def updateFileStatus(self, koIFile, reason):
        if koIFile.isLocal and not koIFile.isNetworkFile:
            time_now = time.time()
            cache_key = self._norm_uri_cache_key(koIFile.URI)
            if reason == self.REASON_BACKGROUND_CHECK and \
               (self._lastChecked.get(cache_key, 0) >=
                (time_now - self.backgroundDuration)):
                return 0
            self._lastChecked[cache_key] = time_now
            return koIFile.updateStats()
        elif reason == self.REASON_FORCED_CHECK:
            # Forced, updateStats() will cause a refresh from the remote server.
            return koIFile.updateStats()
        return 0
