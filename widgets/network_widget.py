from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QVBoxLayout, QLabel, QHBoxLayout
from qfluentwidgets import CardWidget
import pyqtgraph as pg


class NetMonitor(CardWidget):
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("netMonitor")
        self.setMaximumHeight(120)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # 创建绘图区域
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setBackground(None)
        self.plot_widget.setAttribute(Qt.WA_TranslucentBackground, True)
        self.plot_widget.setStyleSheet(
            "background: transparent; border: none;")
        self.plot_widget.setYRange(0, 25000)
        self.plot_widget.setXRange(0, 50)

        # 隐藏坐标值（保留轴线）
        for axis in ("bottom", "left", "right", "top"):
            ax = self.plot_widget.getAxis(axis)
            ax.setTicks([])
            ax.setStyle(showValues=False)

        self.plot_widget.setMenuEnabled(False)
        self.plot_widget.setMouseEnabled(x=False, y=False)

        self.upload_curve = self.plot_widget.plot(
            pen=pg.mkPen("#e67e22", width=2)
        )
        self.download_curve = self.plot_widget.plot(
            pen=pg.mkPen("#27ae60", width=2)
        )

        layout.addWidget(self.plot_widget)

        # ✅ 底部增加速率标签
        label_layout = QHBoxLayout()
        self.upload_label = QLabel("↑ 0 KB/s")
        self.download_label = QLabel("↓ 0 KB/s")

        # 样式（你可以改颜色）
        self.upload_label.setStyleSheet("color:#e67e22; font-weight:bold;")
        self.download_label.setStyleSheet("color:#27ae60; font-weight:bold;")

        label_layout.addWidget(self.upload_label)
        label_layout.addStretch()
        label_layout.addWidget(self.download_label)
        layout.addLayout(label_layout)

        self.upload_data, self.download_data = [], []
        self.max_points = 50

    def update_speed(self, upload_kbps: float, download_kbps: float):
        """
        外部 API 调用：更新上传和下载速率 (单位 KB/s)
        自动刷新曲线和标签
        """
        self.upload_data.append(upload_kbps)
        self.download_data.append(download_kbps)

        if len(self.upload_data) > self.max_points:
            self.upload_data.pop(0)
            self.download_data.pop(0)

        x = list(range(len(self.upload_data)))
        if self.upload_curve:
            self.upload_curve.setData(x, self.upload_data)
            self.download_curve.setData(x, self.download_data)

            # 更新标签
            self.upload_label.setText(f"↑ {self.format_speed(upload_kbps)}")
            self.download_label.setText(
                f"↓ {self.format_speed(download_kbps)}")

            # 强制刷新绘图
            self.plot_widget.update()
            self.plot_widget.repaint()

    def format_speed(self, value: float) -> str:
        """根据 KB/s 数值自动选择单位显示"""
        if value >= 1_000_000:  # GB/s
            return f"{value / 1_000_000:.2f} GB/s"
        elif value >= 1_000:  # MB/s
            return f"{value / 1_000:.2f} MB/s"
        else:  # KB/s
            return f"{value:.1f} KB/s"

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)
