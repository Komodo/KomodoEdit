#!python
# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

# Status bar message data. (see statusbar.js for details)

from xpcom import components, nsError, COMException
import sys, os, time


class KoStatusMessage:
    _com_interfaces_ = [components.interfaces.koIStatusMessage]
    _reg_clsid_ = "{605ce7cb-a712-4b80-b3fb-49004cc14298}"
    _reg_contractid_ = "@activestate.com/koStatusMessage;1"
    _reg_desc_ = "Komodo Status Message"

    def __init__(self):
        self.category = None
        self.msg = None
        self.timeout = 0
        self.highlight = 0
        self.expiresAt = 0
        self.interactive = 0


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

