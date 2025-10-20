import time
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QProgressBar, QFrame, QSizePolicy
)
from qfluentwidgets import setTheme, Theme

# ---------- Helper utils ----------


def nice_speed_from_kb(kbytes: float) -> str:
    """KB/s -> human readable string"""
    if kbytes is None:
        return "0K"
    if kbytes >= 1024 * 1024:
        return f"{kbytes/1024/1024:.1f}G"
    if kbytes >= 1024:
        return f"{kbytes/1024:.1f}M"
    return f"{kbytes:.0f}K"


def small_dot(color: str) -> QLabel:
    lbl = QLabel()
    lbl.setFixedSize(10, 10)
    lbl.setStyleSheet(f"background:{color}; border-radius:5px;")
    return lbl


def vline() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.VLine)
    line.setFrameShadow(QFrame.Plain)
    line.setStyleSheet("color:#2f2f2f;")
    line.setFixedHeight(18)
    return line

# ---------- Thin compact progress bar ----------


class ThinProgressBar(QProgressBar):
    def __init__(self, color="#4CAF50", width=90, height=8):
        super().__init__()
        self.setMaximum(100)
        self.setValue(0)
        self.setTextVisible(False)
        self.setFixedSize(width, height)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._base_style = """
            QProgressBar{
                border-radius:4px;
                background: #232323;
            }
            QProgressBar::chunk{
                border-radius:4px;
                background: %s;
            }
        """
        self.setStyleSheet(self._base_style % color)

    def set_chunk_color(self, color: str):
        self.setStyleSheet(self._base_style % color)

# ---------- Main monitor bar ----------


class MonitorBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        setTheme(Theme.DARK)
        self.setFixedHeight(36)
        # self.setStyleSheet(
        #     "background:#141414; border-radius:6px; padding:6px;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(12)

        self._font_family = "Segoe UI"
        # Uptime & load
        self.uptime_lbl = QLabel("运行: -")
        self.uptime_lbl.setStyleSheet("color:#cfcfcf; font-size:12px;")
        self.load_lbl = QLabel("Load: - - -")
        self.load_lbl.setStyleSheet("color:#9fc8a8; font-size:12px;")

        # CPU
        self.cpu_dot = small_dot("#00bcd4")
        self.cpu_label = QLabel("CPU")
        self.cpu_label.setStyleSheet("color:#cfcfcf; font-size:12px;")
        self.cpu_bar = ThinProgressBar(color="#00bcd4", width=90)
        self.cpu_text = QLabel("-")
        self.cpu_text.setStyleSheet(
            "color:#cfcfcf; font-size:12px; min-width:44px;")

        # RAM
        self.ram_dot = small_dot("#ff9800")
        self.ram_label = QLabel("内存")
        self.ram_label.setStyleSheet("color:#cfcfcf; font-size:12px;")
        self.ram_bar = ThinProgressBar(color="#ff9800", width=90)
        self.ram_text = QLabel("-")
        self.ram_text.setStyleSheet(
            "color:#cfcfcf; font-size:12px; min-width:44px;")

        # Disk
        self.disk_dot = small_dot("#4caf50")
        self.disk_label = QLabel("磁盘")
        self.disk_label.setStyleSheet("color:#cfcfcf; font-size:12px;")
        self.disk_bar = ThinProgressBar(color="#4caf50", width=90)
        self.disk_text = QLabel("-")
        self.disk_text.setStyleSheet(
            "color:#cfcfcf; font-size:12px; min-width:44px;")

        # Network
        self.net_dot = small_dot("#9c27b0")
        self.net_label = QLabel("网速")
        self.net_label.setStyleSheet("color:#cfcfcf; font-size:12px;")
        self.net_text = QLabel("- ↑ - ↓")
        self.net_text.setStyleSheet(
            "color:#cfcfcf; font-size:12px; min-width:80px;")

        # Assemble left: uptime + load
        layout.addWidget(self.uptime_lbl)
        layout.addWidget(self.load_lbl)
        layout.addWidget(vline())

        # CPU block
        layout.addWidget(self.cpu_dot)
        layout.addWidget(self.cpu_label)
        layout.addWidget(self.cpu_bar)
        layout.addWidget(self.cpu_text)
        layout.addWidget(vline())

        # RAM block
        layout.addWidget(self.ram_dot)
        layout.addWidget(self.ram_label)
        layout.addWidget(self.ram_bar)
        layout.addWidget(self.ram_text)
        layout.addWidget(vline())

        # Disk block
        layout.addWidget(self.disk_dot)
        layout.addWidget(self.disk_label)
        layout.addWidget(self.disk_bar)
        layout.addWidget(self.disk_text)
        layout.addWidget(vline())

        # Net block
        layout.addWidget(self.net_dot)
        layout.addWidget(self.net_label)
        layout.addWidget(self.net_text)

        layout.addStretch()
        self.setLayout(layout)

        # internal state used when metrics omit fields
        self._start_time = int(time.time())
        # keep last known values (so partial updates work)
        self._last = {
            "uptime_seconds": 0,
            "load": None,
            "cpu_percent": 0.0,
            "ram_percent": 0.0,
            "disk_percent": 0.0,
            "net_up_kbps": 0.0,
            "net_down_kbps": 0.0
        }

    def update_metrics(self, metrics: dict):
        """
        更新 UI 的 API。
        metrics keys:
         - uptime_seconds: int
         - load: sequence of 3 floats
         - cpu_percent: float (0-100)
         - ram_percent: float (0-100)
         - disk_percent: float (0-100)
         - net_up_kbps: float
         - net_down_kbps: float
        任何缺失的字段将保留上次值（或不更新）。
        """
        # merge into last
        for k, v in metrics.items():
            if k in self._last and v is not None:
                self._last[k] = v

        # uptime
        uptime = self._last.get("uptime_seconds") or int(
            time.time() - self._start_time)
        days = uptime // 86400
        hours = (uptime % 86400) // 3600
        mins = (uptime % 3600) // 60
        self.uptime_lbl.setText(f"运行: {days}d {hours}h {mins}m")

        # load
        load = self._last.get("load")
        if isinstance(load, (list, tuple)) and len(load) >= 3:
            la1, la5, la15 = load[0], load[1], load[2]
            self.load_lbl.setText(f"Load: {la1:.2f} {la5:.2f} {la15:.2f}")
        else:
            self.load_lbl.setText("Load: - - -")

        # cpu / ram / disk
        cpu = self._last.get("cpu_percent", 0.0) or 0.0
        ram = self._last.get("ram_percent", 0.0) or 0.0
        disk = self._last.get("disk_percent", 0.0) or 0.0

        self.cpu_text.setText(f"{cpu:.0f}%")
        self.ram_text.setText(f"{ram:.0f}%")
        self.disk_text.setText(f"{disk:.0f}%")

        # net
        up = self._last.get("net_up_kbps", 0.0) or 0.0
        down = self._last.get("net_down_kbps", 0.0) or 0.0
        self.net_text.setText(
            f"{nice_speed_from_kb(up)}↑ {nice_speed_from_kb(down)}↓")

        # colors (richer thresholds)
        cpu_color = "#00bcd4" if cpu < 50 else (
            "#FFC107" if cpu < 75 else "#F44336")
        ram_color = "#ff9800" if ram < 75 else "#F44336"
        disk_color = "#4CAF50" if disk < 70 else (
            "#FFC107" if disk < 90 else "#F44336")

        self.cpu_bar.set_chunk_color(cpu_color)
        self.ram_bar.set_chunk_color(ram_color)
        self.disk_bar.set_chunk_color(disk_color)

        self.cpu_bar.setValue(int(max(0, min(100, cpu))))
        self.ram_bar.setValue(int(max(0, min(100, ram))))
        self.disk_bar.setValue(int(max(0, min(100, disk))))

        # dynamic dot colors (reflect "health" quickly)
        self.cpu_dot.setStyleSheet(
            f"background:{cpu_color}; border-radius:5px;")
        self.ram_dot.setStyleSheet(
            f"background:{ram_color}; border-radius:5px;")
        self.disk_dot.setStyleSheet(
            f"background:{disk_color}; border-radius:5px;")
        # net dot purple stays constant for clarity

    def set_font_family(self, font_family: str):
        if font_family and font_family != self._font_family:
            self._font_family = font_family
            self.update()
