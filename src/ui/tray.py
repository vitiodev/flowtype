from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush
from PyQt6.QtCore import Qt


def _make_icon(color):
    size = 64
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QBrush(QColor(*color)))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(20, 6, 24, 32)           # mic body
    p.drawRect(28, 37, 8, 12)              # stem
    p.drawEllipse(20, 47, 24, 8)           # base
    p.end()
    # arc (drawn separately so we don't fill it)
    pix2 = QPixmap(size, size)
    pix2.fill(Qt.GlobalColor.transparent)
    p2 = QPainter(pix2)
    p2.setRenderHint(QPainter.RenderHint.Antialiasing)
    p2.drawPixmap(0, 0, pix)
    from PyQt6.QtGui import QPen
    pen = QPen(QColor(*color), 4)
    p2.setPen(pen)
    p2.setBrush(Qt.BrushStyle.NoBrush)
    p2.drawArc(10, 22, 44, 24, 0, 180 * 16)
    p2.end()
    return QIcon(pix2)


STATES = {
    'idle':       (100, 100, 100),
    'recording':  (220,  50,  50),
    'processing': ( 50, 150, 220),
}


class TrayIcon(QSystemTrayIcon):
    def __init__(self, on_settings, on_history, on_quit, parent=None):
        super().__init__(parent)
        self._icons = {state: _make_icon(color) for state, color in STATES.items()}
        self.setIcon(self._icons['idle'])
        self.setToolTip('FlowType — Hold Right Shift to dictate')

        menu = QMenu()
        menu.addAction('FlowType').setEnabled(False)
        menu.addSeparator()
        menu.addAction('History...', on_history)
        menu.addAction('Settings...', on_settings)
        menu.addSeparator()
        menu.addAction('Quit', on_quit)
        self.setContextMenu(menu)
        self.show()

    def set_state(self, state: str):
        self.setIcon(self._icons.get(state, self._icons['idle']))
