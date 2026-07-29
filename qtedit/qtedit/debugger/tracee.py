"""Debuggee-side process: runs a target Python script under `bdb.Bdb`
(stdlib's own trace engine, the same one `pdb` is built on) and speaks
qtedit's own JSON debug protocol (protocol.py) back to session.py over a
TCP loopback connection.

There is no legacy Komodo debugger code anywhere in this repo to port --
searched exhaustively (koIDebugger*/koDBGP*/DBGP, see the plan doc's
Debugger phase) and found only three dangling references to a feature that
apparently never shipped in Komodo Edit (it may have existed in the
commercial Komodo IDE, but nothing survives here). This is a from-scratch
build. `user_line`/`user_return` below follow the same basic
stop-and-wait-for-a-command shape stdlib `pdb.Pdb` uses (see
pdb.py's `user_line`/`user_return`/`interaction`), just driven by socket
messages instead of a console command loop.

The target script's own stdout/stderr are left completely alone -- only
the debug *control* messages go over the TCP socket, so QProcess on the
session.py side can capture real program output normally, the same way it
already does for Toolbox command execution.
"""
import bdb
import os
import socket
import sys
import traceback

from qtedit.debugger import protocol


def _safe_repr(value):
    try:
        text = repr(value)
    except Exception as exc:
        return f"<repr() failed: {exc}>"
    return text if len(text) <= 500 else text[:500] + "..."


class Tracee(bdb.Bdb):
    def __init__(self, sock):
        super().__init__()
        self._sock = sock
        self._frames = []  # list[(frame, lineno)], innermost first
        self._entry_seen = False

    def do_clear(self, arg):
        # Only relevant for temporary breakpoints, which qtedit doesn't
        # set (set_break's temporary=False default) -- implemented anyway
        # since Bdb.break_here() requires the method to exist.
        self.clear_bpbynumber(arg)

    def user_line(self, frame):
        # bdb.Bdb.reset() leaves stopframe=None, which makes stop_here()
        # return True unconditionally -- so the very first traced line
        # always triggers user_line before any real code has run (the
        # same reason `python -m pdb script.py` always stops at line 1
        # before you type anything). qtedit has no "break on entry"
        # feature for v1: skip straight past this one *unless* it happens
        # to coincide with a real breakpoint, so "Start Debugging" reads
        # as "run until the first breakpoint", not "always stop at line 1".
        if not self._entry_seen:
            self._entry_seen = True
            if not self.break_here(frame):
                self.set_continue()
                return
        reason = "breakpoint" if self.break_here(frame) else "step"
        self._interact(frame, reason)

    def user_return(self, frame, _return_value):
        # Fires for the *returning* frame itself, at its return statement
        # -- not yet back in the caller (matches pdb's "--Return--", which
        # shows the same frame one last time before it actually pops).
        # One more step/continue from here lands in the caller.
        self._interact(frame, "return")

    def _interact(self, frame, reason):
        stack, _ = self.get_stack(frame, None)
        # get_stack() walks all the way to self.botframe, which is
        # Bdb.run()'s own `exec(cmd, globals, locals)` frame inside bdb.py
        # itself -- not useful to show the user, filtered out here rather
        # than in every display-facing caller.
        self._frames = [
            (f, lineno) for f, lineno in reversed(stack) if f.f_code.co_filename != bdb.__file__
        ]
        self._send_stopped(reason)
        while True:
            msg = protocol.recv_message(self._sock)
            if msg is None:
                self.set_quit()
                return
            cmd = msg.get("cmd")
            if cmd == "continue":
                self.set_continue()
                return
            if cmd == "step_over":
                self.set_next(frame)
                return
            if cmd == "step_into":
                self.set_step()
                return
            if cmd == "step_out":
                self.set_return(frame)
                return
            if cmd == "stop":
                self.set_quit()
                return
            if cmd == "get_locals":
                self._send_locals(msg.get("frame_index", 0))
                continue
            if cmd == "set_breakpoints":
                self._apply_breakpoints(msg)
                continue
            if cmd == "eval":
                self._send_eval_result(msg.get("expr", ""), msg.get("frame_index", 0))
                continue
            if cmd == "set_local":
                self._set_local(
                    msg.get("frame_index", 0), msg.get("name", ""), msg.get("value_expr", "")
                )
                continue
            # Unknown command -- ignore and keep waiting rather than
            # silently resuming execution the user didn't ask for.

    def _apply_breakpoints(self, msg):
        self.clear_all_breaks()
        path = msg.get("path")
        for bp in msg.get("breakpoints", []):
            line = bp["line"]
            condition = bp.get("condition") or None
            self.set_break(path, line, cond=condition)
            ignore_count = bp.get("ignore_count") or 0
            if ignore_count:
                # set_break() creates the Breakpoint via bdb.Breakpoint's
                # own registry -- get_breaks() looks it back up rather than
                # set_break() returning it directly. Bdb.break_here()'s own
                # stop-checking logic already auto-decrements .ignore and
                # skips the stop while it's > 0, so no custom hit-counting
                # is needed beyond setting this field.
                for bpt in self.get_breaks(path, line):
                    bpt.ignore = ignore_count
        protocol.send_message(self._sock, {"event": "breakpoints_set"})

    def _send_stopped(self, reason):
        entries = [
            {
                "function": frame.f_code.co_name,
                "filename": frame.f_code.co_filename,
                "line": lineno,
            }
            for frame, lineno in self._frames
        ]
        protocol.send_message(self._sock, {"event": "stopped", "reason": reason, "stack": entries})

    def _send_eval_result(self, expr, frame_index):
        # Unlike DBGP's `eval` (see dbgp.py's module docstring -- Xdebug
        # ignores the `-d` depth flag for eval, always evaluating in the
        # innermost frame), bdb gives us the real frame object per index
        # via self._frames, so watch expressions on the Python side can
        # genuinely evaluate in whichever stack frame the user has
        # selected.
        if 0 <= frame_index < len(self._frames):
            frame, _lineno = self._frames[frame_index]
            try:
                value = eval(expr, frame.f_globals, frame.f_locals)
            except Exception as exc:
                protocol.send_message(
                    self._sock,
                    {
                        "event": "watch_result",
                        "expr": expr,
                        "value": None,
                        "error": f"{type(exc).__name__}: {exc}",
                    },
                )
                return
            protocol.send_message(
                self._sock,
                {"event": "watch_result", "expr": expr, "value": _safe_repr(value), "error": None},
            )
        else:
            protocol.send_message(
                self._sock,
                {"event": "watch_result", "expr": expr, "value": None, "error": "no such frame"},
            )

    def _set_local(self, frame_index, name, value_expr):
        # Assigning into frame.f_locals[name] here actually writes back to
        # the real fast-local variable (not just a disconnected snapshot
        # dict), including inside a live function frame -- verified
        # empirically against this project's Python 3.14 interpreter,
        # which implements PEP 667's write-through f_locals proxy for
        # optimized frames (this would need a ctypes
        # PyFrame_LocalsToFast() workaround on pre-3.13 interpreters).
        if not (0 <= frame_index < len(self._frames)):
            protocol.send_message(
                self._sock, {"event": "set_local_error", "message": "no such frame"}
            )
            return
        frame, _lineno = self._frames[frame_index]
        try:
            value = eval(value_expr, frame.f_globals, frame.f_locals)
            frame.f_locals[name] = value
        except Exception as exc:
            protocol.send_message(
                self._sock,
                {"event": "set_local_error", "message": f"{type(exc).__name__}: {exc}"},
            )
            return
        self._send_locals(frame_index)

    def _send_locals(self, frame_index):
        if 0 <= frame_index < len(self._frames):
            frame, _lineno = self._frames[frame_index]
            variables = [
                {"name": name, "type": type(value).__name__, "value": _safe_repr(value)}
                for name, value in frame.f_locals.items()
            ]
        else:
            variables = []
        protocol.send_message(
            self._sock, {"event": "locals", "frame_index": frame_index, "variables": variables}
        )


def main():
    port = int(os.environ["QTEDIT_DEBUG_PORT"])
    script_path = os.path.abspath(sys.argv[1])
    sock = socket.create_connection(("127.0.0.1", port))
    tracee = Tracee(sock)

    protocol.send_message(sock, {"event": "ready"})
    # Handshake before the target script runs at all -- breakpoints must
    # be set before bdb.run() starts tracing, so this loop only handles
    # set_breakpoints/start/stop, not the full step/continue command set
    # (those only make sense once a frame is actually stopped).
    while True:
        msg = protocol.recv_message(sock)
        if msg is None:
            sock.close()
            return
        cmd = msg.get("cmd")
        if cmd == "set_breakpoints":
            tracee._apply_breakpoints(msg)
        elif cmd == "start":
            break
        elif cmd == "stop":
            sock.close()
            return

    with open(script_path, "r", encoding="utf-8") as f:
        source = f.read()
    code = compile(source, script_path, "exec")
    globs = {"__name__": "__main__", "__file__": script_path}

    exit_code = 0
    try:
        tracee.run(code, globs, globs)
    except SystemExit as exc:
        exit_code = exc.code if isinstance(exc.code, int) else (1 if exc.code else 0)
    except BaseException:
        traceback.print_exc()
        exit_code = 1
    finally:
        protocol.send_message(sock, {"event": "terminated", "exit_code": exit_code})
        sock.close()


if __name__ == "__main__":
    main()
