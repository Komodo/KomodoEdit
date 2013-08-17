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

import logging, weakref
from xpcom import components, COMException, nsError

log = logging.getLogger("koNotification")
Ci = components.interfaces

def _createProperty(name, defaultValue=None, setCheck=None):
    """Define a property
    @param name {str} The name of the real property
    @param defaultValue The default value for the property
    @param setCheck {callable} A method to call to ensure the value being
        set is valid. Takes two arguments, self and the new value.
        Return True to allow the set, False to stop it.
    """
    def getter(self):
        return getattr(self, name, defaultValue)

    def setter(self, value):
        if setCheck is not None and not setCheck(self, value):
            raise COMException(nsError.NS_ERROR_ILLEGAL_VALUE)
        oldVal = getattr(self, name, defaultValue)
        setattr(self, name, value)

    return property(getter, setter)

gConstructors = {}
""" Map of createNotification flags -> classes to use """

class KoNotification(object):
    """Stub class used as the constructor for the various possible combinations
    of notification types.
    """
    def __new__(cls, identifier, tags, context, types, mgr):
        if not types in gConstructors:
            bases = []
            interfaces = [Ci.koINotification, Ci.nsIClassInfo]
            if types & Ci.koINotificationManager.TYPE_ACTIONABLE:
                bases.append(KoNotificationActionable)
                interfaces.append(Ci.koINotificationActionable)
            if types & Ci.koINotificationManager.TYPE_PROGRESS:
                bases.append(KoNotificationProgress)
                interfaces.append(Ci.koINotificationProgress)
            if types & Ci.koINotificationManager.TYPE_TEXT:
                bases.append(KoNotificationText)
                interfaces.append(Ci.koINotificationText)
            if types & Ci.koINotificationManager.TYPE_STATUS:
                bases.append(KoNotificationStatus)
                interfaces.append(Ci.koIStatusMessage)
            bases.append(KoNotificationBase)
            def init(self, *args, **kwargs):
                KoNotificationBase.__init__(self, *args, **kwargs)
                for base in bases:
                    if base != KoNotificationBase:
                        base.__init__(self)
            gConstructors[types] = type("KoNotification%s" % (types,),
                                        tuple(bases),
                                        {"__init__": init,
                                         "_com_interfaces_": interfaces})

        return gConstructors[types](identifier, tags, context, mgr)

class KoNotificationBase(object):
    """The base notification type, implementing koINotification"""
    _com_interfaces_ = [] # see KoNotification.__new__
    _reg_desc_ = "Komodo Notification Object"

    sticky = False

    def __init__(self, identifier, tags, context, mgr):
        self.identifier = str(identifier)

        self.__manager = weakref.ref(mgr)
        tags = map(lambda s: s.lower(), filter(None, tags)) # drop empty tags
        self.tags = list(set(tags)) # drop repeated tags
        self.contxt = context

    @property
    def _manager(self):
        """Get the notification manager, if this notification is currently being
        tracked by the manager. Return None if the manager is unaware of us.
        """
        manager = self.__manager()
        if manager and self in manager:
            return manager
        return None

    for attr in ("summary", "iconURL", "description"):
        locals()[attr] = _createProperty("_" + attr, None)
    severity = _createProperty("_severity", 0)
    time = 0 # updating time does _not_ fire notifications
    contxt = context = _createProperty("_context")

    def getTags(self):
        return self.tags

    # nsIClassInfo - the way we play with _com_interfaces_ makes PyXPCOM confused
    # and it won't implement ClassInfo for us
    def getInterfaces(self):
        return self._com_interfaces_[:]
    def getHelperForLanguage(self, language):
        return None
    contractID = None
    classDescription = _reg_desc_
    classID = None
    implementationLanguage = Ci.nsIProgrammingLanguage.PYTHON
    flags = Ci.nsIClassInfo.THREADSAFE

class KoNotificationActionable(KoNotificationBase):
    """Mixin to implement koINotificationActionable"""
    def __init__(self):
        self.actions = []

    def getActions(self, actionId=None):
        if not actionId:
            return list(self.actions)
        return filter(lambda a: a.identifier == actionId, self.actions)

    def updateAction(self, action):
        if not action.identifier:
            raise COMException(nsError.NS_ERROR_NOT_INITIALIZED,
                               "action has no identifier")
        oldaction = self.getActions(action.identifier)
        if oldaction:
            self.actions[self.actions.index(oldaction[0])] = action
        else:
            self.actions.append(action)
        manager = self._manager
        if manager:
            try:
                index = manager.index(manager._wrap(self))
                manager._notify(self, Ci.koINotificationListener.REASON_UPDATED,
                                aOldIndex=index, aNewIndex=index)
            except ValueError:
                # we have a manager, but we're not in it?
                pass
        return len(oldaction) > 0

    def removeAction(self, actionId):
        action = self.getActions(actionId)
        if action:
            self.actions.remove(action[0])
            manager = self._manager
            if manager:
                try:
                    index = manager.index(manager._wrap(self))
                    manager._notify(self, Ci.koINotificationListener.REASON_UPDATED,
                                    aOldIndex=index, aNewIndex=index)
                except ValueError:
                    # we have a manager, but we're not in it?
                    pass
            return True
        return False
    

class KoNotificationProgress(KoNotificationBase):
    """Mixin to implement koINotificationProgress"""
    def __init__(self): pass
    maxProgress = _createProperty("_maxProgress", 0,
                                  lambda self, v: v in (Ci.koINotificationProgress.PROGRESS_INDETERMINATE,
                                                        Ci.koINotificationProgress.PROGRESS_NOT_APPLICABLE) or
                                                  v > 0)
    progress = _createProperty("_progress", 0,
                               lambda self, v: v >= 0 and (self.maxProgress in (Ci.koINotificationProgress.PROGRESS_INDETERMINATE,
                                                                                Ci.koINotificationProgress.PROGRESS_NOT_APPLICABLE) or
                                                           v <= self.maxProgress))

class KoNotificationText(KoNotificationBase):
    """Mixin to implement koINotificationText"""
    def __init__(self): pass
    details = _createProperty("_details", None)

class KoNotificationStatus(KoNotificationBase):
    """Mixin to implement koIStatusMessage"""
    def __init__(self):
        # Category becomes the first tag from constructor, or null.
        self.category = self.tags and self.tags[0] or None
        self.timeout = 0
        self.highlight = 0
        self.expiresAt = 0
        self.interactive = 0
        self._log = True

    msg = _createProperty("_summary", None)
    log = _createProperty("_log", None)
