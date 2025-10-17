from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QVBoxLayout, QLabel, QHBoxLayout, QFrame
from qfluentwidgets import CardWidget, ComboBox
import pyqtgraph as pg


class NetMonitor(CardWidget):
    clicked = pyqtSignal()
    interface_changed = pyqtSignal(str)  # 网卡切换信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("netMonitor")
        self.setMaximumHeight(140)
        self.init_interface = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        self._create_interface_selector(layout)

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setBackground(None)
        self.plot_widget.setAttribute(Qt.WA_TranslucentBackground, True)
        self.plot_widget.setStyleSheet(
            "background: transparent; border: none;")
        self.plot_widget.setYRange(0, 1000)
        self.plot_widget.setXRange(0, 50)

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

        self._create_speed_labels(layout)

        self.upload_data, self.download_data = [], []
        self.max_points = 50
        self.current_interface = ""

        # 存储所有网卡的数据
        self.all_interfaces_data = {}

        self.auto_adjust_enabled = True
        self.y_margin_factor = 1.2
        self.min_y_range = 100
        self.max_y_range = 1000000

    def _create_interface_selector(self, parent_layout):
        """创建网卡选择器"""
        interface_layout = QHBoxLayout()

        interface_label = QLabel("网卡:")
        interface_label.setStyleSheet("color: gray; font-size: 12px;")
        interface_layout.addWidget(interface_label)

        self.interface_combo = ComboBox()
        self.interface_combo.setMinimumWidth(150)
        self.interface_combo.currentTextChanged.connect(
            self._on_interface_changed)
        interface_layout.addWidget(self.interface_combo)

        interface_layout.addStretch()
        parent_layout.addLayout(interface_layout)

    def _create_speed_labels(self, parent_layout):
        """创建速率显示标签"""
        label_layout = QHBoxLayout()

        upload_container = QFrame()
        upload_layout = QHBoxLayout(upload_container)
        upload_layout.setContentsMargins(5, 2, 5, 2)
        upload_layout.setSpacing(5)

        upload_icon = QLabel("↑")
        upload_icon.setStyleSheet("color:#e67e22; font-weight:bold;")
        self.upload_label = QLabel("0 KB/s")
        self.upload_label.setStyleSheet(
            "color:#e67e22; font-weight:bold; font-size: 12px;")

        upload_layout.addWidget(upload_icon)
        upload_layout.addWidget(self.upload_label)
        upload_container.setStyleSheet(
            "background-color: rgba(230, 126, 34, 0.1); border-radius: 8px;")

        download_container = QFrame()
        download_layout = QHBoxLayout(download_container)
        download_layout.setContentsMargins(5, 2, 5, 2)
        download_layout.setSpacing(5)

        download_icon = QLabel("↓")
        download_icon.setStyleSheet("color:#27ae60; font-weight:bold;")
        self.download_label = QLabel("0 KB/s")
        self.download_label.setStyleSheet(
            "color:#27ae60; font-weight:bold; font-size: 12px;")

        download_layout.addWidget(download_icon)
        download_layout.addWidget(self.download_label)
        download_container.setStyleSheet(
            "background-color: rgba(39, 174, 96, 0.1); border-radius: 8px;")

        label_layout.addWidget(upload_container)
        label_layout.addStretch()
        label_layout.addWidget(download_container)
        parent_layout.addLayout(label_layout)

    def initialize_interfaces(self, interfaces):
        """
        初始化设置网卡接口
        在显示速度前调用此方法设置可用的网卡

        Args:
            interfaces: 网卡名称列表，如 ["eth0", "wlan0", "ens33"]
        """
        print(f"初始化网卡: {interfaces}")

        try:
            interfaces = list(interfaces)
        except:
            interfaces = ["eth0"]

        # 清空现有网卡和数据
        self.interface_combo.clear()
        self.all_interfaces_data.clear()

        if interfaces:
            self.interface_combo.addItems(interfaces)
            self.interface_combo.setCurrentIndex(0)
            self.current_interface = interfaces[0]

            # 为每个网卡初始化独立的数据存储
            for interface in interfaces:
                self.all_interfaces_data[interface] = {
                    'upload_data': [],  # 每个网卡都有自己独立的列表
                    'download_data': []  # 每个网卡都有自己独立的列表
                }

            # 初始化当前网卡的数据引用（指向独立的数据列表）
            if self.current_interface in self.all_interfaces_data:
                self.upload_data = self.all_interfaces_data[self.current_interface]['upload_data']
                self.download_data = self.all_interfaces_data[self.current_interface]['download_data']
        self.init_interface = True
        return len(interfaces) > 0

    def _on_interface_changed(self, interface_name):
        """网卡切换处理"""
        if interface_name and interface_name in self.all_interfaces_data:
            # 直接切换到新网卡的数据（数据已经在 all_interfaces_data 中独立存储）
            self.current_interface = interface_name
            self.upload_data = self.all_interfaces_data[interface_name]['upload_data']
            self.download_data = self.all_interfaces_data[interface_name]['download_data']

            # 更新图表
            x = list(range(len(self.upload_data)))
            self.upload_curve.setData(x, self.upload_data)
            self.download_curve.setData(x, self.download_data)

            # 自动调整Y轴范围
            self._auto_adjust_y_range()

            # 更新标签显示最新速度
            if self.upload_data:
                latest_upload = self.upload_data[-1]
                latest_download = self.download_data[-1] if self.download_data else 0
                self.upload_label.setText(
                    f"{self.format_speed(latest_upload)}")
                self.download_label.setText(
                    f"{self.format_speed(latest_download)}")
            else:
                self.upload_label.setText("0 KB/s")
                self.download_label.setText("0 KB/s")

            self.interface_changed.emit(interface_name)

    def _auto_adjust_y_range(self):
        """自动调整Y轴范围到最佳比例"""
        if not self.auto_adjust_enabled or not self.upload_data:
            return

        max_upload = max(self.upload_data) if self.upload_data else 0
        max_download = max(self.download_data) if self.download_data else 0
        max_speed = max(max_upload, max_download)

        if max_speed == 0:
            self.plot_widget.setYRange(0, 1000)
            return

        new_max = max_speed * self.y_margin_factor
        new_max = max(self.min_y_range, min(new_max, self.max_y_range))
        self.plot_widget.setYRange(0, new_max)

    def update_speed(self, upload_kbps: float, download_kbps: float, interface_name=None):
        """
        更新实时速度数据

        Args:
            upload_kbps: 上传速度 (KB/s)
            download_kbps: 下载速度 (KB/s)
            interface_name: 网卡名称，如果为None则使用当前选中的网卡
        """
        # 确定目标网卡
        target_interface = interface_name if interface_name else self.current_interface

        # 如果网卡不存在，忽略更新
        if target_interface not in self.all_interfaces_data:
            print(f"警告: 网卡 '{target_interface}' 未初始化")
            return

        # 获取目标网卡的数据
        target_upload_data = self.all_interfaces_data[target_interface]['upload_data']
        target_download_data = self.all_interfaces_data[target_interface]['download_data']

        # 更新数据
        target_upload_data.append(upload_kbps)
        target_download_data.append(download_kbps)

        if len(target_upload_data) > self.max_points:
            target_upload_data.pop(0)
            target_download_data.pop(0)

        # 如果是当前选中的网卡，更新显示
        if target_interface == self.current_interface:
            x = list(range(len(target_upload_data)))
            self.upload_curve.setData(x, target_upload_data)
            self.download_curve.setData(x, target_download_data)

            # 更新标签
            self.upload_label.setText(f"{self.format_speed(upload_kbps)}")
            self.download_label.setText(f"{self.format_speed(download_kbps)}")

            # 自动调整Y轴范围
            self._auto_adjust_y_range()

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

    def get_current_interface(self) -> str:
        """获取当前选中的网卡"""
        return self.current_interface

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)

    def set_auto_adjust(self, enabled: bool):
        """设置是否启用自动调整比例"""
        self.auto_adjust_enabled = enabled

    def set_y_margin(self, margin_factor: float):
        """设置Y轴边距系数"""
        self.y_margin_factor = margin_factor

    def get_interface_data(self, interface_name):
        """获取指定网卡的数据（用于调试）"""
        if interface_name in self.all_interfaces_data:
            return {
                'upload': self.all_interfaces_data[interface_name]['upload_data'],
                'download': self.all_interfaces_data[interface_name]['download_data']
            }
        return None
