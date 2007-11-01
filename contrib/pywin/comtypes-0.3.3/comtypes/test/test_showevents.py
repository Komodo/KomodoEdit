import sys
import unittest
import comtypes.client
import cStringIO
import ctypes

class EventsTest(unittest.TestCase):
    def setUp(self):
        self.old_stdout = sys.stdout
        sys.stdout = cStringIO.StringIO()

    def tearDown(self):
        sys.stdout = self.old_stdout

    def pump_messages_with_timeout(self, timeout):
        # The following code waits for 'timeout' milliseconds in the
        # way required for COM, internally doing the correct things
        # depending on the COM appartment of the current thread.
        timeout = 1000
        # We have to supply at least one NULL handle, otherwise
        # CoWaitForMultipleHandles complains.
        handles = (ctypes.c_void_p * 1)()
        RPC_S_CALLPENDING = -2147417835
        try:
            ctypes.oledll.ole32.CoWaitForMultipleHandles(0,
                                                         timeout,
                                                         len(handles), handles,
                                                         ctypes.byref(ctypes.c_ulong()))
        except WindowsError, details:
            if details[0] != RPC_S_CALLPENDING: # timeout expired
                raise

    def pump_messages_with_timeout(self, timeout):
        # Running a message loop with a timeout should work for all
        # possible COM apartment types; however it is *required* for
        # single threaded appartments.
        from comtypes.server.localserver import pump_messages
        def post_quit_message(hwnd, msg, idEvent, dwTime):
            ctypes.windll.user32.PostQuitMessage(0)
            ctypes.windll.user32.KillTimer(hwnd, idEvent)
            return 0
        TIMERPROC = ctypes.WINFUNCTYPE(None,
                                       ctypes.c_void_p, ctypes.c_uint,
                                       ctypes.c_uint, ctypes.c_ulong)
        proc = TIMERPROC(post_quit_message)
        ctypes.windll.user32.SetTimer.argtypes = (ctypes.c_void_p, ctypes.c_uint,
                                                  ctypes.c_uint, TIMERPROC)
        ctypes.windll.user32.SetTimer(0, 42, timeout,
                                      TIMERPROC(post_quit_message))
        pump_messages()

    def test(self):
        # Start IE, call .Quit(), and check if the
        # DWebBrowserEvents2_OnQuit event has fired.  We do this by
        # calling ShowEvents() and capturing sys.stdout.
        o = comtypes.client.CreateObject("InternetExplorer.Application")
        conn = comtypes.client.ShowEvents(o)
        o.Quit()
        del o

        self.pump_messages_with_timeout(1000)

        stream = sys.stdout
        stream.flush()
        sys.stdout = self.old_stdout
        output = stream.getvalue().splitlines()

        self.failUnless('# event found: DWebBrowserEvents2_OnMenuBar' in output)
        self.failUnless('Event DWebBrowserEvents2_OnQuit(None)' in output)

if __name__ == "__main__":
    unittest.main()
