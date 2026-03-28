import sys
import os
import threading

# Use X11 via XWayland for precise window positioning (pill indicator)
os.environ.setdefault('QT_QPA_PLATFORM', 'xcb')

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal

from config import load as load_config
from recorder import Recorder
from transcriber import make_transcriber
from hotkey import HotkeyListener
from injector import inject_text, run_shell_command
from commands import load_commands, match_and_run
from ui.tray import TrayIcon
from ui.indicator import Indicator
from ui.settings import SettingsDialog
from ui.history import HistoryWindow
from ui.commands import CommandsDialog


class FlowType(QObject):
    # Signals for thread-safe UI updates from evdev/worker threads
    _sig_record_started  = pyqtSignal()
    _sig_record_stopped  = pyqtSignal()
    _sig_text_ready      = pyqtSignal(str)
    _sig_error           = pyqtSignal(str)
    _sig_amplitude       = pyqtSignal(object)  # list of N_BANDS floats

    def __init__(self, app: QApplication):
        super().__init__()
        self.app = app
        self.cfg = load_config()
        self.recorder = Recorder(
            sample_rate        = self.cfg['sample_rate'],
            device             = self.cfg.get('audio_device'),
            silence_threshold  = self.cfg.get('silence_threshold', 0.01),
        )
        self.transcriber = None
        self.hotkey = None
        self._is_recording = False
        self._lock = threading.Lock()

        # UI
        self.commands      = load_commands()
        self.indicator     = Indicator()
        self.history_win   = HistoryWindow()
        self.tray          = TrayIcon(
            on_settings  = self._show_settings,
            on_history   = self._show_history,
            on_commands  = self._show_commands,
            on_quit      = app.quit,
        )

        # Wire signals → UI slots (always runs in Qt main thread)
        self._sig_record_started.connect(self._ui_on_record_started)
        self._sig_record_stopped.connect(self._ui_on_record_stopped)
        self._sig_text_ready.connect(self._ui_on_text_ready)
        self._sig_error.connect(self._ui_on_error)
        self._sig_amplitude.connect(self.indicator.push_amplitude)
        self._setup_amplitude_callback()

        # Load Whisper model in background
        threading.Thread(target=self._load_model, daemon=True).start()

    # ------------------------------------------------------------------ #
    #  Model loading                                                       #
    # ------------------------------------------------------------------ #

    def _load_model(self):
        self.transcriber = make_transcriber(self.cfg)
        self._start_hotkey()

    def _start_hotkey(self):
        self.hotkey = HotkeyListener(
            hotkey     = self.cfg['hotkey'],
            on_press   = self._on_press,
            on_release = self._on_release,
        )
        self.hotkey.start()

    def _setup_amplitude_callback(self):
        import time as _time
        import numpy as np
        from ui.indicator import N_BANDS

        _last = [0.0]
        _buf = [np.zeros(2048, dtype='float32')]
        sr = self.cfg.get('sample_rate', 16000)
        sig = self._sig_amplitude

        def _cb(indata: np.ndarray):
            now = _time.monotonic()
            if now - _last[0] < 0.040:
                return
            _last[0] = now

            chunk = indata[:, 0] if indata.ndim > 1 else indata.flatten()
            buf = _buf[0]
            n = len(chunk)
            if n >= len(buf):
                _buf[0] = chunk[-len(buf):].astype('float32')
            else:
                _buf[0] = np.roll(buf, -n)
                _buf[0][-n:] = chunk

            window = np.hanning(len(_buf[0]))
            spectrum = np.abs(np.fft.rfft(_buf[0] * window))
            n_fft = len(spectrum)

            # Log-spaced bands 80 Hz – 8000 Hz
            lo_bin = max(1, int(80 * len(_buf[0]) / sr))
            hi_bin = min(n_fft - 1, int(8000 * len(_buf[0]) / sr))
            edges = np.logspace(np.log10(lo_bin), np.log10(hi_bin), N_BANDS + 1)
            edges = np.clip(edges.astype(int), 1, n_fft - 1)

            bands = []
            for i in range(N_BANDS):
                lo, hi = edges[i], edges[i + 1]
                if hi <= lo:
                    hi = lo + 1
                energy = float(np.sqrt(np.mean(spectrum[lo:hi] ** 2)))
                bands.append(min(energy / 2.0, 1.0))

            sig.emit(bands)

        self.recorder.amplitude_callback = _cb

    # ------------------------------------------------------------------ #
    #  Hotkey callbacks  (called from evdev thread)                        #
    # ------------------------------------------------------------------ #

    def _on_press(self):
        with self._lock:
            if self._is_recording or self.transcriber is None:
                return
            self._is_recording = True
        self.recorder.start()
        self._sig_record_started.emit()

    def _on_release(self):
        with self._lock:
            if not self._is_recording:
                return
            self._is_recording = False
        audio = self.recorder.stop()
        self._sig_record_stopped.emit()
        threading.Thread(target=self._transcribe, args=(audio,), daemon=True).start()

    def _transcribe(self, audio):
        import time
        t0 = time.time()
        print(f'[flowtype] Transcribing {len(audio)/16000:.1f}s of audio...')
        try:
            text = self.transcriber.transcribe(audio)
        except Exception as e:
            print(f'[flowtype] Transcription error: {e}')
            self._sig_error.emit(str(e))
            text = ''
        print(f'[flowtype] Transcription done in {time.time()-t0:.1f}s')
        self._sig_text_ready.emit(text)

    # ------------------------------------------------------------------ #
    #  UI slots  (always runs in Qt main thread)                           #
    # ------------------------------------------------------------------ #

    def _ui_on_record_started(self):
        self.tray.set_state('recording')
        self.indicator.show_recording()

    def _ui_on_record_stopped(self):
        self.tray.set_state('processing')
        self.indicator.show_processing()

    def _ui_on_text_ready(self, text: str):
        self.tray.set_state('idle')
        self.indicator.hide_indicator()
        if text:
            print(f'[flowtype] → "{text}"')
            if match_and_run(text, self.commands):
                self.history_win.add_entry(f'[cmd] {text}')
            else:
                self.history_win.add_entry(text)
                command_mode = self.cfg.get('command_mode', 'none')
                if command_mode == 'shell':
                    threading.Thread(
                        target=run_shell_command,
                        args=(text,),
                        daemon=True,
                    ).start()
                else:
                    threading.Thread(
                        target=inject_text,
                        args=(text, self.cfg['inject_method']),
                        kwargs={'run_in_terminal': command_mode == 'terminal'},
                        daemon=True,
                    ).start()
        else:
            print('[flowtype] No speech detected.')

    # ------------------------------------------------------------------ #
    #  Windows                                                             #
    # ------------------------------------------------------------------ #

    def _show_settings(self):
        dlg = SettingsDialog(self.cfg)
        dlg.settings_changed.connect(self._apply_settings)
        dlg.exec()

    def _apply_settings(self, cfg: dict):
        old_cfg = self.cfg
        self.cfg = cfg
        # Restart hotkey listener if hotkey changed
        if self.hotkey:
            self.hotkey.stop()
        self._start_hotkey()
        # Re-create recorder if audio device or silence threshold changed
        if (cfg.get('audio_device') != old_cfg.get('audio_device') or
                cfg.get('silence_threshold') != old_cfg.get('silence_threshold')):
            self.recorder.close()
            self.recorder = Recorder(
                sample_rate       = cfg['sample_rate'],
                device            = cfg.get('audio_device'),
                silence_threshold = cfg.get('silence_threshold', 0.01),
            )
            self._setup_amplitude_callback()
        # Reload transcriber if any transcription-related setting changed
        _transcriber_keys = ('transcription_mode', 'model', 'device', 'language',
                             'api_url', 'api_key', 'api_model')
        if any(cfg.get(k) != old_cfg.get(k) for k in _transcriber_keys):
            self.transcriber = None
            threading.Thread(target=self._load_model, daemon=True).start()
        elif self.transcriber:
            self.transcriber.set_silence_threshold(cfg.get('silence_threshold', 0.01))

    def _ui_on_error(self, message: str):
        self.tray.set_state('idle')
        self.indicator.hide_indicator()
        self.tray.show_error(message)

    def _show_history(self):
        self.history_win.show()
        self.history_win.raise_()
        self.history_win.activateWindow()

    def _show_commands(self):
        dlg = CommandsDialog()
        if dlg.exec():
            self.commands = load_commands()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setApplicationName('FlowType')
    app.setQuitOnLastWindowClosed(False)  # keep running when windows closed

    ft = FlowType(app)
    sys.exit(app.exec())
