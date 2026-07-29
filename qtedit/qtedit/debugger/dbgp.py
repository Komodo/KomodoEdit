"""PHP debugging via the real DBGP protocol (what Xdebug speaks) -- the
second protocol adapter alongside session.py's bespoke JSON protocol for
Python. Unlike the Python case, there's a real external interop partner
here (Xdebug) that qtedit doesn't control, so this wire format is not
invented -- it was captured empirically against a real `php`+Xdebug 3.5.0
process (see the plan doc's PHP-Debugger phase) rather than reconstructed
from memory, and every command/response shape below is exactly what that
probe observed, not a guess:

- Framing is asymmetric: responses/the init packet (Xdebug -> IDE) are
  "<decimal-length>\\0<xml>\\0"; commands (IDE -> Xdebug) are plain text
  "command -i <transaction_id> -flag value ...\\0" with NO length prefix.
- Every command gets exactly one response, correlated by transaction_id --
  there is no separate asynchronous event channel the way session.py's
  protocol has one. The "stopped at a line" information rides inside the
  response to whatever run/step command caused it
  (status="break" + a nested <xdebug:message filename=".." lineno=".."/>),
  but that response does NOT include the full call stack -- a follow-up
  stack_get command is needed for that, which is why _on_run_or_step_response
  below chains into a stack_get before finally emitting `stopped`.
- All paths are file:// URIs, not raw paths.

DbgpSession exposes the exact same signal/method surface as
session.DebugSession (stopped/localsReceived/output/terminated,
start/continue_/step_over/step_into/step_out/stop/get_locals) so
main_window.py's existing debug UI wiring works unmodified for either
language -- only the choice of which class to instantiate differs.
"""
import base64
import os
import xml.etree.ElementTree as ET

from PySide6.QtCore import QObject, QProcess, Signal
from PySide6.QtNetwork import QHostAddress, QTcpServer

DBGP_NS = "urn:debugger_protocol_v1"
XDEBUG_NS = "https://xdebug.org/dbgp/xdebug"


def _to_file_uri(path):
    return f"file://{os.path.abspath(path)}"


def _from_file_uri(uri):
    return uri[len("file://") :] if uri.startswith("file://") else uri


class DbgpBuffer:
    """Incremental reassembler for DBGP's "<decimal-length>\\0<xml>\\0"
    framing (the Xdebug -> IDE direction only -- outgoing commands aren't
    framed this way, see module docstring)."""

    def __init__(self):
        self._buf = b""

    def feed(self, data):
        self._buf += bytes(data)
        messages = []
        while True:
            msg = self._try_extract()
            if msg is None:
                break
            messages.append(msg)
        return messages

    def _try_extract(self):
        if b"\x00" not in self._buf:
            return None
        length_part, rest = self._buf.split(b"\x00", 1)
        try:
            length = int(length_part)
        except ValueError:
            # Corrupt stream -- drop the bad length field and keep going
            # rather than wedging the parser forever on one bad byte run.
            self._buf = rest
            return None
        if len(rest) < length + 1:  # +1 for the trailing \0 after the XML
            return None
        xml_bytes = rest[:length]
        self._buf = rest[length + 1 :]
        return xml_bytes.decode("utf-8", errors="replace")


class DbgpSession(QObject):
    stopped = Signal(str, list)  # reason, stack (list of dicts)
    localsReceived = Signal(int, list)  # frame_index, variables
    watchResult = Signal(str, str, bool)  # expr, display text, is_error
    localError = Signal(str)  # message, from a failed set_local
    output = Signal(str, bool)  # text, is_stderr
    terminated = Signal(int)  # exit_code

    DEFAULT_PORT = 9003

    def __init__(self, parent=None):
        super().__init__(parent)
        self._proc = None
        self._socket = None
        self._buffer = DbgpBuffer()
        self._next_transaction_id = 1
        self._pending = {}  # transaction_id -> callback(root_element)
        self._pending_breakpoints = []
        self._script_uri = None
        self._got_init = False

        self._server = QTcpServer(self)
        # An OS-assigned ephemeral port, not DEFAULT_PORT (Xdebug's own
        # documented default) -- start() below always tells the php
        # subprocess exactly which port to connect back to via
        # -dxdebug.client_port, so nothing here actually depends on binding
        # the well-known port, and using an ephemeral one instead is what
        # lets multiple DbgpSession instances (multiple simultaneous PHP
        # debug sessions) coexist. DEFAULT_PORT would only matter for a
        # remote-attach flow where an externally launched Xdebug process
        # connects using its own default ini setting without us telling it
        # the port -- qtedit doesn't have that feature (see the plan doc's
        # Debugger phase for why it's evaluated and deferred rather than
        # built), so there's no reason to reserve the fixed port here.
        self._server.listen(QHostAddress.LocalHost, 0)
        self._server.newConnection.connect(self._on_new_connection)

    def is_running(self):
        return self._proc is not None and self._proc.state() != QProcess.ProcessState.NotRunning

    def start(self, script_path, breakpoints):
        """`breakpoints` is a list of dicts: {"line": int, "condition":
        str|None, "ignore_count": int} -- same shape session.DebugSession
        takes, so main_window.py doesn't need per-language branching here
        either."""
        if self.is_running():
            return
        self._script_uri = _to_file_uri(script_path)
        self._pending_breakpoints = list(breakpoints)
        self._got_init = False

        self._proc = QProcess(self)
        self._proc.setProgram("php")
        self._proc.setArguments(
            [
                "-dxdebug.mode=debug",
                "-dxdebug.start_with_request=yes",
                f"-dxdebug.client_port={self._server.serverPort()}",
                "-dxdebug.client_host=127.0.0.1",
                script_path,
            ]
        )
        self._proc.setWorkingDirectory(os.path.dirname(script_path))
        self._proc.readyReadStandardOutput.connect(self._on_stdout)
        self._proc.readyReadStandardError.connect(self._on_stderr)
        self._proc.finished.connect(self._on_process_finished)
        self._proc.start()

    def continue_(self):
        self._send_run_like("continue", "run")

    def step_over(self):
        self._send_run_like("step", "step_over")

    def step_into(self):
        self._send_run_like("step", "step_into")

    def step_out(self):
        self._send_run_like("step", "step_out")

    def get_locals(self, frame_index):
        self._send("context_get", {"d": frame_index}, self._on_context_get_response, frame_index)

    def evaluate(self, expr, frame_index=0):
        # `frame_index` is accepted for API symmetry with
        # session.DebugSession, but Xdebug's `eval` command ignores DBGP's
        # `-d` depth flag and always evaluates in the innermost frame
        # (empirically verified against a real php+Xdebug process -- see
        # the plan doc's Debugger phase), so watch expressions on the PHP
        # side only ever reflect the current (topmost) frame regardless of
        # which stack frame is selected in the UI.
        self._send("eval", {}, self._on_eval_response, expr, data=expr)

    def set_local(self, frame_index, name, value_expr):
        # property_set's data is evaluated as PHP code, same as eval's --
        # verified empirically against real Xdebug (see the plan doc's
        # Debugger phase), so a plain expression string works here exactly
        # like it does for watch expressions. `name` must be the
        # property's DBGP "fullname" (e.g. "$x", with the sigil) -- the
        # same string context_get already reports and localsReceived
        # forwards on to main_window.py, so no translation is needed at
        # the call site. `-l` (byte length of the raw expression, not the
        # base64-encoded form) is required or Xdebug rejects the command.
        value_bytes = value_expr.encode("utf-8")
        self._send(
            "property_set",
            {"n": name, "d": frame_index, "l": len(value_bytes)},
            lambda root: self._on_property_set_response(root, frame_index),
            data=value_expr,
        )

    def stop(self):
        self._send("stop", {}, None)
        if self._proc is not None:
            self._proc.kill()

    def _send_run_like(self, reason, command):
        self._send(command, {}, lambda root: self._on_run_or_step_response(root, reason))

    def _send(self, command, flags, callback, *callback_extra_args, data=None):
        # `data`, if given, is a str sent as a base64-encoded "-- <data>"
        # trailer (DBGP's way of passing an arbitrary expression, e.g. a
        # breakpoint condition) -- the transaction id must come *before*
        # "--", not after, or Xdebug rejects the whole command with "invalid
        # or missing options" (empirically verified against a real
        # php+Xdebug process; see the plan doc's Debugger phase).
        if self._socket is None:
            return
        tid = self._next_transaction_id
        self._next_transaction_id += 1
        if callback is not None:
            self._pending[tid] = (callback, callback_extra_args)
        parts = [command, "-i", str(tid)]
        for flag, value in flags.items():
            parts += [f"-{flag}", str(value)]
        text = " ".join(parts)
        if data is not None:
            text += " -- " + base64.b64encode(data.encode("utf-8")).decode("ascii")
        self._socket.write((text + "\x00").encode("utf-8"))

    def _on_new_connection(self):
        self._socket = self._server.nextPendingConnection()
        self._socket.readyRead.connect(self._on_socket_ready_read)

    def _on_socket_ready_read(self):
        for xml_text in self._buffer.feed(self._socket.readAll()):
            try:
                root = ET.fromstring(xml_text)
            except ET.ParseError:
                continue
            self._handle_message(root)

    def _handle_message(self, root):
        if not self._got_init:
            self._got_init = True
            self._on_init()
            return
        tid_text = root.get("transaction_id")
        if tid_text is None:
            return
        entry = self._pending.pop(int(tid_text), None)
        if entry is None:
            return
        callback, extra_args = entry
        callback(root, *extra_args)

    def _on_init(self):
        self._send_next_breakpoint()

    def _send_next_breakpoint(self):
        if not self._pending_breakpoints:
            self._send_run_like("breakpoint", "run")
            return
        bp = self._pending_breakpoints.pop(0)
        condition = bp.get("condition") or None
        ignore_count = bp.get("ignore_count") or 0
        flags = {"f": self._script_uri, "n": bp["line"]}
        # bdb's set_break(cond=...) semantics (skip the first `ignore`
        # hits, stop starting on hit ignore+1 -- see tracee.py) are what
        # qtedit's ignore_count field means everywhere else; DBGP's own
        # hit_value/hit_condition instead means "stop once hit_count
        # satisfies the comparison", so hit_value = ignore_count + 1 with
        # ">=" reproduces the same "skip N, then always break" behavior
        # (verified empirically against real Xdebug -- see the plan doc's
        # Debugger phase).
        if ignore_count:
            flags["h"] = ignore_count + 1
            flags["o"] = ">="
        if condition:
            flags["t"] = "conditional"
            data = condition
        else:
            flags["t"] = "line"
            data = None
        self._send(
            "breakpoint_set",
            flags,
            lambda _root: self._send_next_breakpoint(),
            data=data,
        )

    def _on_run_or_step_response(self, root, reason):
        status = root.get("status")
        if status == "break":
            self._send("stack_get", {}, lambda stack_root: self._emit_stopped(stack_root, reason))
        elif status in ("stopping", "stopped"):
            # Empirically verified: Xdebug does not let the script actually
            # finish running after reporting "stopping" until it receives
            # an explicit stop command (a probe that just closed the
            # socket at this point also worked, but sending `stop` is the
            # documented, clean way to do it without dropping the
            # connection out from under any still-buffering stdout/stderr).
            # `terminated` itself is still emitted from QProcess.finished
            # (see _on_process_finished), not here -- same reasoning as
            # session.py's DebugSession: guarantees any already-buffered
            # stdout/stderr has been delivered to Qt first.
            self._send("stop", {}, None)

    def _emit_stopped(self, stack_root, reason):
        entries = []
        for elem in stack_root.findall(f"{{{DBGP_NS}}}stack"):
            entries.append(
                {
                    "function": elem.get("where", ""),
                    "filename": _from_file_uri(elem.get("filename", "")),
                    "line": int(elem.get("lineno", "0")),
                }
            )
        self.stopped.emit(reason, entries)

    def _on_context_get_response(self, root, frame_index):
        variables = []
        for prop in root.findall(f"{{{DBGP_NS}}}property"):
            name = prop.get("name", "")
            var_type = prop.get("type", "")
            text = prop.text or ""
            if prop.get("encoding") == "base64":
                try:
                    text = base64.b64decode(text).decode("utf-8", errors="replace")
                except Exception:
                    pass
            variables.append({"name": name, "type": var_type, "value": text})
        self.localsReceived.emit(frame_index, variables)

    def _on_eval_response(self, root, expr):
        error_elem = root.find(f"{{{DBGP_NS}}}error")
        if error_elem is not None:
            message_elem = error_elem.find(f"{{{DBGP_NS}}}message")
            message = (message_elem.text or "").strip() if message_elem is not None else "eval error"
            self.watchResult.emit(expr, f"<error: {message}>", True)
            return
        prop = root.find(f"{{{DBGP_NS}}}property")
        if prop is None:
            self.watchResult.emit(expr, "", False)
            return
        text = prop.text or ""
        if prop.get("encoding") == "base64":
            try:
                text = base64.b64decode(text).decode("utf-8", errors="replace")
            except Exception:
                pass
        self.watchResult.emit(expr, text, False)

    def _on_property_set_response(self, root, frame_index):
        if root.get("success") == "1":
            self.get_locals(frame_index)
        else:
            self.localError.emit(
                "Konnte Wert nicht setzen (ungültiger Ausdruck oder nicht änderbare Property)"
            )

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
        self._buffer = DbgpBuffer()
        self._pending = {}
        self._server.close()
        self.terminated.emit(exit_code)
