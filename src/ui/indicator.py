from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont


class Indicator(QWidget):
    """Floating pill shown at top-center of screen during recording/processing."""

    def __init__(self):
        super().__init__()
        self._setup_window()
        self._setup_ui()
        self._blink_timer = QTimer(self)
        self._blink_timer.timeout.connect(self._blink)
        self._blink_on = True

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.X11BypassWindowManagerHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 10, 18, 10)
        layout.setSpacing(8)

        self._dot = QLabel('●')
        self._dot.setFont(QFont('', 10))
        self._dot.setStyleSheet('color: white;')

        self._label = QLabel()
        self._label.setFont(QFont('', 13, QFont.Weight.Medium))
        self._label.setStyleSheet('color: white;')

        layout.addWidget(self._dot)
        layout.addWidget(self._label)

    def _position(self):
        self.adjustSize()
        screen = self.screen().geometry()
        self.move((screen.width() - self.width()) // 2, 24)

    def _blink(self):
        self._blink_on = not self._blink_on
        self._dot.setVisible(self._blink_on)

    def show_recording(self):
        self._label.setText('Recording...')
        self.setStyleSheet('QWidget { background-color: #DC3232; border-radius: 18px; }')
        self._blink_timer.start(500)
        self.show()
        self._position()

    def show_processing(self):
        self._blink_timer.stop()
        self._dot.setVisible(True)
        self._label.setText('Transcribing...')
        self.setStyleSheet('QWidget { background-color: #3296DC; border-radius: 18px; }')
        self._position()

    def hide_indicator(self):
        self._blink_timer.stop()
        self.hide()
