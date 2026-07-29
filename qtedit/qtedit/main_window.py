import os

from PySide6.QtCore import QDir, QPoint, QProcess, QStandardPaths, Qt
from PySide6.QtGui import QAction, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDockWidget,
    QFileDialog,
    QFileSystemModel,
    QHBoxLayout,
    QInputDialog,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QToolBar,
    QTreeView,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from qtedit import icons
from qtedit.codeintel_client import CodeIntelClient
from qtedit.completion_popup import CompletionPopup
from qtedit.debugger import breakpoint_store
from qtedit.debugger.breakpoint_dialog import BreakpointConditionDialog
from qtedit.debugger.dbgp import DbgpSession
from qtedit.debugger.session import DebugSession
from qtedit.editor import UDL_LANGUAGES, CodeEditor
from qtedit.find_bar import FindBar
from qtedit import find_in_files
from qtedit.find_in_files_dialog import FindInFilesDialog
from qtedit.prefs_dialog import PreferencesDialog
from qtedit.projects import model as project_model
from qtedit.projects.tree_model import IS_FILE_ROLE, NODE_ROLE, build_project_model
from qtedit import session
from qtedit import vcs
from qtedit.vcs_dock import VCSPanel
from qtedit.toolbox import model as toolbox_model
from qtedit.toolbox.item_dialog import ToolboxItemDialog
from qtedit.toolbox.tree_model import (
    FOLDER_PATH_ROLE,
    TOOLBOX_ITEM_ROLE,
    build_toolbox_model,
)

KOMODO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# The real Komodo app icons, already sitting in the repo from a prior build
# rather than duplicated into qtedit/ -- the same "reuse prior build
# artifacts" pattern used for the codeintel3/stdlibs/*.cix catalogs.
APP_ICON_PATH = os.path.join(KOMODO_ROOT, "build", "release", "main", "komodo128.edit.png")


class MainWindow(QMainWindow):
    def __init__(self, project_dir=None):
        super().__init__()
        self.setWindowTitle("KomodoEdit (Qt MVP)")
        self.resize(1100, 700)
        if os.path.isfile(APP_ICON_PATH):
            self.setWindowIcon(QIcon(APP_ICON_PATH))

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self._close_tab)
        self.tabs.currentChanged.connect(self._on_current_tab_changed)

        self._find_bar = FindBar(self)
        self._find_bar.hide()
        self._find_bar.closed.connect(self._return_focus_to_editor)

        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        central_layout.addWidget(self.tabs)
        central_layout.addWidget(self._find_bar)
        self.setCentralWidget(central)

        find_shortcut = QShortcut(QKeySequence.Find, self)
        find_shortcut.activated.connect(self.open_find_bar)

        self._prefs_dialog = None
        self._find_in_files_dialog = None
        self._last_replace_undo = []
        self._running_processes = []
        self._build_menu()
        self._build_project_tree(project_dir or os.getcwd())
        self._build_toolbox()
        self._build_find_results()
        self._build_vcs()
        self._build_debugger()
        self._build_codeintel()

        self.new_file()

    def _build_menu(self):
        file_menu = self.menuBar().addMenu("&File")

        self._new_action = QAction(icons.icon("file-plus2"), "&New", self)
        self._new_action.setShortcut(QKeySequence.New)
        self._new_action.triggered.connect(self.new_file)
        file_menu.addAction(self._new_action)

        self._open_action = QAction(icons.icon("folder-open"), "&Open...", self)
        self._open_action.setShortcut(QKeySequence.Open)
        self._open_action.triggered.connect(self.open_file_dialog)
        file_menu.addAction(self._open_action)

        self._save_action = QAction(icons.icon("save"), "&Save", self)
        self._save_action.setShortcut(QKeySequence.Save)
        self._save_action.triggered.connect(self.save_current)
        file_menu.addAction(self._save_action)

        save_as_action = QAction(icons.icon("save"), "Save &As...", self)
        save_as_action.setShortcut(QKeySequence.SaveAs)
        save_as_action.triggered.connect(self.save_current_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        close_action = QAction(icons.icon("close"), "&Close Tab", self)
        close_action.setShortcut(QKeySequence.Close)
        close_action.triggered.connect(lambda: self._close_tab(self.tabs.currentIndex()))
        file_menu.addAction(close_action)

        file_menu.addSeparator()

        new_project_action = QAction(icons.icon("archive"), "New &Project...", self)
        new_project_action.triggered.connect(self.new_project)
        file_menu.addAction(new_project_action)

        open_project_action = QAction(icons.icon("folder2"), "Open P&roject...", self)
        open_project_action.triggered.connect(self.open_project)
        file_menu.addAction(open_project_action)

        self._close_project_action = QAction(icons.icon("close"), "Close Project", self)
        self._close_project_action.setEnabled(False)
        self._close_project_action.triggered.connect(self.close_project)
        file_menu.addAction(self._close_project_action)

        edit_menu = self.menuBar().addMenu("&Edit")

        self._find_in_files_action = QAction(icons.icon("search"), "Find in &Files...", self)
        self._find_in_files_action.setShortcut(QKeySequence("Ctrl+Shift+F"))
        self._find_in_files_action.triggered.connect(self.open_find_in_files)
        edit_menu.addAction(self._find_in_files_action)

        self._undo_replace_action = QAction("&Undo Last Replace All", self)
        self._undo_replace_action.setEnabled(False)
        self._undo_replace_action.triggered.connect(self.undo_last_find_replace)
        edit_menu.addAction(self._undo_replace_action)

        set_language_action = QAction("Set &Language...", self)
        set_language_action.triggered.connect(self.open_set_language)
        edit_menu.addAction(set_language_action)

        edit_menu.addSeparator()

        prefs_action = QAction(icons.icon("cog"), "&Preferences...", self)
        prefs_action.setShortcut(QKeySequence.Preferences)
        prefs_action.triggered.connect(self.open_preferences)
        edit_menu.addAction(prefs_action)

        debug_menu = self.menuBar().addMenu("&Debug")

        self._start_debug_action = QAction("&Start Debugging", self)
        self._start_debug_action.setShortcut(QKeySequence("F5"))
        self._start_debug_action.triggered.connect(self.start_debugging)
        debug_menu.addAction(self._start_debug_action)

        toggle_bp_action = QAction("Toggle &Breakpoint", self)
        toggle_bp_action.setShortcut(QKeySequence("F9"))
        toggle_bp_action.triggered.connect(self.toggle_breakpoint)
        debug_menu.addAction(toggle_bp_action)

        edit_bp_condition_action = QAction("Edit Breakpoint &Condition...", self)
        edit_bp_condition_action.triggered.connect(self.edit_breakpoint_condition)
        debug_menu.addAction(edit_bp_condition_action)

        debug_menu.addSeparator()

        self._continue_action = QAction("&Continue", self)
        self._continue_action.setShortcut(QKeySequence("F6"))
        self._continue_action.setEnabled(False)
        self._continue_action.triggered.connect(self._debug_continue)
        debug_menu.addAction(self._continue_action)

        self._step_over_action = QAction("Step &Over", self)
        self._step_over_action.setShortcut(QKeySequence("F10"))
        self._step_over_action.setEnabled(False)
        self._step_over_action.triggered.connect(self._debug_step_over)
        debug_menu.addAction(self._step_over_action)

        self._step_into_action = QAction("Step &Into", self)
        self._step_into_action.setShortcut(QKeySequence("F11"))
        self._step_into_action.setEnabled(False)
        self._step_into_action.triggered.connect(self._debug_step_into)
        debug_menu.addAction(self._step_into_action)

        self._step_out_action = QAction("Step Ou&t", self)
        self._step_out_action.setShortcut(QKeySequence("Shift+F11"))
        self._step_out_action.setEnabled(False)
        self._step_out_action.triggered.connect(self._debug_step_out)
        debug_menu.addAction(self._step_out_action)

        self._stop_debug_action = QAction("S&top", self)
        self._stop_debug_action.setShortcut(QKeySequence("Shift+F5"))
        self._stop_debug_action.setEnabled(False)
        self._stop_debug_action.triggered.connect(self._debug_stop)
        debug_menu.addAction(self._stop_debug_action)

        self._build_toolbar()

    def _build_toolbar(self):
        toolbar = QToolBar("Main", self)
        toolbar.setObjectName("mainToolBar")
        toolbar.addAction(self._new_action)
        toolbar.addAction(self._open_action)
        toolbar.addAction(self._save_action)
        toolbar.addSeparator()
        toolbar.addAction(self._find_in_files_action)
        self.addToolBar(toolbar)

    def open_preferences(self):
        if self._prefs_dialog is None:
            self._prefs_dialog = PreferencesDialog(self)
        self._prefs_dialog.show()
        self._prefs_dialog.raise_()
        self._prefs_dialog.activateWindow()

    def open_set_language(self):
        """Manually pick a UDL language for the current tab -- the only way
        to reach the handful of UDL languages (Django, AngularJS, TracWiki,
        JSERB, Komodo_Snippet) that have no safe, unambiguous file
        extension of their own (see UDL_EXTENSIONS' docstring in
        editor.py), and a convenience override for everything else too."""
        editor = self.tabs.currentWidget()
        if editor is None:
            return
        name, ok = QInputDialog.getItem(
            self, "Set Language", "Language:", UDL_LANGUAGES, 0, False
        )
        if ok and name:
            editor.set_lexer_by_name(name)

    def _on_current_tab_changed(self, _index):
        self._find_bar.set_editor(self.tabs.currentWidget())

    def open_find_bar(self):
        self._find_bar.set_editor(self.tabs.currentWidget())
        self._find_bar.show_bar()

    def _return_focus_to_editor(self):
        editor = self.tabs.currentWidget()
        if editor is not None:
            # ScintillaEdit.setFocus(bool) shadows QWidget.setFocus(); see
            # the same note in _insert_completion.
            QWidget.setFocus(editor)

    def _build_find_results(self):
        self._all_find_hits = []  # unfiltered, so the filter box can re-apply without re-searching

        self._results_filter_edit = QLineEdit()
        self._results_filter_edit.setPlaceholderText("Filter results...")
        self._results_filter_edit.textChanged.connect(self._apply_find_results_filter)

        self._results_view = QTreeWidget()
        self._results_view.setHeaderLabels(["File", "Line", "Text"])
        self._results_view.itemDoubleClicked.connect(self._on_find_result_double_clicked)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._results_filter_edit)
        layout.addWidget(self._results_view)

        dock = QDockWidget("Find Results", self)
        dock.setWidget(container)
        self.addDockWidget(Qt.BottomDockWidgetArea, dock)

    def _build_vcs(self):
        self._vcs_panel = None
        self._vcs_dock = QDockWidget("Git", self)
        self._vcs_dock.setVisible(False)
        self.addDockWidget(Qt.LeftDockWidgetArea, self._vcs_dock)

        self._diff_view = QPlainTextEdit()
        self._diff_view.setReadOnly(True)
        font = self._diff_view.font()
        font.setFamily("monospace")
        self._diff_view.setFont(font)
        self._diff_dock = QDockWidget("Diff", self)
        self._diff_dock.setWidget(self._diff_view)
        self._diff_dock.setVisible(False)
        self.addDockWidget(Qt.BottomDockWidgetArea, self._diff_dock)

    def _refresh_vcs(self):
        if self._project is not None and vcs.is_git_repo(self._project.base_dir):
            if self._vcs_panel is None or self._vcs_panel.base_dir != self._project.base_dir:
                self._vcs_panel = VCSPanel(self._project.base_dir, self)
                self._vcs_panel.diff_requested.connect(self._show_diff)
                self._vcs_dock.setWidget(self._vcs_panel)
            else:
                self._vcs_panel.refresh()
            self._vcs_dock.setVisible(True)
        else:
            self._vcs_dock.setVisible(False)
            self._diff_dock.setVisible(False)

    def _show_diff(self, path, staged):
        diff_text = vcs.git_diff(self._project.base_dir, path, staged=staged)
        self._diff_view.setPlainText(diff_text or "(no changes)")
        self._diff_dock.setWindowTitle(f"Diff: {path}")
        self._diff_dock.setVisible(True)
        self._diff_dock.raise_()

    def _build_debugger(self):
        # Multiple simultaneous debug sessions: keyed by script path, since
        # only one session per file makes sense (matches start_debugging's
        # own "already running for this file" guard). Only the "active"
        # session's stack/locals/watch panels are shown at a time --
        # switching the combo box changes which one; a background session
        # keeps running and auto-activates itself the next time it stops
        # (see _on_debug_stopped), same as most IDEs bring a breakpoint hit
        # to the foreground.
        self._debug_sessions = {}  # path -> DebugSession|DbgpSession
        self._active_debug_path = None
        self._debug_current_editors = {}  # path -> editor showing that session's execution-line marker

        self._debug_session_combo = QComboBox()
        self._debug_session_combo.currentIndexChanged.connect(self._on_debug_session_switched)

        self._stack_view = QTreeWidget()
        self._stack_view.setHeaderLabels(["Function", "Line"])
        self._stack_view.itemClicked.connect(self._on_stack_item_clicked)

        self._locals_view = QTreeWidget()
        self._locals_view.setHeaderLabels(["Name", "Type", "Value"])
        self._debug_locals_frame_index = 0
        self._locals_view.itemChanged.connect(self._on_locals_item_changed)

        self._watch_view = QTreeWidget()
        self._watch_view.setHeaderLabels(["Expression", "Value"])
        self._watch_expressions = []  # list[str], in display order

        self._watch_add_edit = QLineEdit()
        self._watch_add_edit.setPlaceholderText("Add watch expression...")
        self._watch_add_edit.returnPressed.connect(self._on_add_watch)
        remove_watch_btn = QPushButton("Remove")
        remove_watch_btn.clicked.connect(self._on_remove_watch)
        watch_add_row = QHBoxLayout()
        watch_add_row.addWidget(self._watch_add_edit, 1)
        watch_add_row.addWidget(remove_watch_btn)

        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._debug_session_combo)
        layout.addWidget(self._stack_view, 1)
        layout.addWidget(self._locals_view, 1)
        layout.addLayout(watch_add_row)
        layout.addWidget(self._watch_view, 1)

        self._debug_dock = QDockWidget("Debug", self)
        self._debug_dock.setWidget(panel)
        self._debug_dock.setVisible(False)
        self.addDockWidget(Qt.LeftDockWidgetArea, self._debug_dock)

    def toggle_breakpoint(self):
        editor = self.tabs.currentWidget()
        if editor is None:
            return
        editor.toggle_breakpoint(editor.lineFromPosition(editor.currentPos()))

    def _save_breakpoints_for(self, editor):
        if not editor.filepath:
            return
        abspath = os.path.abspath(editor.filepath)
        breakpoints = [
            {
                "line": line,
                "condition": editor.breakpoint_conditions.get(line),
                "ignore_count": editor.breakpoint_ignore_counts.get(line, 0),
            }
            for line in sorted(editor.breakpoints)
        ]
        breakpoint_store.save_breakpoints(self._breakpoints_path, abspath, breakpoints)

    def edit_breakpoint_condition(self):
        editor = self.tabs.currentWidget()
        if editor is None:
            return
        line = editor.lineFromPosition(editor.currentPos())
        dialog = BreakpointConditionDialog(
            condition=editor.breakpoint_conditions.get(line, ""),
            ignore_count=editor.breakpoint_ignore_counts.get(line, 0),
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            editor.set_breakpoint_condition(line, dialog.condition(), dialog.ignore_count())

    def start_debugging(self):
        editor = self.tabs.currentWidget()
        path = editor.filepath if editor is not None else None
        session_cls = None
        if path is not None:
            if path.endswith(".py"):
                session_cls = DebugSession
            elif path.endswith(".php"):
                session_cls = DbgpSession
        if session_cls is None:
            self.statusBar().showMessage(
                "Start Debugging benötigt eine gespeicherte .py- oder .php-Datei im aktiven Tab",
                4000,
            )
            return
        existing = self._debug_sessions.get(path)
        if existing is not None and existing.is_running():
            self.statusBar().showMessage("Für diese Datei läuft bereits eine Debug-Sitzung", 3000)
            return

        sess = session_cls(self)
        self._debug_sessions[path] = sess
        self._connect_session_signals(path, sess)

        self._debug_session_combo.blockSignals(True)
        self._debug_session_combo.addItem(os.path.basename(path), path)
        self._debug_session_combo.setCurrentIndex(self._debug_session_combo.count() - 1)
        self._debug_session_combo.blockSignals(False)
        self._active_debug_path = path
        self._stack_view.clear()
        self._locals_view.clear()

        # bdb (Python) and DBGP (PHP) both use 1-based line numbers;
        # Scintilla's own line indices (editor.breakpoints) are 0-based.
        breakpoints = [
            {
                "line": line + 1,
                "condition": editor.breakpoint_conditions.get(line),
                "ignore_count": editor.breakpoint_ignore_counts.get(line, 0),
            }
            for line in sorted(editor.breakpoints)
        ]
        sess.start(path, breakpoints)

        self._set_debug_actions_running(True)
        self._debug_dock.setVisible(True)

    def _connect_session_signals(self, path, sess):
        # Every handler below is path-tagged (via the `p=path` default-arg
        # trick, since PySide6 signals don't carry any sender identity on
        # their own) so a background session's events don't clobber the
        # currently active session's panels -- only `stopped` is allowed to
        # change which session is active (see _on_debug_stopped).
        sess.stopped.connect(lambda reason, stack, p=path: self._on_debug_stopped(p, reason, stack))
        sess.localsReceived.connect(
            lambda frame_index, variables, p=path: self._on_debug_locals(p, frame_index, variables)
        )
        sess.watchResult.connect(
            lambda expr, text, is_error, p=path: self._on_watch_result(p, expr, text, is_error)
        )
        sess.localError.connect(lambda message, p=path: self._on_debug_local_error(p, message))
        sess.output.connect(lambda text, is_stderr, p=path: self._on_debug_output(p, text, is_stderr))
        sess.terminated.connect(lambda exit_code, p=path: self._on_debug_terminated(p, exit_code))

    def _current_session(self):
        return self._debug_sessions.get(self._active_debug_path)

    def _on_debug_session_switched(self, index):
        self._active_debug_path = self._debug_session_combo.itemData(index) if index >= 0 else None
        # v1 doesn't cache each session's last-known stack/locals across a
        # switch -- panels go blank until that session's own next `stopped`
        # (or a manual stack-item click) repopulates them.
        self._stack_view.clear()
        self._locals_view.blockSignals(True)
        self._locals_view.clear()
        self._locals_view.blockSignals(False)
        for i in range(self._watch_view.topLevelItemCount()):
            self._watch_view.topLevelItem(i).setText(1, "")

    def _set_debug_actions_running(self, running):
        self._start_debug_action.setEnabled(True)  # starting a session for a *different* file is fine
        self._continue_action.setEnabled(running)
        self._step_over_action.setEnabled(running)
        self._step_into_action.setEnabled(running)
        self._step_out_action.setEnabled(running)
        self._stop_debug_action.setEnabled(running)

    def _debug_continue(self):
        session = self._current_session()
        if session is not None:
            session.continue_()

    def _debug_step_over(self):
        session = self._current_session()
        if session is not None:
            session.step_over()

    def _debug_step_into(self):
        session = self._current_session()
        if session is not None:
            session.step_into()

    def _debug_step_out(self):
        session = self._current_session()
        if session is not None:
            session.step_out()

    def _debug_stop(self):
        session = self._current_session()
        if session is not None:
            session.stop()

    def _on_debug_stopped(self, path, _reason, stack):
        if self._active_debug_path != path:
            # Bring a background session's breakpoint hit to the front,
            # same as most IDEs -- without re-triggering
            # _on_debug_session_switched's panel-clearing (redundant, since
            # this method repopulates them immediately below anyway).
            idx = self._debug_session_combo.findData(path)
            if idx != -1:
                self._debug_session_combo.blockSignals(True)
                self._debug_session_combo.setCurrentIndex(idx)
                self._debug_session_combo.blockSignals(False)
            self._active_debug_path = path

        self._stack_view.clear()
        for entry in stack:
            self._stack_view.addTopLevelItem(
                QTreeWidgetItem([entry["function"], str(entry["line"])])
            )
        old_editor = self._debug_current_editors.get(path)
        if old_editor is not None:
            old_editor.clear_current_line()
            del self._debug_current_editors[path]
        if stack:
            top = stack[0]
            self.open_file(top["filename"])
            editor = self.tabs.currentWidget()
            if editor is not None:
                editor.set_current_line(top["line"] - 1)  # bdb is 1-based
                self._debug_current_editors[path] = editor
            session = self._debug_sessions.get(path)
            if session is not None:
                session.get_locals(0)
                self._refresh_watches(0)

    def _on_stack_item_clicked(self, _item, _column):
        session = self._current_session()
        if session is not None:
            frame_index = self._stack_view.indexOfTopLevelItem(_item)
            session.get_locals(frame_index)
            self._refresh_watches(frame_index)

    def _on_debug_locals(self, path, frame_index, variables):
        if path != self._active_debug_path:
            return
        self._debug_locals_frame_index = frame_index
        # blockSignals so repopulating the tree doesn't re-trigger
        # itemChanged (and thus a spurious set_local() round-trip) for
        # every row -- only a real user edit should do that.
        self._locals_view.blockSignals(True)
        self._locals_view.clear()
        for var in variables:
            item = QTreeWidgetItem([var["name"], var["type"], var["value"]])
            # Editable as a whole (Qt has no clean per-column editable
            # flag for QTreeWidgetItem) -- _on_locals_item_changed ignores
            # edits to columns other than Value, so an accidental edit to
            # Name/Type is a harmless no-op that a subsequent refresh
            # overwrites.
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            self._locals_view.addTopLevelItem(item)
        self._locals_view.blockSignals(False)

    def _on_locals_item_changed(self, item, column):
        session = self._current_session()
        if column != 2 or session is None:
            return
        name = item.text(0)
        value_expr = item.text(2)
        session.set_local(self._debug_locals_frame_index, name, value_expr)

    def _on_debug_local_error(self, path, message):
        if path != self._active_debug_path:
            return
        self.statusBar().showMessage(message, 5000)

    def _on_add_watch(self):
        expr = self._watch_add_edit.text().strip()
        if not expr or expr in self._watch_expressions:
            self._watch_add_edit.clear()
            return
        self._watch_add_edit.clear()
        self._watch_expressions.append(expr)
        self._watch_view.addTopLevelItem(QTreeWidgetItem([expr, ""]))
        session = self._current_session()
        if session is not None and session.is_running():
            session.evaluate(expr, 0)

    def _on_remove_watch(self):
        item = self._watch_view.currentItem()
        if item is None:
            return
        expr = item.text(0)
        if expr in self._watch_expressions:
            self._watch_expressions.remove(expr)
        self._watch_view.takeTopLevelItem(self._watch_view.indexOfTopLevelItem(item))

    def _refresh_watches(self, frame_index):
        session = self._current_session()
        if session is None:
            return
        for expr in self._watch_expressions:
            session.evaluate(expr, frame_index)

    def _on_watch_result(self, path, expr, text, _is_error):
        if path != self._active_debug_path:
            return
        for i in range(self._watch_view.topLevelItemCount()):
            item = self._watch_view.topLevelItem(i)
            if item.text(0) == expr:
                item.setText(1, text)

    def _on_debug_output(self, path, text, _is_stderr):
        stripped = text.rstrip("\n")
        if not stripped:
            return
        # Prefix with the originating script only when more than one
        # session is (or, at the moment this fires, was still) running --
        # keeps the common single-session case's output uncluttered.
        if len(self._debug_sessions) > 1:
            stripped = f"[{os.path.basename(path)}] {stripped}"
        self._output_view.appendPlainText(stripped)

    def _on_debug_terminated(self, path, exit_code):
        editor = self._debug_current_editors.pop(path, None)
        if editor is not None:
            editor.clear_current_line()
        self._debug_sessions.pop(path, None)
        idx = self._debug_session_combo.findData(path)
        if idx != -1:
            # If `path` was the active selection, removeItem's own
            # currentIndexChanged fires _on_debug_session_switched, which
            # clears the panels (or repopulates the combo box's newly
            # current session's -- empty -- panel state); if it wasn't
            # active, nothing else needs to happen here.
            self._debug_session_combo.removeItem(idx)
        self._set_debug_actions_running(bool(self._debug_sessions))
        self.statusBar().showMessage(
            f"{os.path.basename(path)}: Debuggee exited with code {exit_code}", 5000
        )

    def _default_search_dir(self):
        if self._project is not None:
            return self._project.base_dir
        return self._project_root_path

    def open_find_in_files(self):
        # Recreated every time rather than cached: the open-files list and
        # project scope can change between invocations (tabs opened/closed,
        # project opened/closed), and this dialog is cheap to build.
        open_files = [
            self.tabs.widget(i).filepath
            for i in range(self.tabs.count())
            if self.tabs.widget(i).filepath
        ]
        project_base_dir = self._project.base_dir if self._project is not None else None
        self._find_in_files_dialog = FindInFilesDialog(
            self._default_search_dir(),
            self,
            open_files=open_files,
            project_base_dir=project_base_dir,
        )
        self._find_in_files_dialog.hits_found.connect(self._on_find_in_files_hits)
        self._find_in_files_dialog.replacements_applied.connect(
            self._on_find_in_files_replaced
        )
        self._find_in_files_dialog.show()
        self._find_in_files_dialog.raise_()
        self._find_in_files_dialog.activateWindow()

    def _on_find_in_files_replaced(self, undo_record):
        self._last_replace_undo = undo_record
        self._undo_replace_action.setEnabled(bool(undo_record))

    def undo_last_find_replace(self):
        if not self._last_replace_undo:
            return
        find_in_files.undo_replacements(self._last_replace_undo)
        # Reload any of the restored files that happen to be open so the
        # editor doesn't keep showing the (now reverted) replaced text.
        restored_paths = {path for path, _ in self._last_replace_undo}
        for i in range(self.tabs.count()):
            editor = self.tabs.widget(i)
            if editor.filepath in restored_paths:
                try:
                    with open(editor.filepath, "r", encoding="utf-8", errors="replace") as f:
                        editor.setText(f.read())
                except OSError:
                    continue
        self.statusBar().showMessage(
            f"Reverted {len(self._last_replace_undo)} file(s)", 4000
        )
        self._last_replace_undo = []
        self._undo_replace_action.setEnabled(False)

    def _on_find_in_files_hits(self, hits):
        self._all_find_hits = hits
        self._results_filter_edit.clear()  # also triggers _apply_find_results_filter
        self.statusBar().showMessage(f"{len(hits)} match(es) found", 5000)

    def _apply_find_results_filter(self, text):
        self._results_view.clear()
        needle = text.strip().lower()
        base_dir = self._default_search_dir()
        for hit in self._all_find_hits:
            rel_path = os.path.relpath(hit.path, base_dir)
            if needle and needle not in rel_path.lower() and needle not in hit.line_text.lower():
                continue
            item = QTreeWidgetItem([rel_path, str(hit.line_no), hit.line_text.strip()])
            item.setData(0, Qt.ItemDataRole.UserRole, hit)
            self._results_view.addTopLevelItem(item)
        for column in range(3):
            self._results_view.resizeColumnToContents(column)

    def _on_find_result_double_clicked(self, item, _column):
        hit = item.data(0, Qt.ItemDataRole.UserRole)
        if hit is None:
            return
        self.open_file(hit.path)
        editor = self.tabs.currentWidget()
        if editor is None:
            return
        line = hit.line_no - 1
        start = editor.findColumn(line, hit.column)
        end = editor.findColumn(line, hit.column + (hit.match_end - hit.match_start))
        editor.setSel(start, end)
        editor.ensureVisible(line)
        editor.scrollCaret()
        QWidget.setFocus(editor)

    def _build_project_tree(self, root_path):
        self._project = None
        self._project_root_path = root_path
        self._fs_model = None
        self._project_tree = QTreeView()
        self._project_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._project_tree.customContextMenuRequested.connect(
            self._show_project_context_menu
        )
        # One connection for the tree's whole lifetime -- _on_tree_double_clicked
        # dispatches on self._project instead of us disconnecting/reconnecting
        # a different handler each time the dock switches between folder-
        # browser and project-tree mode.
        self._project_tree.doubleClicked.connect(self._on_tree_double_clicked)

        self._project_dock = QDockWidget("Project", self)
        self._project_dock.setWidget(self._project_tree)
        self.addDockWidget(Qt.LeftDockWidgetArea, self._project_dock)

        self._show_folder_browser(root_path)

    def _show_folder_browser(self, root_path):
        """No-project fallback: a plain live folder browser, same behavior
        this dock always had before Projects existed -- legacy Komodo can
        run without any project open too."""
        self._fs_model = QFileSystemModel(self)
        self._fs_model.setRootPath(root_path)
        self._fs_model.setFilter(QDir.AllEntries | QDir.NoDotAndDotDot)
        self._project_tree.setModel(self._fs_model)
        self._project_tree.setRootIndex(self._fs_model.index(root_path))
        for column in (1, 2, 3):
            self._project_tree.hideColumn(column)
        self._project_dock.setWindowTitle("Project")

    def _show_project_tree(self):
        self._fs_model = None
        self._project_tree.setModel(build_project_model(self._project, self._git_status_map()))
        self._project_dock.setWindowTitle(f"Project: {self._project.name}")

    def _git_status_map(self):
        if self._project is None or not vcs.is_git_repo(self._project.base_dir):
            return {}
        return {
            s.path: f"{s.index_code}{s.worktree_code}"
            for s in vcs.git_status(self._project.base_dir)
        }

    def _on_tree_double_clicked(self, index):
        if self._project is None:
            self._open_from_tree(self._fs_model, index)
            return
        if not index.data(IS_FILE_ROLE):
            return  # a folder/group row -- let the view's expand/collapse handle it
        node = index.data(NODE_ROLE)
        self.open_file(os.path.join(self._project.base_dir, node.url))

    def new_project(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "New Project", filter=f"Komodo Project (*{project_model.PROJECT_EXTENSION})"
        )
        if not path:
            return
        if not path.endswith(project_model.PROJECT_EXTENSION):
            path += project_model.PROJECT_EXTENSION
        name = os.path.splitext(os.path.basename(path))[0]
        self._project = project_model.create_project(path, name)
        self._close_project_action.setEnabled(True)
        self._show_project_tree()
        self._refresh_toolbox()
        self._refresh_vcs()
        self._restore_session()

    def open_project(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Project", filter=f"Komodo Project (*{project_model.PROJECT_EXTENSION})"
        )
        if not path:
            return
        try:
            self._project = project_model.load_project(path)
        except OSError as exc:
            QMessageBox.warning(self, "Open Project", f"Could not open {path}:\n{exc}")
            return
        self._close_project_action.setEnabled(True)
        self._show_project_tree()
        self._refresh_toolbox()
        self._refresh_vcs()
        self._restore_session()

    def close_project(self):
        if self._project is None:
            return
        self._save_session()
        self._project = None
        self._close_project_action.setEnabled(False)
        self._show_folder_browser(self._project_root_path)
        self._refresh_toolbox()
        self._refresh_vcs()

    def _show_project_context_menu(self, pos):
        menu = QMenu(self)
        if self._project is None:
            menu.addAction(icons.icon("archive"), "New Project...").triggered.connect(
                self.new_project
            )
            menu.addAction(icons.icon("folder2"), "Open Project...").triggered.connect(
                self.open_project
            )
            menu.exec(self._project_tree.viewport().mapToGlobal(pos))
            return

        index = self._project_tree.indexAt(pos)
        node = index.data(NODE_ROLE) if index.isValid() else None

        menu.addAction(icons.icon("file-plus2"), "Add File...").triggered.connect(
            self._add_file_to_project
        )
        menu.addAction(icons.icon("folder-plus"), "Add Folder...").triggered.connect(
            self._add_folder_to_project
        )
        menu.addAction(icons.icon("plus-square"), "New Group...").triggered.connect(
            self._add_group_to_project
        )
        if node is not None:
            menu.addSeparator()
            menu.addAction(
                icons.icon("minus-square"), "Remove from Project"
            ).triggered.connect(lambda: self._remove_project_node(node))
        menu.addSeparator()
        menu.addAction(icons.icon("close"), "Close Project").triggered.connect(
            self.close_project
        )
        menu.exec(self._project_tree.viewport().mapToGlobal(pos))

    def _add_file_to_project(self):
        path, _ = QFileDialog.getOpenFileName(self, "Add File to Project")
        if path:
            project_model.add_file(self._project, path)
            self._show_project_tree()

    def _add_folder_to_project(self):
        path = QFileDialog.getExistingDirectory(self, "Add Folder to Project")
        if path:
            project_model.import_folder_snapshot(self._project, path)
            self._show_project_tree()

    def _add_group_to_project(self):
        name, ok = QInputDialog.getText(self, "New Group", "Name:")
        if ok and name:
            project_model.add_group(self._project, name)
            self._show_project_tree()

    def _remove_project_node(self, node):
        project_model.remove_node(self._project, node)
        self._show_project_tree()

    def _build_toolbox(self):
        config_dir = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppConfigLocation
        )
        self._toolbox_root = os.path.join(config_dir, "toolbox")
        toolbox_model.ensure_default_toolbox(self._toolbox_root)
        self._session_path = os.path.join(config_dir, session.FILENAME)
        self._breakpoints_path = os.path.join(config_dir, breakpoint_store.FILENAME)

        self._toolbox_view = QTreeView()
        self._toolbox_view.setHeaderHidden(True)
        self._toolbox_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._toolbox_view.customContextMenuRequested.connect(
            self._show_toolbox_context_menu
        )
        self._toolbox_view.doubleClicked.connect(self._on_toolbox_double_clicked)
        self._refresh_toolbox()

        dock = QDockWidget("Toolbox", self)
        dock.setWidget(self._toolbox_view)
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)

        self._output_view = QPlainTextEdit()
        self._output_view.setReadOnly(True)
        output_dock = QDockWidget("Output", self)
        output_dock.setWidget(self._output_view)
        self.addDockWidget(Qt.BottomDockWidgetArea, output_dock)

    def _refresh_toolbox(self):
        project_toolbox_root = None
        if self._project is not None:
            project_toolbox_root = os.path.join(self._project.base_dir, ".komodotools")
            os.makedirs(project_toolbox_root, exist_ok=True)
        self._toolbox_view.setModel(
            build_toolbox_model(self._toolbox_root, project_toolbox_root)
        )

    def _on_toolbox_double_clicked(self, index):
        item = index.data(TOOLBOX_ITEM_ROLE)
        if item is None:
            return  # a folder row -- let the view's default expand/collapse handle it
        if item.type == toolbox_model.SNIPPET:
            self._insert_snippet(item)
        elif item.type == toolbox_model.COMMAND:
            self._run_toolbox_command(item)

    def _insert_snippet(self, item):
        editor = self.tabs.currentWidget()
        if editor is None:
            return
        pos = editor.currentPos()
        editor.insertText(pos, item.value)
        new_pos = pos + len(item.value.encode("utf-8"))
        editor.setSel(new_pos, new_pos)
        QWidget.setFocus(editor)

    def _run_toolbox_command(self, item):
        proc = QProcess(self)
        if item.cwd:
            proc.setWorkingDirectory(item.cwd)
        proc.finished.connect(
            lambda code, _status, proc=proc, item=item: self._on_command_finished(
                proc, item, code
            )
        )
        self._output_view.appendPlainText(f"$ {item.value}")
        self._running_processes.append(proc)
        proc.start("/bin/sh", ["-c", item.value])

    def _on_command_finished(self, proc, item, exit_code):
        output = bytes(proc.readAllStandardOutput()).decode("utf-8", errors="replace")
        errors = bytes(proc.readAllStandardError()).decode("utf-8", errors="replace")
        if output:
            self._output_view.appendPlainText(output.rstrip("\n"))
        if errors:
            self._output_view.appendPlainText(errors.rstrip("\n"))
        self._output_view.appendPlainText(f"[{item.name}] exited with code {exit_code}\n")
        self._running_processes.remove(proc)
        proc.deleteLater()

    def _show_toolbox_context_menu(self, pos):
        index = self._toolbox_view.indexAt(pos)
        if index.isValid():
            item = index.data(TOOLBOX_ITEM_ROLE)
            target_folder = index.data(FOLDER_PATH_ROLE)
            delete_path = item.path if item is not None else target_folder
        else:
            target_folder = self._toolbox_root
            delete_path = None

        menu = QMenu(self)
        menu.addAction(icons.svg_icon("snippet.svg"), "New Snippet...").triggered.connect(
            lambda: self._create_toolbox_item(target_folder, toolbox_model.SNIPPET)
        )
        menu.addAction(icons.svg_icon("command.svg"), "New Command...").triggered.connect(
            lambda: self._create_toolbox_item(target_folder, toolbox_model.COMMAND)
        )
        menu.addAction(icons.icon("folder-plus"), "New Folder...").triggered.connect(
            lambda: self._create_toolbox_folder(target_folder)
        )
        menu.addSeparator()
        edit_item = index.data(TOOLBOX_ITEM_ROLE) if index.isValid() else None
        edit_action = menu.addAction(icons.icon("pencil-square"), "Edit...")
        edit_action.setEnabled(edit_item is not None)
        edit_action.triggered.connect(lambda: self._edit_toolbox_item(edit_item))
        delete_action = menu.addAction(icons.icon("trash"), "Delete")
        delete_action.setEnabled(delete_path is not None)
        delete_action.triggered.connect(lambda: self._delete_toolbox_entry(delete_path))
        menu.addSeparator()
        menu.addAction(icons.icon("refresh"), "Refresh").triggered.connect(
            self._refresh_toolbox
        )
        menu.exec(self._toolbox_view.viewport().mapToGlobal(pos))

    def _create_toolbox_item(self, folder_path, item_type):
        dialog = ToolboxItemDialog(item_type, editing_name=True, parent=self)
        if dialog.exec() != ToolboxItemDialog.DialogCode.Accepted:
            return
        name = dialog.name()
        if not name:
            return
        toolbox_model.create_item(folder_path, name, item_type, dialog.value(), dialog.cwd())
        self._refresh_toolbox()

    def _edit_toolbox_item(self, item):
        # Matches legacy Komodo: snippets (and macros, not implemented here)
        # open in the main editor via a virtual URL scheme so the full
        # editor is available; commands stay on a small properties-style
        # dialog (legacy has no in-editor command-edit path at all, only
        # "Edit Properties").
        if item.type == toolbox_model.SNIPPET:
            self._open_snippet_editor(item)
            return
        dialog = ToolboxItemDialog(
            item.type,
            name=item.name,
            value=item.value,
            cwd=item.cwd,
            editing_name=False,
            parent=self,
        )
        if dialog.exec() != ToolboxItemDialog.DialogCode.Accepted:
            return
        toolbox_model.update_item(item.path, item.name, item.type, dialog.value(), dialog.cwd())
        self._refresh_toolbox()

    def _open_snippet_editor(self, item):
        for i in range(self.tabs.count()):
            editor = self.tabs.widget(i)
            existing = editor.toolbox_item
            if existing is not None and existing.path == item.path:
                self.tabs.setCurrentIndex(i)
                return

        editor = CodeEditor(self)
        editor.setText(item.value)
        editor.toolbox_item = item
        index = self.tabs.addTab(editor, f"Snippet: {item.name}")
        self.tabs.setTabToolTip(index, item.path)
        self.tabs.setCurrentIndex(index)

    def _create_toolbox_folder(self, parent_path):
        name, ok = QInputDialog.getText(self, "New Folder", "Name:")
        if ok and name:
            toolbox_model.create_folder(parent_path, name)
            self._refresh_toolbox()

    def _delete_toolbox_entry(self, path):
        reply = QMessageBox.question(
            self, "Delete", f"Delete {os.path.basename(path)}?"
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            toolbox_model.delete_path(path)
        except OSError as exc:
            QMessageBox.warning(self, "Delete", f"Could not delete {path}:\n{exc}")
            return
        self._refresh_toolbox()

    def _build_codeintel(self):
        # Drives the codeintel3 OOP engine (Python 3 port of codeintel2,
        # runs in-process-family via a plain subprocess of this same
        # interpreter) via the OOP protocol -- see codeintel_client.py.
        # Scoped to saved Python files only for this MVP.
        self.codeintel = CodeIntelClient(parent=self)
        self.codeintel.errorOccurred.connect(
            lambda msg: self.statusBar().showMessage(msg, 5000)
        )
        self.completion_popup = CompletionPopup(self)
        self.completion_popup.accepted.connect(self._insert_completion)
        self._pending_editor = None
        self._pending_pos = None

        shortcut = QShortcut(QKeySequence("Ctrl+Space"), self)
        shortcut.activated.connect(self.trigger_autocomplete)

    def trigger_autocomplete(self):
        editor = self.tabs.currentWidget()
        if editor is None:
            return
        path = editor.filepath
        if not path:
            self.statusBar().showMessage(
                "Autocomplete nur für gespeicherte Python-Dateien (Datei erst speichern)",
                4000,
            )
            return
        pos = editor.currentPos()
        text = editor.current_text()
        # The OOP round-trip is async and, on a cold codeintel3 cache (first
        # import-resolving request in a session -- has to scan site-packages
        # and parse the ~9MB stdlib catalog), can take several real seconds
        # with otherwise zero visual feedback. Show something immediately so
        # it doesn't look stuck, and snapshot the edit generation so a
        # response that arrives after further edits gets dropped instead of
        # being applied at a now-wrong position (see _on_eval).
        self.statusBar().showMessage("Suche Vervollständigungen…")
        generation = editor.edit_generation
        self.codeintel.scan_document(
            path, text, "Python",
            callback=lambda resp: self._on_scanned(editor, path, pos, generation),
        )

    def _drop_stale_completion(self):
        # Called wherever an in-flight completion request turns out to be
        # stale (the buffer changed since it was triggered). Only clears
        # the "Suche Vervollständigungen…" placeholder, not some unrelated
        # message that may have shown up in the meantime.
        if self.statusBar().currentMessage() == "Suche Vervollständigungen…":
            self.statusBar().clearMessage()

    def _on_scanned(self, editor, path, pos, generation):
        if editor.edit_generation != generation:
            self._drop_stale_completion()
            return
        self.codeintel.trg_from_pos(
            path, pos, lambda resp: self._on_trg(editor, pos, resp, generation), implicit=False
        )

    def _on_trg(self, editor, pos, resp, generation):
        if editor.edit_generation != generation:
            self._drop_stale_completion()
            return
        trg = resp.get("trg")
        if not trg:
            self.statusBar().showMessage("Keine Vervollständigung an dieser Position", 3000)
            return
        self.codeintel.eval_trigger(trg, lambda resp: self._on_eval(editor, pos, resp, generation))

    def _on_eval(self, editor, pos, resp, generation):
        if editor.edit_generation != generation:
            # The buffer changed while this request was in flight -- pos
            # (and possibly the whole trigger) no longer applies. Drop it
            # silently rather than inserting/popping up at a stale position;
            # the user can just re-trigger (fast now that the codeintel3
            # process has warmed its caches for this session).
            self._drop_stale_completion()
            return
        cplns = resp.get("cplns")
        if not cplns:
            self.statusBar().showMessage(
                resp.get("message", "Keine Vervollständigungen gefunden"), 3000
            )
            return
        self.statusBar().clearMessage()
        self._pending_editor = editor
        self._pending_pos = pos
        x = editor.pointXFromPosition(pos)
        y = editor.pointYFromPosition(pos) + 20
        # completion_popup is a plain child widget of this window (see its
        # docstring for why -- not a top-level Qt.WindowType.Popup), so it
        # needs a position in *this window's* coordinate system, not a
        # global/screen one.
        local_pos = self.mapFromGlobal(editor.mapToGlobal(QPoint(x, y)))
        self.completion_popup.show_completions(cplns, local_pos)

    def _insert_completion(self, name):
        editor, pos = self._pending_editor, self._pending_pos
        if editor is None or pos is None:
            return
        editor.insertText(pos, name)
        new_pos = pos + len(name.encode("utf-8"))
        editor.setSel(new_pos, new_pos)
        # ScintillaEdit.setFocus(bool) shadows QWidget.setFocus() (it's the
        # SCI_SETFOCUS message, an unrelated internal flag) -- call the
        # QWidget version explicitly to actually give it keyboard focus.
        QWidget.setFocus(editor)

    def closeEvent(self, event):
        if self._project is not None:
            self._save_session()
        for sess in list(self._debug_sessions.values()):
            if sess.is_running():
                sess.stop()
        self.codeintel.shutdown()
        super().closeEvent(event)

    def _restore_session(self):
        open_files, active_file = session.load_session(self._session_path, self._project.path)
        # Remember the blank "untitled" placeholder tab (if that's all that's
        # open) so it can be dropped *after* the real files are open --
        # closing it first would trip _close_tab's "keep at least one tab"
        # safety net and just recreate another blank tab in its place.
        placeholder_index = None
        if open_files and self.tabs.count() == 1:
            placeholder = self.tabs.widget(0)
            if placeholder.filepath is None and not placeholder.current_text():
                placeholder_index = 0
        for path in open_files:
            if os.path.isfile(path):
                self.open_file(path)
        if placeholder_index is not None and self.tabs.count() > 1:
            self._close_tab(placeholder_index)
        if active_file:
            for i in range(self.tabs.count()):
                if self.tabs.widget(i).filepath == active_file:
                    self.tabs.setCurrentIndex(i)
                    break

    def _save_session(self):
        open_files = [
            self.tabs.widget(i).filepath
            for i in range(self.tabs.count())
            if self.tabs.widget(i).filepath
        ]
        current = self.tabs.currentWidget()
        active_file = current.filepath if current is not None else None
        session.save_session(self._session_path, self._project.path, open_files, active_file)

    def _open_from_tree(self, model, index):
        path = model.filePath(index)
        if os.path.isfile(path):
            self.open_file(path)

    def new_file(self):
        editor = CodeEditor(self)
        editor.set_lexer_by_name("python")
        index = self.tabs.addTab(editor, "untitled")
        self.tabs.setCurrentIndex(index)
        editor.filepath = None

    def open_file_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open File")
        if path:
            self.open_file(path)

    def open_file(self, path):
        for i in range(self.tabs.count()):
            editor = self.tabs.widget(i)
            if editor.filepath == path:
                self.tabs.setCurrentIndex(i)
                return

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError as exc:
            QMessageBox.warning(self, "Open File", f"Could not open {path}:\n{exc}")
            return

        editor = CodeEditor(self)
        editor.setText(text)
        editor.set_lexer_for_filename(path, text)
        editor.filepath = path
        abspath = os.path.abspath(path)
        editor.restore_breakpoints(breakpoint_store.load_breakpoints(self._breakpoints_path, abspath))
        editor.breakpointsChanged.connect(lambda ed=editor: self._save_breakpoints_for(ed))

        index = self.tabs.addTab(editor, os.path.basename(path))
        self.tabs.setTabToolTip(index, path)
        self.tabs.setCurrentIndex(index)

    def save_current(self):
        editor = self.tabs.currentWidget()
        if editor is None:
            return
        item = editor.toolbox_item
        if item is not None:
            new_value = editor.current_text()
            toolbox_model.update_item(item.path, item.name, item.type, new_value, item.cwd)
            item.value = new_value
            return
        path = editor.filepath
        if not path:
            self.save_current_as()
            return
        self._write(editor, path)

    def save_current_as(self):
        editor = self.tabs.currentWidget()
        if editor is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save File As")
        if path:
            self._write(editor, path)
            editor.filepath = path
            editor.set_lexer_for_filename(path, editor.current_text())
            self.tabs.setTabText(self.tabs.indexOf(editor), os.path.basename(path))
            self.tabs.setTabToolTip(self.tabs.indexOf(editor), path)

    def _write(self, editor, path):
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(editor.current_text())
        except OSError as exc:
            QMessageBox.warning(self, "Save File", f"Could not save {path}:\n{exc}")

    def _close_tab(self, index):
        if index < 0:
            return
        widget = self.tabs.widget(index)
        self.tabs.removeTab(index)
        widget.deleteLater()
        if self.tabs.count() == 0:
            self.new_file()
