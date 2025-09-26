import random
from PyQt5.QtCore import Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel
from PyQt5.QtWidgets import QVBoxLayout, QWidget, QHeaderView
from qfluentwidgets import TableView, LineEdit


class ProcessTableModel(QAbstractTableModel):
    def __init__(self, headers, data=None):
        super().__init__()
        self._headers = headers
        self._data = data or []  # list of lists

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return len(self._headers)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row, col = index.row(), index.column()
        if role == Qt.DisplayRole:
            if col < len(self._data[row]):
                return str(self._data[row][col])
            return ""
        elif role == Qt.TextAlignmentRole:
            # 数字右对齐
            if col in [1, 3, 4]:  # PID, CPU%, MEM%
                return Qt.AlignRight | Qt.AlignVCenter
            return Qt.AlignLeft | Qt.AlignVCenter
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._headers[section]
        return None

    def updateData(self, new_data):
        """更新表格数据"""
        self.beginResetModel()
        converted = []
        for item in new_data:
            row = [
                item.get("user", ""),
                item.get("pid", 0),
                item.get("name", ""),
                item.get("cpu", 0.0),
                item.get("mem", 0.0),
                item.get("command", "")
            ]
            converted.append(row)
        self._data = converted
        self.endResetModel()


class ProcessMonitor(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Process Info Monitor Demo")
        self.resize(1200, 600)

        self.headers = [
            "User", "PID", "Process Name", "CPU %", "Mem %", "Command"
        ]
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 搜索框
        self.filter_input = LineEdit(self)
        self.filter_input.setPlaceholderText("Filter by any field...")
        self.filter_input.textChanged.connect(self.filterData)
        layout.addWidget(self.filter_input)

        # 模型
        self.source_model = ProcessTableModel(self.headers)
        self.proxy_model = QSortFilterProxyModel(self)
        self.proxy_model.setSourceModel(self.source_model)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy_model.setFilterKeyColumn(-1)  # 所有列都可过滤

        # 表格
        self.table_view = TableView(self)
        self.table_view.setModel(self.proxy_model)
        self.table_view.setSortingEnabled(True)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table_view.horizontalHeader().setStretchLastSection(True)

        # 设置列宽
        header = self.table_view.horizontalHeader()
        header.resizeSection(0, 100)  # User
        header.resizeSection(1, 80)   # PID
        header.resizeSection(2, 150)  # Process Name
        header.resizeSection(3, 80)   # CPU %
        header.resizeSection(4, 80)   # Mem %
        header.resizeSection(5, 700)  # Command

        layout.addWidget(self.table_view, 1)

    def filterData(self, text):
        self.proxy_model.setFilterRegExp(text)

    def updateProcessData(self, process_data):
        """外部接口：更新进程信息"""
        self.source_model.updateData(process_data)

    def generateSampleData(self):
        """生成模拟数据"""
        users = ["root", "user1", "mysql", "nginx"]
        procs = ["python3", "nginx", "mysqld",
                 "chrome", "firefox", "sshd", "java"]

        sample = []
        for i in range(30):
            item = {
                "user": random.choice(users),
                "pid": random.randint(100, 5000),
                "name": random.choice(procs),
                "cpu": round(random.uniform(0, 50), 1),
                "mem": round(random.uniform(0, 10), 1),
                "command": f"/usr/bin/{random.choice(procs)} --option {random.randint(1, 10)}"
            }
            sample.append(item)
        self.updateProcessData(sample)
