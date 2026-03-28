"""Dialog for managing voice commands."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QDialogButtonBox, QHeaderView, QCheckBox, QLabel,
    QAbstractItemView, QMessageBox, QLineEdit, QFormLayout
)
from PyQt6.QtCore import Qt
import commands as cmd_module


class _EditDialog(QDialog):
    """Add / edit a single voice command."""

    def __init__(self, phrase='', command='', exact=False, terminal=False, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Edit Command')
        self.setMinimumWidth(440)
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self._phrase = QLineEdit(phrase)
        self._phrase.setPlaceholderText('e.g. открой терминал')
        form.addRow('Voice phrase:', self._phrase)

        self._command = QLineEdit(command)
        self._command.setPlaceholderText('e.g. gnome-terminal')
        form.addRow('Shell command:', self._command)

        self._exact = QCheckBox('Exact match (phrase must equal full transcription)')
        self._exact.setChecked(exact)
        form.addRow('', self._exact)

        self._terminal = QCheckBox('Run in terminal window (output visible)')
        self._terminal.setChecked(terminal)
        form.addRow('', self._terminal)

        layout.addLayout(form)

        hint = QLabel('Hint: leave "Exact match" unchecked to trigger the command\n'
                      'whenever the phrase appears anywhere in what you say.\n'
                      '"Run in terminal" opens a terminal window so you can see output.')
        hint.setStyleSheet('color: gray; font-size: 11px;')
        layout.addWidget(hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _validate(self):
        if not self._phrase.text().strip():
            QMessageBox.warning(self, 'Validation', 'Voice phrase cannot be empty.')
            return
        if not self._command.text().strip():
            QMessageBox.warning(self, 'Validation', 'Shell command cannot be empty.')
            return
        self.accept()

    def result_data(self) -> dict:
        return {
            'phrase':    self._phrase.text().strip(),
            'command':   self._command.text().strip(),
            'exact':     self._exact.isChecked(),
            'terminal':  self._terminal.isChecked(),
        }


class CommandsDialog(QDialog):
    """Main dialog: table of all voice commands with add / edit / delete."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('FlowType — Voice Commands')
        self.setMinimumSize(600, 400)
        self._commands = cmd_module.load_commands()
        self._setup_ui()
        self._populate()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        info = QLabel(
            'Voice commands are matched against the transcribed text.\n'
            'When a phrase is recognised the shell command is executed instead of typing.'
        )
        info.setStyleSheet('color: gray; font-size: 11px;')
        layout.addWidget(info)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(['Voice phrase', 'Shell command', 'Exact', 'Terminal'])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.doubleClicked.connect(self._edit_selected)
        layout.addWidget(self._table)

        btn_row = QHBoxLayout()
        add_btn  = QPushButton('Add')
        edit_btn = QPushButton('Edit')
        del_btn  = QPushButton('Delete')
        add_btn.clicked.connect(self._add)
        edit_btn.clicked.connect(self._edit_selected)
        del_btn.clicked.connect(self._delete_selected)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(edit_btn)
        btn_row.addWidget(del_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _populate(self):
        self._table.setRowCount(0)
        for cmd in self._commands:
            self._add_row(cmd)

    def _add_row(self, cmd: dict):
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._table.setItem(row, 0, QTableWidgetItem(cmd.get('phrase', '')))
        self._table.setItem(row, 1, QTableWidgetItem(cmd.get('command', '')))
        for col, key in ((2, 'exact'), (3, 'terminal')):
            item = QTableWidgetItem('Yes' if cmd.get(key) else 'No')
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, col, item)

    def _add(self):
        dlg = _EditDialog(parent=self)
        if dlg.exec():
            data = dlg.result_data()
            self._commands.append(data)
            self._add_row(data)

    def _edit_selected(self):
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
        cmd = self._commands[row]
        dlg = _EditDialog(
            phrase=cmd.get('phrase', ''),
            command=cmd.get('command', ''),
            exact=cmd.get('exact', False),
            terminal=cmd.get('terminal', False),
            parent=self,
        )
        if dlg.exec():
            data = dlg.result_data()
            self._commands[row] = data
            self._table.item(row, 0).setText(data['phrase'])
            self._table.item(row, 1).setText(data['command'])
            self._table.item(row, 2).setText('Yes' if data['exact'] else 'No')
            self._table.item(row, 3).setText('Yes' if data['terminal'] else 'No')

    def _delete_selected(self):
        rows = sorted(
            [r.row() for r in self._table.selectionModel().selectedRows()],
            reverse=True,
        )
        for row in rows:
            self._table.removeRow(row)
            del self._commands[row]

    def _save(self):
        cmd_module.save_commands(self._commands)
        self.accept()
