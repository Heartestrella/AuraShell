from PyQt5.QtCore import Qt, QRectF,  pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QBrush, QLinearGradient, QFont,  QPen
from PyQt5.QtWidgets import QFrame


class ProcessTable(QFrame):
    fontChanged = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            ProcessTable {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(30, 30, 40, 180), 
                    stop:1 rgba(20, 20, 30, 200));
                border: 1px solid rgba(255, 255, 255, 60);
                border-radius: 12px;
            }
        """)
        self.setMinimumHeight(130)
        self.setFixedHeight(150)
        self.setMinimumWidth(300)

        self.progress = {'cpu': 0.0, 'ram': 0.0}

        self._font_family = "Segoe UI"
        self._font_size = 10
        self._font_bold = True

        self.colors = {
            'cpu': {
                'gradient_start': QColor(100, 200, 255),    # 蓝色系
                'gradient_end': QColor(50, 120, 220),
                'text': QColor(200, 230, 255)
            },
            'ram': {
                'gradient_start': QColor(255, 100, 150),    # 粉色系
                'gradient_end': QColor(220, 60, 120),
                'text': QColor(255, 200, 220)
            }
        }

    def set_font_family(self, font_family: str):
        """设置字体族"""
        if font_family and font_family != self._font_family:
            self._font_family = font_family
            self.fontChanged.emit(font_family)
            self.update()

    def set_font_size(self, size: int):
        """设置字体大小"""
        if 8 <= size <= 20 and size != self._font_size:
            self._font_size = size
            self.update()

    def set_font_bold(self, bold: bool):
        """设置字体是否粗体"""
        if bold != self._font_bold:
            self._font_bold = bold
            self.update()

    def set_progress(self, type_str: str, percent: float):
        """设置进度值"""
        if type_str not in self.progress:
            return
        p = max(0.0, min(100.0, float(percent)))
        if abs(self.progress[type_str] - p) > 0.1:
            self.progress[type_str] = p
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 绘制背景阴影效果
        self._draw_shadow(painter)

        total_width = self.width() - 40
        total_height = self.height() - 30
        rect_height = (total_height - 10) / 2

        rects = {
            'cpu': QRectF(20, 15, total_width, rect_height),
            'ram': QRectF(20, 20 + rect_height, total_width, rect_height)
        }

        for name, rect in rects.items():
            self._draw_progress_bar(painter, name, rect)

    def _draw_shadow(self, painter):
        """绘制阴影效果"""
        shadow_rect = QRectF(2, 2, self.width() - 4, self.height() - 4)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 80))
        painter.drawRoundedRect(shadow_rect, 10, 10)

    def _draw_progress_bar(self, painter, name, rect):
        """绘制单个进度条"""
        bg_rect = QRectF(rect.x(), rect.y(), rect.width(), rect.height())
        painter.setPen(QPen(QColor(255, 255, 255, 30), 1))
        painter.setBrush(QColor(50, 50, 60, 150))
        painter.drawRoundedRect(bg_rect, 8, 8)

        if self.progress[name] > 0:
            fill_width = max(10, rect.width() * self.progress[name] / 100.0)
            fill_rect = QRectF(rect.left() + 2, rect.top() + 2,
                               fill_width - 4, rect.height() - 4)

            # 创建渐变
            grad = QLinearGradient(fill_rect.topLeft(), fill_rect.topRight())
            colors = self.colors[name]
            grad.setColorAt(0, colors['gradient_start'])
            grad.setColorAt(0.7, colors['gradient_end'])
            grad.setColorAt(1, colors['gradient_end'].darker(120))

            painter.setBrush(QBrush(grad))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(fill_rect, 6, 6)

            if fill_width > 20:
                highlight_rect = QRectF(fill_rect.left(), fill_rect.top(),
                                        fill_rect.width(), fill_rect.height() * 0.3)
                highlight_grad = QLinearGradient(
                    highlight_rect.topLeft(), highlight_rect.bottomLeft())
                highlight_grad.setColorAt(0, QColor(255, 255, 255, 80))
                highlight_grad.setColorAt(1, QColor(255, 255, 255, 0))
                painter.setBrush(QBrush(highlight_grad))
                painter.drawRoundedRect(highlight_rect, 6, 6)

        self._draw_text(painter, name, rect)

    def _draw_text(self, painter, name, rect):
        """绘制文本"""
        font = QFont(self._font_family)
        font.setPointSize(self._font_size)
        font.setBold(self._font_bold)
        painter.setFont(font)

        painter.setPen(self.colors[name]['text'])
        label_rect = QRectF(rect.left() + 12, rect.top(),
                            rect.width() * 0.3, rect.height())
        painter.drawText(label_rect, Qt.AlignVCenter | Qt.AlignLeft,
                         f"{name.upper()}")

        percent_text = f"{int(self.progress[name])}%"
        percent_rect = QRectF(rect.left(), rect.top(),
                              rect.width() - 12, rect.height())
        painter.drawText(percent_rect, Qt.AlignVCenter | Qt.AlignRight,
                         percent_text)

        if self.progress[name] > 10:
            indicator_font = QFont(self._font_family)
            indicator_font.setPointSize(self._font_size - 1)
            indicator_font.setBold(True)
            painter.setFont(indicator_font)

            fill_width = rect.width() * self.progress[name] / 100.0
            if fill_width > 80:
                indicator_rect = QRectF(rect.left() + 12, rect.top(),
                                        fill_width - 24, rect.height())
                painter.setPen(QColor(255, 255, 255, 200))
                painter.drawText(indicator_rect, Qt.AlignVCenter | Qt.AlignCenter,
                                 percent_text)

    def sizeHint(self):
        """返回建议大小"""
        return self.minimumSize()
