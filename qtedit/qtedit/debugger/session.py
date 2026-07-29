"""Qt side of the debugger: launches the target script under tracee.py as
a QProcess and drives qtedit's own JSON debug protocol (protocol.py) over
a local TCP loopback connection -- the IDE listens (QTcpServer on an
OS-assigned port), the debuggee connects in and speaks first ("ready").
See tracee.py's module docstring for why this is a bespoke protocol
instead of real DBGP (no legacy Komodo debugger code exists to be
compatible with, and nothing here needs to interoperate with Xdebug).
"""
import os
import sys

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, Signal
from PySide6.QtNetwork import QHostAddress, QTcpServer

import qtedit
from qtedit.debugger import protocol

QTEDIT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(qtedit.__file__)))


class DebugSession(QObject):
    stopped = Signal(str, list)  # reason, stack (list of dicts)
    localsReceived = Signal(int, list)  # frame_index, variables
    watchResult = Signal(str, str, bool)  # expr, display text, is_error
    localError = Signal(str)  # message, from a failed set_local
    output = Signal(str, bool)  # text, is_stderr
    terminated = Signal(int)  # exit_code

    def __init__(self, parent=None):
        super().__init__(parent)
        self._proc = None
        self._socket = None
        self._buffer = protocol.MessageBuffer()
        self._pending_start = None  # (script_path, breakpoints) until "ready"
        self._debuggee_exit_code = None

        self._server = QTcpServer(self)
        self._server.listen(QHostAddress.LocalHost, 0)
        self._server.newConnection.connect(self._on_new_connection)

    def is_running(self):
        return self._proc is not None and self._proc.state() != QProcess.ProcessState.NotRunning

    def start(self, script_path, breakpoints):
        """`breakpoints` is a list of dicts: {"line": int, "condition":
        str|None, "ignore_count": int} (0-based line numbers, matching
        editor.py's CodeEditor.breakpoints)."""
        if self.is_running():
            return
        self._pending_start = (script_path, list(breakpoints))

        env = QProcessEnvironment.systemEnvironment()
        env.insert("QTEDIT_DEBUG_PORT", str(self._server.serverPort()))
        existing_path = env.value("PYTHONPATH")
        env.insert(
            "PYTHONPATH",
            QTEDIT_ROOT if not existing_path else os.pathsep.join([QTEDIT_ROOT, existing_path]),
        )

        self._proc = QProcess(self)
        self._proc.setProcessEnvironment(env)
        self._proc.setWorkingDirectory(os.path.dirname(script_path))
        self._proc.setProgram(sys.executable)
        self._proc.setArguments(["-m", "qtedit.debugger.tracee", script_path])
        self._proc.readyReadStandardOutput.connect(self._on_stdout)
        self._proc.readyReadStandardError.connect(self._on_stderr)
        self._proc.finished.connect(self._on_process_finished)
        self._proc.start()

    def continue_(self):
        self._send({"cmd": "continue"})

    def step_over(self):
        self._send({"cmd": "step_over"})

    def step_into(self):
        self._send({"cmd": "step_into"})

    def step_out(self):
        self._send({"cmd": "step_out"})

    def get_locals(self, frame_index):
        self._send({"cmd": "get_locals", "frame_index": frame_index})

    def evaluate(self, expr, frame_index=0):
        self._send({"cmd": "eval", "expr": expr, "frame_index": frame_index})

    def set_local(self, frame_index, name, value_expr):
        self._send(
            {"cmd": "set_local", "frame_index": frame_index, "name": name, "value_expr": value_expr}
        )

    def stop(self):
        self._send({"cmd": "stop"})
        if self._proc is not None:
            self._proc.kill()

    def _send(self, obj):
        if self._socket is not None:
            self._socket.write(protocol.encode_message(obj))

    def _on_new_connection(self):
        self._socket = self._server.nextPendingConnection()
        self._socket.readyRead.connect(self._on_socket_ready_read)

    def _on_socket_ready_read(self):
        for msg in self._buffer.feed(bytes(self._socket.readAll())):
            self._handle_message(msg)

    def _handle_message(self, msg):
        event = msg.get("event")
        if event == "ready":
            script_path, breakpoints = self._pending_start
            self._send(
                {"cmd": "set_breakpoints", "path": script_path, "breakpoints": breakpoints}
            )
            self._send({"cmd": "start"})
        elif event == "stopped":
            self.stopped.emit(msg.get("reason", ""), msg.get("stack", []))
        elif event == "locals":
            self.localsReceived.emit(msg.get("frame_index", 0), msg.get("variables", []))
        elif event == "watch_result":
            error = msg.get("error")
            text = f"<error: {error}>" if error else msg.get("value", "")
            self.watchResult.emit(msg.get("expr", ""), text, error is not None)
        elif event == "set_local_error":
            self.localError.emit(msg.get("message", ""))
        elif event == "terminated":
            # Recorded, not emitted here: QProcess.finished() is guaranteed
            # to fire only after all buffered stdout/stderr has already
            # been delivered via readyReadStandardOutput/Error, while this
            # JSON message can race ahead of that on its own separate
            # socket -- emitting `terminated` from here could reach
            # main_window.py before the last bit of debuggee program
            # output has shown up in the Output dock.
            self._debuggee_exit_code = msg.get("exit_code", 0)

    def _on_stdout(self):
        if self._proc is not None:
            text = bytes(self._proc.readAllStandardOutput()).decode("utf-8", errors="replace")
            self.output.emit(text, False)

    def _on_stderr(self):
        if self._proc is not None:
            text = bytes(self._proc.readAllStandardError()).decode("utf-8", errors="replace")
            self.output.emit(text, True)

    def _on_process_finished(self, exit_code, _exit_status):
        self._socket = None
        self._buffer = protocol.MessageBuffer()
        reported = self._debuggee_exit_code if self._debuggee_exit_code is not None else exit_code
        self._debuggee_exit_code = None
        self.terminated.emit(reported)
