# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Komodo.
#
# The Initial Developer of the Original Code is
# ActiveState Software Inc.
# Portions created by the Initial Developer are Copyright (C) 2011
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
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

import logging
from xpcom import components, COMException, nsError
from xpcom.client import Component

log = logging.getLogger("KoNotificationAsyncCallbackAdapter")
#log.setLevel(logging.DEBUG)

Ci = components.interfaces
koINotificationManager = Ci.koINotificationManager

class KoNotificationAsyncCallbackAdapter(object):
    _com_interfaces_ = [Ci.koINotificationAsyncCallbackAdapter,
                        Ci.koIAsyncCallback,
                        Ci.koIAsyncCallbackWithProgress]
    _reg_clsid_ = "{4856061a-0ea1-463d-8ec3-1088ec444281}"
    _reg_contractid_ = "@activestate.com/koNotification/AsyncCallbackAdapter;1"
    _reg_desc_ = "Komodo Notification / Async Callback Adapter"

    def __init__(self):
        self.next = None
        self.notification = None

    # koINotificationAsyncCallbackAdapter
    def initAsyncAdapter(self, operation, identifier, tags, context, types):
        log.debug("initAsyncAdapter: %r = %r/%r/%r", operation, identifier,
                  tags, context)
        self._nm = components.classes["@activestate.com/koNotification/manager;1"]\
                             .getService(koINotificationManager)
        self.notification = \
            self._nm.createNotification(identifier,
                                        tags,
                                        context,
                                        koINotificationManager.TYPE_PROGRESS |
                                          koINotificationManager.TYPE_TEXT |
                                          types)
        self.notification.QueryInterface(Ci.koINotificationProgress)
        self.notification.progress = 0
        self.notification.maxProgress = Ci.koINotificationProgress.PROGRESS_INDETERMINATE
        self._nm.addNotification(self.notification)

    # koIAsyncCallback
    def callback(self, result, data):
        log.debug("callback: %r, %r (%r)", result, data, self.next)
        # the progress is completed
        if self.notification.maxProgress == Ci.koINotificationProgress.PROGRESS_INDETERMINATE:
            # we don't want indeterminate on complete
            self.notification.maxProgress = 100
        self.notification.progress = self.notification.maxProgress
        self.notification.severity = {
                Ci.koIAsyncCallback.RESULT_SUCCESSFUL: Ci.koINotification.SEVERITY_INFO,
                Ci.koIAsyncCallback.RESULT_STOPPED:    Ci.koINotification.SEVERITY_WARNING,
                Ci.koIAsyncCallback.RESULT_ERROR:      Ci.koINotification.SEVERITY_ERROR,
            }.get(result, self.notification.severity)
        if self.notification.details is None:
            self.notification.details = ""
        elif len(self.notification.details) > 0 and not self.notification.details.endswith("\n"):
            self.notification.details += "\n"
        if isinstance(data, (str, unicode)) and len(data) > 0:
            self.notification.details += data
        elif isinstance(data, Component):
            try:
                data.QueryInterface(components.interfaces.nsIException)
                self.notification.details += data.toString()
            except COMException, e:
                if e.number != nsError.NS_ERROR_NO_INTERFACE:
                    raise

        # hide all actions on completion
        try:
            self.notification.QueryInterface(Ci.koINotificationActionable)
            for action in self.notification.getActions():
                action.visible = False
                self.notification.updateAction(action)
        except COMException, e:
            if e.number != nsError.NS_ERROR_NO_INTERFACE:
                raise

        self._nm.addNotification(self.notification)
        # chain to the other callback
        if self.next is not None:
            try:
                self.next.QueryInterface(components.interfaces.koIAsyncCallback)
                self.next.callback(result, data)
            except COMException, e:
                if getattr(e, "number", None) != nsError.NS_ERROR_NO_INTERFACE:
                    raise

    # koIAsyncCallbackWithProgress
    def onProgress(self, label, value):
        log.debug("onProgress: %r, %r (%r)", label, value, self.next)
        # update the progress notification
        self.notification.maxProgress = 100
        self.notification.progress = value
        self.notification.description = label
        self._nm.addNotification(self.notification)
        # chain to the other callback
        if self.next is not None:
            try:
                self.next.QueryInterface(components.interfaces.koIAsyncCallbackWithProgress)
                self.next.onProgress(label, value)
            except COMException, e:
                if e.number != nsError.NS_ERROR_NO_INTERFACE:
                    raise

PYXPCOM_CLASSES = [KoNotificationAsyncCallbackAdapter]
