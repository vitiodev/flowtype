from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox,
    QLineEdit, QGroupBox, QLabel, QDialogButtonBox
)
from PyQt6.QtCore import pyqtSignal
import config as cfg_module

MODELS = ['tiny', 'base', 'small', 'medium', 'large']
LANGUAGES = [
    ('Auto-detect', None),
    ('Russian',     'ru'),
    ('English',     'en'),
    ('German',      'de'),
    ('French',      'fr'),
    ('Spanish',     'es'),
    ('Chinese',     'zh'),
    ('Japanese',    'ja'),
]
DEVICES = ['cpu', 'cuda']
INJECT_METHODS = ['ydotool', 'clipboard']


class SettingsDialog(QDialog):
    settings_changed = pyqtSignal(dict)

    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self._cfg = cfg
        self.setWindowTitle('FlowType — Settings')
        self.setMinimumWidth(360)
        self._setup_ui()
        self._load(cfg)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # --- Whisper ---
        whisper_box = QGroupBox('Speech Recognition')
        form = QFormLayout(whisper_box)

        self._model = QComboBox()
        self._model.addItems(MODELS)
        form.addRow('Model:', self._model)

        self._language = QComboBox()
        for label, _ in LANGUAGES:
            self._language.addItem(label)
        form.addRow('Language:', self._language)

        self._device = QComboBox()
        self._device.addItems(DEVICES)
        form.addRow('Device:', self._device)

        layout.addWidget(whisper_box)

        # --- Input ---
        input_box = QGroupBox('Input')
        form2 = QFormLayout(input_box)

        self._hotkey = QLineEdit()
        self._hotkey.setPlaceholderText('e.g. KEY_RIGHTSHIFT')
        form2.addRow('Hotkey:', self._hotkey)

        self._inject = QComboBox()
        self._inject.addItems(INJECT_METHODS)
        form2.addRow('Text injection:', self._inject)

        layout.addWidget(input_box)

        note = QLabel('* Model and device changes require restart.')
        note.setStyleSheet('color: gray; font-size: 11px;')
        layout.addWidget(note)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load(self, cfg):
        self._model.setCurrentText(cfg.get('model', 'base'))
        lang_val = cfg.get('language', None)
        for i, (_, val) in enumerate(LANGUAGES):
            if val == lang_val:
                self._language.setCurrentIndex(i)
                break
        self._device.setCurrentText(cfg.get('device', 'cpu'))
        self._hotkey.setText(cfg.get('hotkey', 'KEY_RIGHTSHIFT'))
        self._inject.setCurrentText(cfg.get('inject_method', 'ydotool'))

    def _save(self):
        lang_idx = self._language.currentIndex()
        self._cfg.update({
            'model':         self._model.currentText(),
            'language':      LANGUAGES[lang_idx][1],
            'device':        self._device.currentText(),
            'hotkey':        self._hotkey.text().strip(),
            'inject_method': self._inject.currentText(),
        })
        cfg_module.save(self._cfg)
        self.settings_changed.emit(self._cfg)
        self.accept()
