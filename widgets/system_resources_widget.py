from PyQt5.QtCore import Qt,  QRectF
from PyQt5.QtGui import QPainter, QColor, QBrush, QLinearGradient, QFont
from PyQt5.QtWidgets import QFrame


class ProcessTable(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        self.setMinimumHeight(80)

        self.progress = {'cpu': 0.0, 'ram': 0.0}

        # self.timer = QTimer(self)
        # self.timer.timeout.connect(self._random_update)
        # self.timer.start(300)

    def set_progress(self, type_str: str, percent: float):
        if type_str not in self.progress:
            return
        p = max(0.0, min(100.0, float(percent)))
        self.progress[type_str] = p
        self.update()

    # def _random_update(self):
    #     self.set_progress('cpu', random.randint(0, 100))
    #     self.set_progress('arm', random.randint(0, 100))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        total_width = self.width() - 20
        total_height = self.height() - 20
        rect_height = total_height / 2 - 5

        rects = {
            'cpu': QRectF(10, 10, total_width, rect_height),
            'ram': QRectF(10, 15 + rect_height, total_width, rect_height)
        }

        for name, rect in rects.items():
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(100, 100, 100, 50))
            painter.drawRoundedRect(rect, 8, 8)

            # Fill progress gradient
            fill_width = rect.width() * self.progress[name] / 100.0
            fill_rect = QRectF(rect.left() + 1, rect.top() + 1,
                               fill_width - 2, rect.height() - 2)

            grad = QLinearGradient(fill_rect.topLeft(), fill_rect.topRight())
            if name == 'cpu':
                grad.setColorAt(0, QColor(255, 180, 100))
                grad.setColorAt(1, QColor(255, 100, 50))
            else:  # arm
                grad.setColorAt(0, QColor(100, 250, 100))
                grad.setColorAt(1, QColor(50, 200, 50))

            painter.setBrush(QBrush(grad))
            painter.drawRoundedRect(fill_rect, 6, 6)

            # Draw text
            painter.setPen(QColor(255, 255, 255, 200))
            font = QFont()
            font.setPointSize(10)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(rect.adjusted(8, 0, -8, 0),
                             Qt.AlignVCenter | Qt.AlignLeft,
                             f"{name.upper()} : {int(self.progress[name])}%")
