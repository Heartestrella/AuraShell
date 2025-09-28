#!/usr/bin/env python3
# disk_monitor_demo.py
# Demo: Disk monitor widget (PyQt5 + qfluentwidgets)
# - Cards auto-resize to scroll viewport width
# - No "occupying stretch" that blocks expansion
# - APIs: add_disk_item, update_disk_item, remove_disk_item
# - Simple demo random updates

from qfluentwidgets import FluentIcon as FIF, IconWidget, ToolButton
from PyQt5.QtWidgets import QFrame, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QSizePolicy
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, QTimer
from qfluentwidgets import FluentIcon as FIF, IconWidget, ToolButton, ScrollArea as QS_SCROLL
import sys
import random
from functools import partial
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QRectF, QEvent
from PyQt5.QtGui import QColor, QPainter, QPen, QBrush, QLinearGradient, QFont
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QApplication, QPushButton, QSizePolicy
)
from tools.font_config import font_config
_FONT = font_config().get_font()

# fallback font_config.get_font


class GradientFillBackgroundMixin:
    @staticmethod
    def _choose_colors(percent: int):
        if percent < 60:
            return "#27ae60", "#2ecc71"
        elif percent < 85:
            return "#f39c12", "#f1c40f"
        else:
            return "#e74c3c", "#c0392b"

    @staticmethod
    def _fg_text_color_for_percent(percent: int):
        return "#FFFFFF"


# 只贴关键类： FillDiskCard 和 DiskMonitor


class FillDiskCard(QFrame):
    def __init__(self, disk_id: str, data: dict, parent=None, open_callback=None):
        super().__init__(parent)
        self.disk_id = disk_id
        self.open_callback = open_callback
        self.setFixedHeight(90)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(72)
        self.setAttribute(Qt.WA_StyledBackground, True)

        self._percent = 0

        # 基础样式（文字透明背景）
        self.setStyleSheet("""
            QFrame { border-radius: 10px; margin:0px; padding:0px; }
            QLabel, QPushButton { background: transparent; }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(12)

        # --- 左侧（设备 + 挂载点）
        left_v = QVBoxLayout()
        top_row = QHBoxLayout()
        self.icon = IconWidget(FIF.DEVELOPER_TOOLS, self)
        self.icon.setFixedSize(16, 16)

        self.device_label = QLabel(data.get("device", "unknown"))
        self.device_label.setStyleSheet("font-weight:700; color: #FFFFFF;")

        top_row.addWidget(self.icon, 0, Qt.AlignVCenter)
        top_row.addWidget(self.device_label, 0, Qt.AlignVCenter)
        top_row.addStretch(1)

        self.mount_label = QLabel(data.get("mount", ""))
        self.mount_label.setWordWrap(True)
        self.mount_label.setStyleSheet(
            "color: rgba(255,255,255,200); font-size:11px;")

        left_v.addLayout(top_row)
        left_v.addWidget(self.mount_label)

        # --- 中间（容量 + 百分比）
        center = QVBoxLayout()
        self.percent_label = QLabel("0%")
        self.percent_label.setStyleSheet("font-weight:700; color: #FFFFFF;")
        self.size_info = QLabel("")
        self.size_info.setStyleSheet(
            "color: rgba(255,255,255,200); font-size:11px;")

        info_row = QHBoxLayout()
        info_row.addWidget(self.size_info)
        info_row.addStretch(1)
        info_row.addWidget(self.percent_label)

        center.addStretch(1)
        center.addLayout(info_row)
        center.addStretch(1)

        # --- 右侧（读写速率 + 打开按钮）
        right = QVBoxLayout()
        self.read_label = QLabel("R: 0 KB/s", self)
        self.write_label = QLabel("W: 0 KB/s", self)
        self.read_label.setStyleSheet(
            "color: rgba(255,255,255,240); font-weight:700; font-size:12px;")
        self.write_label.setStyleSheet(
            "color: rgba(255,255,255,220); font-weight:600; font-size:11px;")
        right.addWidget(self.read_label, 0, Qt.AlignRight)
        right.addWidget(self.write_label, 0, Qt.AlignRight)

        self.open_btn = ToolButton(FIF.FOLDER, self)
        self.open_btn.setFixedSize(20, 20)
        self.open_btn.setStyleSheet(
            "background: transparent; color: rgba(255,255,255,200);")
        self.open_btn.clicked.connect(self._open_mount)

        right_wrap = QHBoxLayout()
        right_wrap.addLayout(right)
        right_wrap.addWidget(self.open_btn, 0, Qt.AlignRight)

        layout.addLayout(left_v, 4)
        layout.addLayout(center, 5)
        layout.addLayout(right_wrap, 2)

        # 初始化数据
        self.setData(data)

    # ----------- 新增：绘制渐变背景 -----------
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()

        # 根据使用率选择颜色
        main_col, mid_col = self._choose_colors(self._percent)
        stop = max(0.0, min(1.0, self._percent / 100.0))

        grad = QLinearGradient(rect.topLeft(), rect.topRight())
        grad.setColorAt(0, QColor(main_col))
        grad.setColorAt(stop, QColor(mid_col))
        grad.setColorAt(1, QColor(0, 0, 0, 40))

        painter.setBrush(QBrush(grad))
        painter.setPen(QPen(QColor(255, 255, 255, 20), 1))
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 10, 10)

        painter.end()
        super().paintEvent(event)

    # ----------- 配色函数 -----------
    def _choose_colors(self, percent: int):
        if percent < 60:
            return "#27ae60", "#2ecc71"
        elif percent < 85:
            return "#f39c12", "#f1c40f"
        else:
            return "#e74c3c", "#c0392b"

    def _open_mount(self):
        mount = self.mount_label.toolTip() or self.mount_label.text()
        if self.open_callback:
            self.open_callback(mount)

    def setData(self, data: dict):
        device = data.get("device", self.device_label.text())
        mount = data.get("mount", self.mount_label.toolTip()
                         or self.mount_label.text())
        used_percent = data.get("used_percent", None)
        size_kb = data.get("size_kb", None)
        used_kb = data.get("used_kb", None)
        avail_kb = data.get("avail_kb", None)
        r = data.get("read_kbps", 0)
        w = data.get("write_kbps", 0)

        self.device_label.setText(device)
        if mount is None:
            mount = ""
        self.mount_label.setText(mount)
        self.mount_label.setToolTip(mount)

        # normalize percent
        p = 0
        if used_percent is not None:
            try:
                if isinstance(used_percent, str) and used_percent.endswith("%"):
                    p = int(used_percent.rstrip("%"))
                else:
                    p = int(float(used_percent))
            except Exception:
                p = 0
        p = max(0, min(100, p))
        self._percent = p
        self.percent_label.setText(f"{p}%")

        # size info (human readable) if present
        if all(v is not None for v in (size_kb, used_kb, avail_kb)):
            try:
                def hr(kb):
                    if kb >= 1024*1024:
                        return f"{kb/1024/1024:.1f}G"
                    if kb >= 1024:
                        return f"{kb/1024:.1f}M"
                    return f"{kb}K"
                self.size_info.setText(f"{hr(used_kb)}/{hr(size_kb)} used")
            except Exception:
                self.size_info.setText("")
        else:
            self.size_info.setText("")

        # R/W text
        try:
            self.read_label.setText(f"R: {float(r):.1f} KB/s")
            self.write_label.setText(f"W: {float(w):.1f} KB/s")
        except Exception:
            self.read_label.setText(f"R: {r} KB/s")
            self.write_label.setText(f"W: {w} KB/s")

        # update card background (full-card fill)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()
        main_col, mid_col = self._choose_colors(self._percent)
        stop = max(0.0, min(1.0, self._percent / 100.0))

        grad = QLinearGradient(rect.topLeft(), rect.topRight())
        grad.setColorAt(0, QColor(main_col))
        grad.setColorAt(stop, QColor(mid_col))
        grad.setColorAt(min(stop + 0.001, 1.0), QColor(0, 0, 0, 40))
        grad.setColorAt(1, QColor(0, 0, 0, 40))

        painter.setBrush(QBrush(grad))
        painter.setPen(QPen(QColor(255, 255, 255, 20), 1))
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 10, 10)

        super().paintEvent(event)


class DiskMonitor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.disk_items = {}
        main = QVBoxLayout(self)
        main.setContentsMargins(8, 8, 8, 8)
        main.setSpacing(8)

        header = QHBoxLayout()
        header.addStretch(1)
        main.addLayout(header)

        # use qfluentwidgets ScrollArea (you used QS_SCROLL)
        from qfluentwidgets import ScrollArea as QS_SCROLL
        self.scroll = QS_SCROLL(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)

        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(10)
        self.container_layout.setAlignment(
            Qt.AlignTop)  # important: top-align children

        self.scroll.setWidget(self.container)
        main.addWidget(self.scroll)

        # optional demo timer left out

    def add_disk_item(self, disk_id: str, data: dict):
        if disk_id in self.disk_items:
            self.update_disk_item(disk_id, data)
            return
        card = FillDiskCard(
            disk_id, data, parent=self.container, open_callback=self._on_open)
        # ensure card objectName is set (FillDiskCard already does it)
        self.container_layout.insertWidget(0, card)
        self.disk_items[disk_id] = card
        # no stretch widget added: cards keep their minimum height

    def update_disk_item(self, disk_id: str, data: dict):
        card = self.disk_items.get(disk_id)
        if not card:
            self.add_disk_item(disk_id, data)
            return
        card.setData(data)

    def remove_disk_item(self, disk_id: str):
        card = self.disk_items.pop(disk_id, None)
        if card:
            card.hide()
            card.deleteLater()

    def _on_open(self, mount: str):
        print("open mount:", mount)
