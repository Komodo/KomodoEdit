"""Find in Files dialog -- UI/wiring only, all search/replace logic lives
in find_in_files.py. The actual filesystem walk/regex work runs on a
background QThread (search_files()/plan_replacements() are both plain
generators/functions with no Qt dependency, so they're safe to call from
a worker thread as long as results only get handed back to the UI thread
via signals, which is what happens here).
"""
from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from qtedit import find_in_files as fif

SCOPE_DIRECTORY = "Directory"
SCOPE_OPEN_FILES = "Open Files"
SCOPE_PROJECT = "Project"


class _SearchWorker(QObject):
    finished = Signal(list)  # list[FileHit]

    def __init__(self, paths, pattern, kwargs):
        super().__init__()
        self._paths = paths
        self._pattern = pattern
        self._kwargs = kwargs
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        hits = list(
            fif.search_files(
                self._paths,
                self._pattern,
                is_cancelled=lambda: self._cancelled,
                **self._kwargs,
            )
        )
        self.finished.emit(hits)


class _PlanWorker(QObject):
    finished = Signal(list)  # list[FileReplacement]

    def __init__(self, paths, pattern, replacement, kwargs):
        super().__init__()
        self._paths = paths
        self._pattern = pattern
        self._replacement = replacement
        self._kwargs = kwargs
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        planned = fif.plan_replacements(
            self._paths,
            self._pattern,
            self._replacement,
            is_cancelled=lambda: self._cancelled,
            **self._kwargs,
        )
        self.finished.emit(planned)


class ReplacePreviewDialog(QDialog):
    """Per-hit checklist shown before Replace All actually writes anything
    -- replaces the old single "Replace N occurrences?" summary confirm."""

    def __init__(self, replacements, base_dir, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Replace All -- Preview")
        self.resize(700, 400)
        self._replacements = replacements
        self._base_dir = base_dir

        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["", "File", "Line", "Text", "Replacement"])
        self._tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._items_by_planned = {}
        for repl in replacements:
            for planned in repl.planned:
                hit = planned.hit
                item = QTreeWidgetItem(
                    [
                        "",
                        _rel(hit.path, base_dir),
                        str(hit.line_no),
                        hit.line_text.strip(),
                        planned.replacement_text,
                    ]
                )
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(
                    0, Qt.CheckState.Checked if planned.selected else Qt.CheckState.Unchecked
                )
                self._tree.addTopLevelItem(item)
                self._items_by_planned[id(planned)] = (item, planned)
        for column in range(5):
            self._tree.resizeColumnToContents(column)

        select_row = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(lambda: self._set_all(Qt.CheckState.Checked))
        select_none_btn = QPushButton("Select None")
        select_none_btn.clicked.connect(lambda: self._set_all(Qt.CheckState.Unchecked))
        select_row.addWidget(select_all_btn)
        select_row.addWidget(select_none_btn)
        select_row.addStretch(1)

        total = sum(len(r.planned) for r in replacements)
        self._summary = QLabel(f"{total} occurrence(s) in {len(replacements)} file(s)")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self._summary)
        layout.addLayout(select_row)
        layout.addWidget(self._tree)
        layout.addWidget(buttons)

    def _set_all(self, state):
        for i in range(self._tree.topLevelItemCount()):
            self._tree.topLevelItem(i).setCheckState(0, state)

    def _on_accept(self):
        for item, planned in self._items_by_planned.values():
            planned.selected = item.checkState(0) == Qt.CheckState.Checked
        self.accept()

    def selected_replacements(self):
        """The original `replacements` list, with each PlannedReplacement's
        `.selected` updated from the checklist -- pass straight to
        find_in_files.apply_selected_replacements()."""
        return self._replacements


def _rel(path, base_dir):
    import os

    try:
        return os.path.relpath(path, base_dir)
    except ValueError:
        return path


class FindInFilesDialog(QDialog):
    # Emits the list[FileHit] from a completed "Find All" so the caller
    # (MainWindow) can populate the Find Results dock.
    hits_found = Signal(list)
    # Emits the undo record (list[(path, original_text)]) after a Replace
    # All actually writes files, so MainWindow can offer "Undo".
    replacements_applied = Signal(list)

    def __init__(self, default_dir, parent=None, open_files=None, project_base_dir=None):
        super().__init__(parent)
        self.setWindowTitle("Find in Files")
        self._open_files = open_files or []
        self._project_base_dir = project_base_dir
        self._thread = None
        self._worker = None

        self._find_edit = QLineEdit()
        self._replace_edit = QLineEdit()

        self._scope_combo = QComboBox()
        self._scope_combo.addItem(SCOPE_DIRECTORY)
        self._scope_combo.addItem(SCOPE_OPEN_FILES)
        if project_base_dir:
            self._scope_combo.addItem(SCOPE_PROJECT)
        self._scope_combo.currentTextChanged.connect(self._on_scope_changed)

        self._dir_edit = QLineEdit(default_dir)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_dir)
        self._dir_row_widgets = [self._dir_edit, browse_btn]
        dir_row = QHBoxLayout()
        for w in self._dir_row_widgets:
            dir_row.addWidget(w)

        self._include_edit = QLineEdit("*")
        self._exclude_edit = QLineEdit()

        self._recursive = QCheckBox("Search in subdirectories")
        self._recursive.setChecked(True)
        self._match_case = QCheckBox("Match case")
        self._whole_word = QCheckBox("Whole word")
        self._regex = QCheckBox("Regex")

        self._form = QFormLayout()
        self._form.addRow("Find:", self._find_edit)
        self._form.addRow("Replace:", self._replace_edit)
        self._form.addRow("Search in:", self._scope_combo)
        self._dir_row_label = QLabel("Directory:")
        self._form.addRow(self._dir_row_label, dir_row)
        self._include_label = QLabel("Include:")
        self._form.addRow(self._include_label, self._include_edit)
        self._exclude_label = QLabel("Exclude:")
        self._form.addRow(self._exclude_label, self._exclude_edit)
        self._form.addRow(self._recursive)

        options_row = QHBoxLayout()
        options_row.addWidget(self._match_case)
        options_row.addWidget(self._whole_word)
        options_row.addWidget(self._regex)
        options_row.addStretch(1)

        self._status_label = QLabel("")

        buttons = QDialogButtonBox()
        self._find_all_btn = buttons.addButton(
            "Find All", QDialogButtonBox.ButtonRole.ActionRole
        )
        self._find_all_btn.clicked.connect(self._on_find_all)
        self._replace_all_btn = buttons.addButton(
            "Replace All", QDialogButtonBox.ButtonRole.ActionRole
        )
        self._replace_all_btn.clicked.connect(self._on_replace_all)
        self._cancel_btn = buttons.addButton(
            "Cancel Search", QDialogButtonBox.ButtonRole.ActionRole
        )
        self._cancel_btn.clicked.connect(self._on_cancel_search)
        self._cancel_btn.setVisible(False)
        close_btn = buttons.addButton(QDialogButtonBox.StandardButton.Close)
        close_btn.clicked.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(self._form)
        layout.addLayout(options_row)
        layout.addWidget(self._status_label)
        layout.addWidget(buttons)

        self._find_edit.setFocus()

    def _on_scope_changed(self, scope):
        is_dir = scope == SCOPE_DIRECTORY
        self._dir_row_label.setVisible(is_dir)
        for w in self._dir_row_widgets:
            w.setVisible(is_dir)
        self._include_label.setVisible(is_dir)
        self._include_edit.setVisible(is_dir)
        self._exclude_label.setVisible(is_dir)
        self._exclude_edit.setVisible(is_dir)
        self._recursive.setVisible(is_dir)

    def _browse_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Select Directory", self._dir_edit.text())
        if path:
            self._dir_edit.setText(path)

    def _search_kwargs(self):
        return dict(
            case_sensitive=self._match_case.isChecked(),
            whole_word=self._whole_word.isChecked(),
            use_regex=self._regex.isChecked(),
        )

    def _resolve_paths(self):
        scope = self._scope_combo.currentText()
        if scope == SCOPE_OPEN_FILES:
            return list(self._open_files)
        if scope == SCOPE_PROJECT:
            root_dir = self._project_base_dir
        else:
            root_dir = self._dir_edit.text()
        if not root_dir:
            return None
        return fif.search_dir(
            root_dir,
            recursive=self._recursive.isChecked(),
            include_glob=self._include_edit.text() or "*",
            exclude_glob=self._exclude_edit.text(),
        )

    def _set_running(self, running):
        self._find_all_btn.setEnabled(not running)
        self._replace_all_btn.setEnabled(not running)
        self._cancel_btn.setVisible(running)
        self._status_label.setText("Searching..." if running else "")

    def _start_thread(self, worker, on_finished):
        self._thread = QThread(self)
        self._worker = worker
        worker.moveToThread(self._thread)
        self._thread.started.connect(worker.run)
        worker.finished.connect(on_finished)
        worker.finished.connect(self._thread.quit)
        self._thread.finished.connect(self._on_thread_done)
        self._set_running(True)
        self._thread.start()

    def _on_thread_done(self):
        self._set_running(False)
        self._thread = None
        self._worker = None

    def _on_cancel_search(self):
        if self._worker is not None:
            self._worker.cancel()

    def _on_find_all(self):
        pattern = self._find_edit.text()
        if not pattern:
            return
        paths = self._resolve_paths()
        if paths is None:
            return
        worker = _SearchWorker(paths, pattern, self._search_kwargs())
        self._start_thread(worker, self._on_find_all_finished)

    def _on_find_all_finished(self, hits):
        self.hits_found.emit(hits)
        self._status_label.setText(f"{len(hits)} match(es) found")

    def _on_replace_all(self):
        pattern = self._find_edit.text()
        if not pattern:
            return
        paths = self._resolve_paths()
        if paths is None:
            return
        replacement = self._replace_edit.text()
        worker = _PlanWorker(paths, pattern, replacement, self._search_kwargs())
        self._start_thread(worker, self._on_plan_finished)

    def _on_plan_finished(self, planned):
        if not planned:
            QMessageBox.information(self, "Replace All", "No matches found.")
            return
        scope = self._scope_combo.currentText()
        base_dir = (
            self._project_base_dir
            if scope == SCOPE_PROJECT
            else self._dir_edit.text() if scope == SCOPE_DIRECTORY else ""
        )
        preview = ReplacePreviewDialog(planned, base_dir, self)
        if preview.exec() != QDialog.DialogCode.Accepted:
            return
        selected = preview.selected_replacements()
        undo_record = fif.apply_selected_replacements(selected)
        if not undo_record:
            QMessageBox.information(self, "Replace All", "Nothing selected -- no changes made.")
            return
        all_hits = [p.hit for r in selected for p in r.planned if p.selected]
        self.hits_found.emit(all_hits)
        self.replacements_applied.emit(undo_record)
        self._status_label.setText(
            f"Replaced {len(all_hits)} occurrence(s) in {len(undo_record)} file(s)"
        )
