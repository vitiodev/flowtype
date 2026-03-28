from PyQt6.QtWidgets import QApplication, QWidget, QHBoxLayout
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QPainter, QColor

N_BANDS = 14


class WaveformWidget(QWidget):
    """Equalizer-style bar graph: each bar = one frequency band."""

    WIDTH = 120
    HEIGHT = 36

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(self.WIDTH, self.HEIGHT)
        self.setStyleSheet('background: transparent;')
        self._bands = [0.0] * N_BANDS
        self._active = True
        self._decay_timer = QTimer(self)
        self._decay_timer.setInterval(50)
        self._decay_timer.timeout.connect(self._decay)

    def sizeHint(self):
        return QSize(self.WIDTH, self.HEIGHT)

    def set_bands(self, values):
        for i, v in enumerate(values[:N_BANDS]):
            if v > self._bands[i]:
                self._bands[i] = v                          # instant attack
            else:
                self._bands[i] = self._bands[i] * 0.5 + v * 0.5  # smooth release
        self.update()

    def set_active(self, active: bool):
        self._active = active
        if not active:
            self._decay_timer.start()
        else:
            self._decay_timer.stop()
        self.update()

    def reset(self):
        self._decay_timer.stop()
        self._bands = [0.0] * N_BANDS
        self._active = True
        self.update()

    def _decay(self):
        self._bands = [v * 0.8 for v in self._bands]
        self.update()
        if all(v < 0.005 for v in self._bands):
            self._decay_timer.stop()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        n = N_BANDS
        gap = 2
        bar_w = (w - gap * (n - 1)) / n

        color = QColor(255, 255, 255, 220 if self._active else 100)
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)

        for i, val in enumerate(self._bands):
            bar_h = max(3.0, val * h)
            x = i * (bar_w + gap)
            y = h - bar_h          # grow from bottom
            painter.drawRoundedRect(int(x), int(y), int(bar_w), int(bar_h), 1, 1)

        painter.end()


class Indicator(QWidget):
    """Floating pill shown at bottom-center of screen during recording/processing."""

    def __init__(self):
        super().__init__()
        self.setObjectName('Indicator')
        self._setup_window()
        self._setup_ui()

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
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(0)
        self._wave = WaveformWidget()
        layout.addWidget(self._wave)

    def _position(self):
        self.adjustSize()
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = screen.height() - self.height() - 24
        self.move(x, y)

    def push_amplitude(self, bands):
        self._wave.set_bands(bands)

    def show_recording(self):
        self.setStyleSheet('#Indicator { background-color: #DC3232; border-radius: 18px; }')
        self._wave.set_active(True)
        self.show()
        self._position()

    def show_processing(self):
        self._wave.set_active(False)
        self.setStyleSheet('#Indicator { background-color: #3296DC; border-radius: 18px; }')
        self._position()

    def hide_indicator(self):
        self._wave.reset()
        self.hide()
