import sys
import os
import threading

# Use X11 via XWayland for precise window positioning (pill indicator)
os.environ.setdefault('QT_QPA_PLATFORM', 'xcb')

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal

from config import load as load_config
from recorder import Recorder
from transcriber import Transcriber
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

        # Load Whisper model in background
        threading.Thread(target=self._load_model, daemon=True).start()

    # ------------------------------------------------------------------ #
    #  Model loading                                                       #
    # ------------------------------------------------------------------ #

    def _load_model(self):
        self.transcriber = Transcriber(
            model               = self.cfg['model'],
            device              = self.cfg['device'],
            language            = self.cfg['language'],
            silence_threshold   = self.cfg.get('silence_threshold', 0.01),
        )
        self._start_hotkey()

    def _start_hotkey(self):
        self.hotkey = HotkeyListener(
            hotkey     = self.cfg['hotkey'],
            on_press   = self._on_press,
            on_release = self._on_release,
        )
        self.hotkey.start()

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
        # Update silence threshold in transcriber without reload
        if self.transcriber:
            self.transcriber.set_silence_threshold(cfg.get('silence_threshold', 0.01))

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
