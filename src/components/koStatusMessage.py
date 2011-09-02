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

# Status bar message data. (see statusbar.js for details)

from xpcom import components, nsError, COMException
import sys, os, time

# This is now purely a shim class to create a notification of type status.
# This is necessary in order to allow people to still create status messages
# by contract id.
class KoStatusMessage(object):
    _com_interfaces_ = []
    _reg_clsid_ = "{605ce7cb-a712-4b80-b3fb-49004cc14298}"
    _reg_contractid_ = "@activestate.com/koStatusMessage;1"
    _reg_desc_ = "Komodo Status Message"

    def __new__(cls):
        nm = components.classes["@activestate.com/koNotification/manager;1"]\
                       .getService(components.interfaces.koINotificationManager)
        return nm.createNotification("status-notification-%s" % (time.time(),),
                                     ["status"],
                                     None,
                                     components.interfaces.koINotificationManager.TYPE_STATUS)

class KoStatusMessageStack:
    _com_interfaces_ = [components.interfaces.koIStatusMessageStack]
    _reg_clsid_ = "{e30afa49-c889-45b8-a1a7-37036898b0a7}"
    _reg_contractid_ = "@activestate.com/koStatusMessageStack;1"
    _reg_desc_ = "Komodo Status Message Stack"

    def __init__(self):
        # dictionary of category->message
        self._messages = {}
        # ordered list of categories, first in the list shows on the statusbar
        self._order = []
    
    def _CullExpiredMessages(self):
        cullList = []
        curTime = time.time()
        for sm in self._messages.values():
            try:
                if sm.expiresAt and sm.expiresAt < curTime:
                    cullList.append(sm.category)
                    del self._messages[sm.category]
            except AttributeError:
                pass
        self._order = [c for c in self._order if c not in cullList]
    
    def Push(self, sm):
        if not sm.msg:
            # If the added message string is empty then remove that category.
            try:
                del self._messages[sm.category]
            except KeyError:
                pass
            self._order = [c for c in self._order if c != sm.category]
        else:
            # Otherwise, replace the msg for this category and promote the
            # category to the top of the stack. If the message has a timeout
            # then timestamp when this message expires.
            if sm.timeout:
                sm.expiresAt = time.time() + float(sm.timeout)/1000.0
            self._messages[sm.category] = sm
            order = [c for c in self._order if c != sm.category]
            if sm.timeout:
                # timeout messages next
                self._order = [sm.category] + order
            elif sm.interactive:
                # interactive messages trump
                self._order = [sm.category] + order
            else:
                # insert after last message with timeout or interactive
                for i in range(len(order)):
                    m = self._messages[order[i]]
                    if not m.timeout and not m.interactive:
                        self._order = order[:i] + [sm.category] + order[i:]
                        break
                else:
                    self._order = order + [sm.category]

    def Top(self):
        self._CullExpiredMessages()
        try:
            return self._messages[self._order[0]]
        except IndexError:
            return None

    def Dump(self):
        """Dump the current stack to stdout."""
        stack = []
        for key in self._order:
            sm = self._messages[key]
            smdict = {'category': sm.category,
                      'msg': sm.msg,
                      'timeout': sm.timeout,
                      'highlight': sm.highlight,
                      'expiresAt': sm.expiresAt,
                     }
            stack.append(smdict)
        import pprint
        pprint.pprint(stack)

