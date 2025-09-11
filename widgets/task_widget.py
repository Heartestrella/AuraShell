from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QFrame, QVBoxLayout


from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QFrame, QVBoxLayout


class Tasks(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.NoFrame)
        self.setStyleSheet("background: transparent;")
        self.setMinimumHeight(100)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget(0, 3, self)
        self.table.setHorizontalHeaderLabels(["RAM", "CPU", "NAME"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.setAlternatingRowColors(False)
        self.table.setStyleSheet("""
            QTableWidget {
                background: transparent;
                border: none;
                gridline-color: rgba(200,200,200,0.1);
            }
            QTableWidget::item, QTableWidget::item:alternate {
                background: transparent;
                padding: 4px;
            }
            QTableWidget::item:selected {
                background-color: rgba(0,120,215,0.3);
            }
            QHeaderView::section {
                background: transparent;
                color: white;
                font-weight: bold;
                border: none;
                padding: 6px;
            }
        """)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

        # 默认字体颜色
        self.text_color = "#ffffff"

    def set_text_color(self, color_hex: str):
        """设置表格内容字体颜色（不影响表头）"""
        self.text_color = color_hex

    def add_row(self, mem, cpu, cmd):
        # 如果行数超过5，先清空表格
        if self.table.rowCount() >= 5:
            self.table.setRowCount(0)

        row = self.table.rowCount()
        self.table.insertRow(row)

        # 内存列
        mem_item = QTableWidgetItem(str(mem))
        mem_item.setTextAlignment(Qt.AlignCenter)
        mem_item.setFont(self._bold_font())
        mem_item.setForeground(QColor(self.text_color))
        self.table.setItem(row, 0, mem_item)

        # CPU列
        cpu_item = QTableWidgetItem(str(cpu))
        cpu_item.setTextAlignment(Qt.AlignCenter)
        cpu_item.setFont(self._bold_font())
        cpu_item.setForeground(QColor(self.text_color))
        self.table.setItem(row, 1, cpu_item)

        # 命令列
        cmd_item = QTableWidgetItem(str(cmd))
        cmd_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        cmd_item.setForeground(QColor(self.text_color))
        self.table.setItem(row, 2, cmd_item)

        self.table.setRowHeight(row, 26)

    def _bold_font(self):
        font = QFont()
        font.setBold(True)
        return font
