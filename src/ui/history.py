from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget,
    QListWidgetItem, QPushButton, QLabel, QApplication
)
from PyQt6.QtCore import Qt, QDateTime
from PyQt6.QtGui import QFont


class HistoryWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('FlowType — History')
        self.resize(420, 520)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 12)
        layout.setSpacing(10)

        # Header
        header = QHBoxLayout()
        title = QLabel('Recent transcriptions')
        title.setFont(QFont('', 13, QFont.Weight.Bold))
        clear_btn = QPushButton('Clear')
        clear_btn.setFixedWidth(64)
        clear_btn.clicked.connect(self._list.clear if hasattr(self, '_list') else lambda: None)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(clear_btn)
        layout.addLayout(header)

        # List
        self._list = QListWidget()
        self._list.setAlternatingRowColors(True)
        self._list.setWordWrap(True)
        self._list.setSpacing(2)
        self._list.itemDoubleClicked.connect(self._copy_item)
        layout.addWidget(self._list)

        # Wire clear button now that _list exists
        clear_btn.clicked.disconnect()
        clear_btn.clicked.connect(self._list.clear)

        # Hint
        hint = QLabel('Double-click an entry to copy to clipboard')
        hint.setStyleSheet('color: gray; font-size: 11px;')
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

    def add_entry(self, text):
        time_str = QDateTime.currentDateTime().toString('HH:mm:ss')
        item = QListWidgetItem(f'[{time_str}]   {text}')
        item.setData(Qt.ItemDataRole.UserRole, text)
        item.setToolTip(text)
        self._list.insertItem(0, item)

    def _copy_item(self, item):
        QApplication.clipboard().setText(item.data(Qt.ItemDataRole.UserRole))
