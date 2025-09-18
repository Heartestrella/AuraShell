from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor, QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import QFrame, QVBoxLayout, QSizePolicy
from qfluentwidgets import TableView, isDarkTheme
from widgets.network_widget import NetMonitor


class Tasks(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.NoFrame)
        self.setStyleSheet("background: transparent;")
        self.setMinimumHeight(100)
        self.netmonitor = NetMonitor()
        self.netmonitor.setMinimumHeight(80)
        self.netmonitor.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.netmonitor.setStyleSheet("""
                QFrame#netmonitor
                {
                    background-color: rgba(220, 220, 220, 0.06);
                    border: 1px solid rgba(0,0,0,0.06);
                    border-radius: 6px;
                }
            """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # ✅ 使用 QFluentWidgets 的 TableView
        self.table = TableView(self)
        self.model = QStandardItemModel(0, 3, self)
        self.model.setHorizontalHeaderLabels(["RAM", "CPU", "NAME"])
        self.table.setModel(self.model)

        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(self.table.NoSelection)
        self.table.setEditTriggers(self.table.NoEditTriggers)
        self.table.setAlternatingRowColors(False)

        # 样式
        self.table.setShowGrid(False)
        self.table.setCornerButtonEnabled(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setStyleSheet("""
            TableView {
                border: none;
                background: transparent;
            }
            TableView::item {
                padding: 4px;
            }
        """)

        # 水平表头也可以透明
        self.table.horizontalHeader().setStyleSheet("""
            QHeaderView::section {
                background: transparent;
                border: none;
                color: white; /* 或者根据主题切换 */
                font-weight: bold;
                padding: 4px;
            }
        """)
        layout.addWidget(self.table)
        layout.addWidget(self.netmonitor)
        self.text_color = "#ffffff" if isDarkTheme() else "#000000"

    def set_text_color(self, color_hex: str):
        self.text_color = color_hex

    def add_row(self, mem, cpu, cmd):
        # 如果行数超过5，清空
        if self.model.rowCount() >= 4:
            self.model.removeRows(0, self.model.rowCount())

        items = []

        # RAM
        mem_item = QStandardItem(str(mem))
        mem_item.setTextAlignment(Qt.AlignCenter)
        mem_item.setFont(self._bold_font())
        mem_item.setForeground(QColor(self.text_color))
        items.append(mem_item)

        # CPU
        cpu_item = QStandardItem(str(cpu))
        cpu_item.setTextAlignment(Qt.AlignCenter)
        cpu_item.setFont(self._bold_font())
        cpu_item.setForeground(QColor(self.text_color))
        items.append(cpu_item)

        # NAME / Command
        cmd_item = QStandardItem(str(cmd))
        cmd_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        cmd_item.setForeground(QColor(self.text_color))
        items.append(cmd_item)

        self.model.appendRow(items)

        # 可选：固定行高
        row_index = self.model.rowCount() - 1
        self.table.setRowHeight(row_index, 32)

    def _bold_font(self):
        font = QFont()
        font.setBold(True)
        return font

    # def set_netmonitor(self, upload, download):
    #     self.netmonitor.update_speed(
    #         upload_kbps=upload, download_kbps=download)
