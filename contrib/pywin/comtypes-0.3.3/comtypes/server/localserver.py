from ctypes import *
import comtypes
from comtypes.hresult import *
from comtypes.server import IClassFactory
import logging
import Queue

logger = logging.getLogger(__name__)
_debug = logger.debug
_critical = logger.critical

REGCLS_SINGLEUSE = 0       # class object only generates one instance
REGCLS_MULTIPLEUSE = 1     # same class object genereates multiple inst.
REGCLS_MULTI_SEPARATE = 2  # multiple use, but separate control over each
REGCLS_SUSPENDED      = 4  # register it as suspended, will be activated
REGCLS_SURROGATE      = 8  # must be used when a surrogate process

def run(classes):
    assert len(classes) == 1
    cls = classes[0]
    factory = ClassFactory(cls)
    factory._run()

g_cLocks = 0 # XXX We should use Interlocked access

class ClassFactory(comtypes.COMObject):
    _com_interfaces_ = [IClassFactory]
    _locks = 0
    _queue = None
    regcls = REGCLS_MULTIPLEUSE

    def __init__(self, cls, *args, **kw):
        super(ClassFactory, self).__init__()
        cls._factory = self
        self._cls = cls
        self._register_class()
        self._args = args
        self._kw = kw

    def _register_class(self):
        regcls = getattr(self._cls, "_regcls_", self.regcls)
        cookie = c_ulong()
        ptr = self._com_pointers_[comtypes.IUnknown._iid_]
        oledll.ole32.CoRegisterClassObject(byref(comtypes.GUID(self._cls._reg_clsid_)),
                                           ptr,
                                           self._cls._reg_clsctx_,
                                           regcls,
                                           byref(cookie))
        self.cookie = cookie

    def _revoke_class(self):
        oledll.ole32.CoRevokeClassObject(self,cookie)

    def CreateInstance(self, this, punkOuter, riid, ppv):
        _debug("ClassFactory.CreateInstance(%s)", riid[0])
        self.LockServer(None, True)
        obj = self._cls(*self._args, **self._kw)
        result = obj.IUnknown_QueryInterface(None, riid, ppv)
        _debug("CreateInstance() -> %s", result)
        return result

    def LockServer(self, this, fLock):
        global g_cLocks
        if fLock:
            g_cLocks += 1
        else:
            g_cLocks -= 1
        _debug("LockServer -> %d", g_cLocks)
        if g_cLocks == 0:
            if self._queue is not None:
                self._queue.put(42)
            else:
                windll.user32.PostQuitMessage(0)
        return S_OK

    def _run(self):
        result = windll.ole32.CoInitialize(None)
        if RPC_E_CHANGED_MODE == result:
            # we're running in MTA: no message pump needed
            _debug("Server running in MTA")
            self.run_mta()
        else:
            # we're running in STA: need a message pump
            _debug("Server running in STA")
            if result >= 0:
                # we need a matching CoUninitialize() call for a successful CoInitialize().
                windll.ole32.CoUninitialize()
            self.run_sta()

    def run_sta(self):
        "Can be overridden in subclasses, to install a custom message pump."
        pump_messages()

    def run_mta(self):
        "Can be overridden in subclasses."
        self._queue = Queue.Queue()
        self._queue.get()

def pump_messages():
    from ctypes.wintypes import MSG
    user32 = windll.user32
    msg = MSG()
    while 1:
        res = user32.GetMessageA(byref(msg), None, 0, 0)
        if res == -1:
            raise WinError()
        if res:
            user32.TranslateMessage(byref(msg))
            user32.DispatchMessageA(byref(msg))
        else:
            return
