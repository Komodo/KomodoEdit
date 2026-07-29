"""Small dialog for attaching a condition expression and/or an ignore
(hit) count to the breakpoint on the editor's current line -- operates on
the cursor line rather than via a margin right-click, consistent with how
toggle_breakpoint() already works off F9/the current line (see the plan
doc's Debugger phase: a margin right-click was considered and rejected,
since Scintilla's marginClicked signal doesn't cleanly distinguish mouse
buttons)."""
from PySide6.QtWidgets import (
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QDialog,
)


class BreakpointConditionDialog(QDialog):
    def __init__(self, condition="", ignore_count=0, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Breakpoint Condition")

        self._condition_edit = QLineEdit(condition)
        self._condition_edit.setPlaceholderText("e.g. i == 3 (leave empty for unconditional)")
        self._ignore_spin = QSpinBox()
        self._ignore_spin.setRange(0, 1_000_000)
        self._ignore_spin.setValue(ignore_count)
        self._ignore_spin.setSpecialValueText("0 (break every hit)")

        form = QFormLayout()
        form.addRow("Condition:", self._condition_edit)
        form.addRow("Ignore count:", self._ignore_spin)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)
        self.setLayout(form)

    def condition(self):
        return self._condition_edit.text().strip()

    def ignore_count(self):
        return self._ignore_spin.value()
