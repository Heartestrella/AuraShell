#!/usr/bin/env python3
from qfluentwidgets import FluentIcon as FIF, IconWidget, ScrollArea
from PyQt5.QtWidgets import QFrame, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QSizePolicy, QApplication
from PyQt5.QtGui import QColor, QPainter, QBrush, QLinearGradient, QPen, QFont
from PyQt5.QtCore import Qt, pyqtSignal
import sys


class DiskCard(QFrame):
    def __init__(self, disk_id: str, data: dict, parent=None, open_callback=None):
        super().__init__(parent)
        self.disk_id = disk_id
        self.open_callback = open_callback
        self._percent = 0

        self.setMinimumHeight(38)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setAttribute(Qt.WA_StyledBackground, True)

        self.setStyleSheet("""
            QFrame { 
                border-radius: 6px; 
                margin: 0px; 
                padding: 0px; 
                background: transparent;
            }
            QLabel { 
                background: transparent; 
                border: none;
            }
        """)

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(10, 6, 10, 6)
        self.main_layout.setSpacing(6)

        self.icon = IconWidget(FIF.DEVELOPER_TOOLS, self)
        self.icon.setFixedSize(14, 14)
        self.icon.setStyleSheet("color: rgba(255,255,255,0.9);")

        self.device_label = QLabel()
        dev_font = QFont()
        dev_font.setPointSize(9)
        dev_font.setBold(True)
        self.device_label.setFont(dev_font)
        self.device_label.setStyleSheet("color: #FFFFFF;")
        self.device_label.setMinimumWidth(40)
        self.device_label.setMaximumWidth(60)

        self.mount_label = QLabel()
        mount_font = QFont()
        mount_font.setPointSize(9)
        self.mount_label.setFont(mount_font)
        self.mount_label.setStyleSheet("color: rgba(255,255,255,0.8);")
        self.mount_label.setMinimumWidth(50)
        self.mount_label.setMaximumWidth(120)

        self.usage_label = QLabel()
        usage_font = QFont()
        usage_font.setPointSize(9)
        self.usage_label.setFont(usage_font)
        self.usage_label.setStyleSheet("color: rgba(255,255,255,0.9);")
        self.usage_label.setMinimumWidth(60)

        self.percent_label = QLabel("0%")
        pct_font = QFont()
        pct_font.setPointSize(10)
        pct_font.setBold(True)
        self.percent_label.setFont(pct_font)
        self.percent_label.setStyleSheet("""
            color: #FFFFFF; 
            background: rgba(255,255,255,0.15); 
            border-radius: 8px;
            padding: 2px 6px;
        """)
        self.percent_label.setFixedWidth(38)

        self.main_layout.addWidget(self.icon, 0)
        self.main_layout.addWidget(self.device_label, 0)
        self.main_layout.addWidget(self.mount_label, 1)  # 挂载点可伸缩
        self.main_layout.addWidget(self.usage_label, 2)  # 使用情况可伸缩
        self.main_layout.addWidget(self.percent_label, 0)

        self.mount_label.installEventFilter(self)
        self.usage_label.installEventFilter(self)

        self.mouseDoubleClickEvent = self._on_double_click
        self.setData(data)

    def eventFilter(self, obj, event):
        if event.type() == event.Resize and obj in [self.mount_label, self.usage_label]:
            self._update_elided_text()
        return super().eventFilter(obj, event)

    def _update_elided_text(self):
        if hasattr(self, '_mount_text'):
            fm = self.mount_label.fontMetrics()
            width = self.mount_label.width() - 4
            elided_mount = fm.elidedText(
                self._mount_text, Qt.ElideMiddle, width)
            self.mount_label.setText(elided_mount)

        if hasattr(self, '_usage_text'):
            fm = self.usage_label.fontMetrics()
            width = self.usage_label.width() - 4
            elided_usage = fm.elidedText(
                self._usage_text, Qt.ElideRight, width)
            self.usage_label.setText(elided_usage)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_elided_text()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()
        main_col, mid_col = self._choose_colors(self._percent)
        stop = max(0.0, min(1.0, self._percent / 100.0))

        grad = QLinearGradient(rect.topLeft(), rect.topRight())
        grad.setColorAt(0, QColor(main_col))
        grad.setColorAt(max(0, stop-0.1), QColor(main_col))
        grad.setColorAt(stop, QColor(mid_col))
        grad.setColorAt(min(stop + 0.05, 1.0), QColor(0, 0, 0, 40))
        grad.setColorAt(1, QColor(0, 0, 0, 40))

        painter.setBrush(QBrush(grad))
        painter.setPen(QPen(QColor(255, 255, 255, 30), 1))

        adjusted_rect = rect.adjusted(1, 1, -1, -1)
        painter.drawRoundedRect(adjusted_rect, 6, 6)

        painter.setPen(QPen(QColor(255, 255, 255, 15), 1))
        painter.drawRoundedRect(adjusted_rect.adjusted(1, 1, -1, -1), 5, 5)

        super().paintEvent(event)

    def _choose_colors(self, percent: int):
        if percent < 60:
            return "#2ecc71", "#27ae60"
        elif percent < 85:
            return "#f1c40f", "#f39c12"
        else:
            return "#e74c3c", "#c0392b"

    def _on_double_click(self, event):
        if self.open_callback and event.button() == Qt.LeftButton:
            self.open_callback(self._mount_path)

    def setData(self, data: dict):
        device = data.get("device", "unknown")
        self.device_label.setText(device)

        mount = data.get("mount", "")
        self._mount_path = mount

        if len(mount) > 40:
            start = mount[:20]
            end = mount[-20:]
            display_mount = f"{start}...{end}"
        else:
            display_mount = mount

        self._mount_text = display_mount
        self.mount_label.setText(display_mount)
        self.mount_label.setToolTip(mount)

        used_percent = data.get("used_percent", 0)
        try:
            if isinstance(used_percent, str) and used_percent.endswith("%"):
                p = int(used_percent.rstrip("%"))
            else:
                p = int(float(used_percent))
        except (ValueError, TypeError):
            p = 0

        p = max(0, min(100, p))
        self._percent = p
        self.percent_label.setText(f"{p}%")

        size_kb = data.get("size_kb")
        used_kb = data.get("used_kb")

        if size_kb is not None and used_kb is not None:
            try:
                def format_size(kb):
                    if kb >= 1024 * 1024:
                        return f"{kb / 1024 / 1024:.1f}G"
                    if kb >= 1024:
                        return f"{kb / 1024:.1f}M"
                    return f"{kb}K"

                used_str = format_size(used_kb)
                total_str = format_size(size_kb)
                self._usage_text = f"{used_str} / {total_str}"
            except Exception:
                self._usage_text = ""
        else:
            self._usage_text = ""

        self._update_elided_text()
        self.update()


class DiskMonitor(QWidget):
    into_driver_path = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.disk_items = {}

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)

        title_layout = QHBoxLayout()
        title_label = QLabel(self.tr("Storage Status"))
        title_font = QFont()
        title_font.setPointSize(11)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: white; padding: 2px;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        main_layout.addLayout(title_layout)

        self.scroll_area = ScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            ScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: rgba(255,255,255,0.1);
                width: 6px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255,255,255,0.3);
                border-radius: 3px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255,255,255,0.5);
            }
        """)

        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(2, 4, 2, 4)
        self.container_layout.setSpacing(5)
        self.container_layout.setAlignment(Qt.AlignTop)

        self.scroll_area.setWidget(self.container)
        main_layout.addWidget(self.scroll_area)

    def add_disk_item(self, disk_id: str, data: dict):
        if disk_id in self.disk_items:
            self.update_disk_item(disk_id, data)
            return

        card = DiskCard(disk_id, data, self.container, self._on_open_mount)
        self.container_layout.addWidget(card)
        self.disk_items[disk_id] = card

    def update_disk_item(self, disk_id: str, data: dict):
        card = self.disk_items.get(disk_id)
        if card:
            card.setData(data)
        else:
            self.add_disk_item(disk_id, data)

    def remove_disk_item(self, disk_id: str):
        card = self.disk_items.pop(disk_id, None)
        if card:
            card.deleteLater()

    def _on_open_mount(self, mount_path: str):
        self.into_driver_path.emit(mount_path)
