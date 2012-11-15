import sys
from xpcom import components
import logging

log = logging.getLogger("koWindowManagerUtils")
log.setLevel(logging.DEBUG)

Ci = components.interfaces
Cc = components.classes

class koWindowManagerUtils(object):
    _com_interfaces_ = [Ci.koIWindowManagerUtils]
    _reg_clsid_ = "{5ae9f3a2-5343-450b-99d6-193946f80eeb}"
    _reg_contractid_ = "@activestate.com/koIWindowManagerUtils;1"
    _reg_desc_ = "Komodo Window Manager Utilities"

    if sys.platform.startswith("win"):
        def setOnTop(self, xulWin, relativeXulWin, onTop):
            if onTop:
                xulWin.zLevel = Ci.nsIXULWindow.raisedZ
            else:
                xulWin.zLevel = Ci.nsIXULWindow.normalZ

    elif sys.platform == "darwin":
        def __init__(self):
            self._ctypes = None
            self._objc = None
            self._appkit = None
            self._coregraphics = None

        @property
        def ctypes(self):
            if self._ctypes is None:
                import ctypes
                import ctypes.util
                self._ctypes = ctypes
            return self._ctypes

        @property
        def objc(self):
            if self._objc is None:
                ctypes = self.ctypes
                objc = self._objc = ctypes.CDLL(self.ctypes.util.find_library('objc'))
                # Need to declare the functions we use, otherwise we crash on x86_64
                objc.objc_getClass.restype = ctypes.c_void_p
                objc.objc_msgSend.restype = ctypes.c_void_p
                objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
                objc.sel_registerName.restype = ctypes.c_void_p
            return self._objc

        @property
        def appkit(self):
            if self._appkit is None:
                self._appkit = self.ctypes.CDLL(self.ctypes.util.find_library('AppKit'))
            return self._appkit

        @property
        def coregraphics(self):
            if self._coregraphics is None:
                self._coregraphics = self.ctypes.CDLL(self.ctypes.util.find_library('CoreGraphics'))
            return self._coregraphics

        def setOnTop(self, xulWin, relativeXulWin, onTop):
            objc = self.objc

            def getTopLevel(xulWin):
                """ Given a nsIXULWindow, return the NSWindow*
                    corresponding to the toplevel window of its nsIBaseWindow
                """
                requestor = xulWin.docShell.QueryInterface(Ci.nsIInterfaceRequestor)
                view = requestor.getInterface(Ci.nsIBaseWindow).parentNativeWindow
                return objc.objc_msgSend(view, objc.sel_registerName('window'))

            # pool = [[NSAutoReleasePool alloc] init];
            NSAutoreleasePool = objc.objc_getClass('NSAutoreleasePool')
            pool = objc.objc_msgSend(NSAutoreleasePool, objc.sel_registerName('alloc'))
            pool = objc.objc_msgSend(pool, objc.sel_registerName('init'))
            try:
                if onTop:
                    levelKey = 5 # kCGFloatingWindowLevelKey
                else:
                    levelKey = 4 # kCGNormalWindowLevelKey
                self.coregraphics.CGWindowLevelForKey.restype = self.ctypes.c_int32
                level = self.coregraphics.CGWindowLevelForKey(levelKey)
                win = getTopLevel(xulWin)
                objc.objc_msgSend(win, objc.sel_registerName('setLevel:'), level)
            finally:
                # [pool release];
                objc.objc_msgSend(pool, objc.sel_registerName('release'))

    else:
        def __init__(self):
            self._ctypes = None
            self._gdk = None

        @property
        def ctypes(self):
            if self._ctypes is None:
                import ctypes
                import ctypes.util
                self._ctypes = ctypes
            return self._ctypes

        @property
        def gdk(self):
            if self._gdk is None:
                self._gdk = self.ctypes.CDLL(self.ctypes.util.find_library("gdk-x11-2.0"))
            return self._gdk

        def setOnTop(self, window, relativeWindow, onTop):

            def getTopLevel(xulWin):
                """ Given a nsIXULWindow, return the GDKWindow*
                    corresponding to the toplevel window of its nsIBaseWindow
                """
                requestor = xulWin.docShell.QueryInterface(Ci.nsIInterfaceRequestor)
                child = requestor.getInterface(Ci.nsIBaseWindow).parentNativeWindow
                self.gdk.gdk_window_get_effective_toplevel.argtypes = [
                    self.ctypes.c_void_p]
                self.gdk.gdk_window_get_effective_toplevel.restype = self.ctypes.c_void_p
                return self.gdk.gdk_window_get_effective_toplevel(child)

            gdkWin = getTopLevel(window)
            if relativeWindow:
                if onTop:
                    gdkRel = getTopLevel(relativeWindow)
                else:
                    # we want to undo the pinnning; grab the root window and
                    # use that as the transient parent instead.
                    self.gdk.gdk_get_default_root_window.restype = self.ctypes.c_void_p
                    gdkRel = self.gdk.gdk_get_default_root_window()
                self.gdk.gdk_window_set_transient_for.argtypes = [
                    self.ctypes.c_void_p, self.ctypes.c_void_p]
                self.gdk.gdk_window_set_transient_for(gdkWin, gdkRel)
                return

            # no relative window, make this on top of all windows (across
            # applications)
            self.gdk.gdk_window_set_keep_above.argtypes = [
                self.ctypes.c_void_p, self.ctypes.c_bool]
            self.gdk.gdk_window_set_keep_above(gdkWin, onTop)
