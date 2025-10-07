from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QPainter, QColor, QPen, QPainterPath
from qfluentwidgets import isDarkTheme
class ExpanderBar(QWidget):
    clicked = pyqtSignal()
    def __init__(self, parent=None,width = 4):
        super().__init__(parent)
        self.setObjectName("ExpanderBar")
        self.setFixedWidth(width)
        self.setCursor(Qt.PointingHandCursor)
        self._hovered = False
        self.setMouseTracking(True)
        self.setToolTip(self.tr("Click to expand side panel"))
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)
    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if isDarkTheme():
            if self._hovered:
                bg_color = QColor(100, 149, 237, 180)
                border_color = QColor(100, 149, 237, 220)
            else:
                bg_color = QColor(100, 100, 100, 80)
                border_color = QColor(255, 255, 255, 30)
        else:
            if self._hovered:
                bg_color = QColor(100, 149, 237, 180)
                border_color = QColor(100, 149, 237, 220)
            else:
                bg_color = QColor(150, 150, 150, 100)
                border_color = QColor(0, 0, 0, 50)
        painter.fillRect(self.rect(), bg_color)
        pen = QPen(border_color, 1 if not self._hovered else 2)
        painter.setPen(pen)
        painter.drawLine(0, 0, 0, self.height())
        if self._hovered:
            self._draw_arrow(painter)
    def _draw_arrow(self, painter):
        painter.setPen(Qt.NoPen)
        arrow_color = QColor(255, 255, 255, 200)
        painter.setBrush(arrow_color)
        center_y = self.height() // 2
        arrow_size = 8
        path = QPainterPath()
        path.moveTo(3, center_y)
        path.lineTo(3 + arrow_size // 2, center_y - arrow_size // 2)
        path.lineTo(3 + arrow_size // 2, center_y + arrow_size // 2)
        path.closeSubpath()
        painter.drawPath(path)
    def sizeHint(self):
        return QSize(4, 100)
    def minimumSizeHint(self):
        return QSize(4, 50)