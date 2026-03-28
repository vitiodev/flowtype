from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox,
    QLineEdit, QGroupBox, QLabel, QDialogButtonBox,
    QSlider, QHBoxLayout, QWidget
)
from PyQt6.QtCore import pyqtSignal, Qt
import sounddevice as sd
import config as cfg_module

TRANSCRIPTION_MODES = [
    ('Local (faster-whisper)', 'local'),
    ('API (OpenAI-compatible)', 'api'),
]
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
INJECT_METHODS = ['auto', 'ydotool', 'xdotool', 'clipboard']
COMMAND_MODES = [
    ('Just insert text', 'none'),
    ('Run in terminal (insert + Enter)', 'terminal'),
    ('Run via shell (background)', 'shell'),
]


def _get_input_devices():
    """Return list of (display_name, device_index_or_None) for input devices."""
    result = [('System default', None)]
    try:
        for i, dev in enumerate(sd.query_devices()):
            if dev['max_input_channels'] > 0:
                name = dev['name']
                result.append((f'{name}', i))
    except Exception:
        pass
    return result


class SettingsDialog(QDialog):
    settings_changed = pyqtSignal(dict)

    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self._cfg = cfg
        self._input_devices = _get_input_devices()
        self.setWindowTitle('FlowType — Settings')
        self.setMinimumWidth(420)
        self._setup_ui()
        self._load(cfg)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # --- Speech Recognition ---
        whisper_box = QGroupBox('Speech Recognition')
        vbox = QVBoxLayout(whisper_box)

        # Mode selector — always visible
        mode_form = QFormLayout()
        self._mode = QComboBox()
        for label, _ in TRANSCRIPTION_MODES:
            self._mode.addItem(label)
        mode_form.addRow('Mode:', self._mode)
        vbox.addLayout(mode_form)

        # Local-only fields (model, device)
        self._local_widget = QWidget()
        local_form = QFormLayout(self._local_widget)
        local_form.setContentsMargins(0, 0, 0, 0)
        self._model = QComboBox()
        self._model.addItems(MODELS)
        local_form.addRow('Model:', self._model)
        self._device = QComboBox()
        self._device.addItems(DEVICES)
        local_form.addRow('Device:', self._device)
        vbox.addWidget(self._local_widget)

        # API-only fields
        self._api_widget = QWidget()
        api_form = QFormLayout(self._api_widget)
        api_form.setContentsMargins(0, 0, 0, 0)
        self._api_url = QLineEdit()
        self._api_url.setPlaceholderText('https://api.openai.com/v1')
        api_form.addRow('API URL:', self._api_url)
        self._api_key = QLineEdit()
        self._api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key.setPlaceholderText('sk-...')
        api_form.addRow('API Key:', self._api_key)
        self._api_model = QLineEdit()
        self._api_model.setPlaceholderText('whisper-1')
        api_form.addRow('Model name:', self._api_model)
        vbox.addWidget(self._api_widget)

        # Language — visible in both modes
        lang_form = QFormLayout()
        self._language = QComboBox()
        for label, _ in LANGUAGES:
            self._language.addItem(label)
        lang_form.addRow('Language:', self._language)
        vbox.addLayout(lang_form)

        self._mode.currentIndexChanged.connect(self._on_mode_changed)
        layout.addWidget(whisper_box)

        # --- Audio ---
        audio_box = QGroupBox('Audio')
        form3 = QFormLayout(audio_box)

        self._audio_device = QComboBox()
        for label, _ in self._input_devices:
            self._audio_device.addItem(label)
        form3.addRow('Input device:', self._audio_device)

        # Silence threshold slider: range 1–50 (maps to 0.001–0.050)
        thresh_row = QHBoxLayout()
        self._thresh_slider = QSlider(Qt.Orientation.Horizontal)
        self._thresh_slider.setRange(1, 50)
        self._thresh_slider.setTickInterval(5)
        self._thresh_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._thresh_label = QLabel()
        self._thresh_label.setFixedWidth(40)
        self._thresh_slider.valueChanged.connect(self._update_thresh_label)
        thresh_row.addWidget(self._thresh_slider)
        thresh_row.addWidget(self._thresh_label)
        form3.addRow('Silence threshold:', thresh_row)

        thresh_hint = QLabel('Lower = more sensitive (picks up quiet speech)\n'
                             'Higher = ignores background noise')
        thresh_hint.setStyleSheet('color: gray; font-size: 11px;')
        form3.addRow('', thresh_hint)

        layout.addWidget(audio_box)

        # --- Input ---
        input_box = QGroupBox('Input')
        form2 = QFormLayout(input_box)

        self._hotkey = QLineEdit()
        self._hotkey.setPlaceholderText('e.g. KEY_RIGHTSHIFT or ctrl+alt')
        form2.addRow('Hotkey:', self._hotkey)

        self._inject = QComboBox()
        self._inject.addItems(INJECT_METHODS)
        form2.addRow('Text injection:', self._inject)

        self._command_mode = QComboBox()
        for label, _ in COMMAND_MODES:
            self._command_mode.addItem(label)
        form2.addRow('Command mode:', self._command_mode)

        layout.addWidget(input_box)

        note = QLabel('* Mode/model/device changes take effect immediately after Save.')
        note.setStyleSheet('color: gray; font-size: 11px;')
        layout.addWidget(note)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_mode_changed(self, index):
        is_api = (TRANSCRIPTION_MODES[index][1] == 'api')
        self._local_widget.setVisible(not is_api)
        self._api_widget.setVisible(is_api)

    def _update_thresh_label(self, value):
        self._thresh_label.setText(f'{value / 1000:.3f}')

    def _load(self, cfg):
        mode_val = cfg.get('transcription_mode', 'local')
        for i, (_, val) in enumerate(TRANSCRIPTION_MODES):
            if val == mode_val:
                self._mode.setCurrentIndex(i)
                break
        self._on_mode_changed(self._mode.currentIndex())

        self._api_url.setText(cfg.get('api_url', 'https://api.openai.com/v1'))
        self._api_key.setText(cfg.get('api_key', ''))
        self._api_model.setText(cfg.get('api_model', 'whisper-1'))

        self._model.setCurrentText(cfg.get('model', 'base'))
        lang_val = cfg.get('language', None)
        for i, (_, val) in enumerate(LANGUAGES):
            if val == lang_val:
                self._language.setCurrentIndex(i)
                break
        self._device.setCurrentText(cfg.get('device', 'cpu'))
        self._hotkey.setText(cfg.get('hotkey', 'KEY_RIGHTSHIFT'))
        self._inject.setCurrentText(cfg.get('inject_method', 'auto'))

        cmd_val = cfg.get('command_mode', 'none')
        for i, (_, val) in enumerate(COMMAND_MODES):
            if val == cmd_val:
                self._command_mode.setCurrentIndex(i)
                break

        # Audio device
        saved_dev = cfg.get('audio_device', None)
        for i, (_, idx) in enumerate(self._input_devices):
            if idx == saved_dev:
                self._audio_device.setCurrentIndex(i)
                break

        # Silence threshold (0.001–0.050 → slider 1–50)
        thresh = cfg.get('silence_threshold', 0.01)
        self._thresh_slider.setValue(max(1, min(50, int(thresh * 1000))))

    def _save(self):
        lang_idx = self._language.currentIndex()
        audio_dev_idx = self._audio_device.currentIndex()
        self._cfg.update({
            'transcription_mode':  TRANSCRIPTION_MODES[self._mode.currentIndex()][1],
            'api_url':             self._api_url.text().strip() or 'https://api.openai.com/v1',
            'api_key':             self._api_key.text(),
            'api_model':           self._api_model.text().strip() or 'whisper-1',
            'model':               self._model.currentText(),
            'language':            LANGUAGES[lang_idx][1],
            'device':              self._device.currentText(),
            'hotkey':              self._hotkey.text().strip(),
            'inject_method':       self._inject.currentText(),
            'command_mode':        COMMAND_MODES[self._command_mode.currentIndex()][1],
            'audio_device':        self._input_devices[audio_dev_idx][1],
            'silence_threshold':   self._thresh_slider.value() / 1000,
        })
        cfg_module.save(self._cfg)
        self.settings_changed.emit(self._cfg)
        self.accept()
