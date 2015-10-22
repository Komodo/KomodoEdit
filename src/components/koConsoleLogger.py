#!/usr/bin/env python
# Copyright (c) 2013 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

"""koErrorLogger - logging for the (JS) Error console"""

from xpcom import components, COMException, ServerException, nsError
from xpcom.components import classes as Cc, interfaces as Ci
from argparse import Namespace
import logging

try:
    from zope.cachedescriptors.property import Lazy as LazyProperty
except ImportError:
    LazyProperty = property

class KoConsoleLogger:
    """ This logs things from the error console and dumps them into the Python
    logging facilities."""
    _com_interfaces_ = [Ci.nsIConsoleListener,
                        Ci.nsIObserver]
    _reg_clsid_ = "{6c3f4619-ae3c-4e8e-9139-7a9679552fd5}"
    _reg_contractid_ = "@activestate.com/KoConsoleLogger;1"
    _reg_desc_ = "JS Error Console Logger"
    _reg_categories_ = [
        ("xpcom-startup", "@activestate.com/KoConsoleLogger;1")
    ]

    def __init__(self):
        (Cc["@mozilla.org/consoleservice;1"]
           .getService(Ci.nsIConsoleService)
           .registerListener(self))

    @LazyProperty
    def log(self):
        return logging.getLogger("console-logger")

    def _handleException(self, exc):
        try:
            exc.QueryInterface(Ci.nsIException)
        except COMException:
            return False
        def make_frame(frame):
            if not frame:
                return None
            f = Namespace(f_code=Namespace(co_filename=frame.filename,
                                           co_name=frame.name),
                          f_globals=None)
            return Namespace(tb_frame=f,
                             tb_lineno=frame.lineNumber,
                             tb_next=make_frame(frame.caller))
        self.log.error("%s", exc.message, make_frame(exc.location))
        return True

    ignored_error_strings = [
        # Can't do much about external libraries.
        "analytics.com/ga.js",
        "/analytics_debug.js",
        "/socketio.js",
        "/jquery.js",
        "chrome://komodo/content/contrib/less.js",
        # Returns an empty XML node - nothing to be concerned about.
        "addons.updates: Update manifest had an unrecognised namespace",
        # Preferences xpath queries result in this message - nothing we can do about that.
        'Use of getAttributeNodeNS() is deprecated.',
        # SVG icons:
        'Error: path does not exist:',
        # XPCOMUtils and Services being a global constant:
        'TypeError: "XPCOMUtils" is read-only',
        'TypeError: "Services" is read-only',
        'SyntaxError: test for equality (==) mistyped as assignment',
        'Key event not available on some keyboard layouts: key="u" modifiers="control,alt"',
        'ReferenceError: reference to undefined property this._nm',
        'Bootstrapped manifest not allowed to use',
        'ReferenceError: reference to undefined property this.treeBoxObject.columns',
        'SyntaxError: applying the \'delete\' operator to an unqualified name is deprecated (5) in resource://gre/modules/DownloadUtils.jsm',
        'No valid manifest directive',
        'JavaScript strict warning: chrome://komodo/content/contrib/less.js',
        'JavaScript strict warning: http://www.google-analytics.com/analytics_debug.js',
        'JavaScript strict warning: chrome://global/content/bindings/tree.xml',
        'JavaScript strict warning: resource://gre/modules/notifications.js',
        'SyntaxError: test for equality (==) mistyped as assignment (=)?',
        'SyntaxError: in strict mode code, functions may be declared only at top level or immediately within another function',
        'JavaScript strict warning: , line 0: TypeError: "XPCOMUtils" is read-only',
        'JavaScript strict warning: , line 0: TypeError: "Services" is read-only',
        'Unexpected value  parsing y1 attribute',
        'Unexpected value  parsing y2 attribute',
        'Unexpected value  parsing x1 attribute',
        'Unexpected value  parsing x2 attribute'
    ]
    def _handleScriptError(self, error):
        try:
            error.QueryInterface(Ci.nsIScriptError)
        except COMException:
            return False

        errorMessage = error.errorMessage or ""
        sourceName = error.sourceName or ""
        if any(x in errorMessage or x in sourceName for x in self.ignored_error_strings):
            return True

        exc_info = None
        if error.flags & Ci.nsIScriptError.warningFlag:
            log = self.log.warn
        else:
            log = self.log.error
            frame = Namespace(f_code=Namespace(co_filename=sourceName,
                                               co_name=""),
                              f_globals=None)
            tb = Namespace(tb_frame=frame,
                           tb_lineno=error.lineNumber,
                           tb_next=None)
            exc_info = ("", None, tb)
        log("%s (%x) in %s:%r", errorMessage, error.flags, sourceName,
            error.lineNumber, exc_info=exc_info)
        return True

    def observe(self, message, *args):
        if len(args) > 0:
            return # Just tells us that the component has been initialized
        if self._handleException(message):
            return
        if self._handleScriptError(message):
            return

        messagetext = message.message
        if any(x in messagetext for x in self.ignored_error_strings):
            self.log.debug("FILTERED: %s", messagetext)
        else:
            self.log.info("%s", messagetext)
