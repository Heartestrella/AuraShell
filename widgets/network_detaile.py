import random
import re
from PyQt5.QtCore import Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel, pyqtSignal
from PyQt5.QtWidgets import QVBoxLayout, QWidget, QHeaderView
from qfluentwidgets import TableView,  FluentIcon, RoundMenu, LineEdit, Action


class NetConnectionProxyModel(QSortFilterProxyModel):
    def lessThan(self, left, right):
        column = left.column()

        left_data = left.data(Qt.DisplayRole)
        right_data = right.data(Qt.DisplayRole)

        if left_data is None:
            left_data = ""
        if right_data is None:
            right_data = ""

        if column in [1, 2, 4, 5]:  # PID, Local Port, Remote Port, Connections
            try:
                left_num = float(str(left_data)) if str(
                    left_data).strip() else 0
                right_num = float(str(right_data)) if str(
                    right_data).strip() else 0
                return left_num < right_num
            except (ValueError, TypeError):
                pass

        elif column == 6:
            try:
                left_upload = self._extract_kb_value(str(left_data))
                right_upload = self._extract_kb_value(str(right_data))
                return left_upload < right_upload
            except (ValueError, TypeError):
                pass

        left_str = str(left_data).lower()
        right_str = str(right_data).lower()
        return left_str < right_str

    def _extract_kb_value(self, text):
        """从上传/下载字符串中提取数字值"""
        if not text:
            return 0

        match = re.search(r'(\d+)\s*KB', str(text))
        if match:
            return float(match.group(1))
        return 0


class NetConnectionModel(QAbstractTableModel):
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
            # 返回显示文本
            if col < len(self._data[row]):
                return str(self._data[row][col])
            return ""

        elif role == Qt.TextAlignmentRole:
            # 数字列右对齐，其他左对齐
            if col in [1, 2, 4, 5]:  # PID, Local Port, Remote Port, Connections
                return Qt.AlignRight | Qt.AlignVCenter
            return Qt.AlignLeft | Qt.AlignVCenter

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._headers[section]
        return None

    def updateData(self, new_data):
        self.beginResetModel()
        # 转换 dict list 到 list of lists
        converted_data = []
        for item in new_data:
            row = [
                item.get("Process Name", ""),
                item.get("PID", 0),
                item.get("Local Port", 0),
                item.get("Local IP", ""),
                item.get("Remote Port", 0),
                item.get("Connections", 0),
                item.get("Upload/Download", "")
            ]
            converted_data.append(row)
        self._data = converted_data
        self.endResetModel()


class NetProcessMonitor(QWidget):
    # pid
    kill_process = pyqtSignal(int)
    dataRefreshed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr("Process Network Connections Monitor"))
        self.resize(1000, 600)

        self.headers = [
            self.tr("Process Name"),
            self.tr("PID"),
            self.tr("Local Port"),
            self.tr("Local IP"),
            self.tr("Remote Port"),
            self.tr("Connections"),
            self.tr("Upload/Download")
        ]

        self.initUI()

    def initUI(self):
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        control_layout = QVBoxLayout()
        control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.setSpacing(5)

        self.filter_input = LineEdit(self)
        self.filter_input.setPlaceholderText(
            self.tr("Filter by process name or PID..."))
        self.filter_input.textChanged.connect(self.filterData)
        self.filter_input.setStyleSheet("""
            LineEdit {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 20px;
            color: rgba(255, 255, 255, 0.9);
            padding: 12px 16px;
            font-size: 13px;
            min-height: 20px;
        }
        LineEdit:focus {
            background: rgba(255, 255, 255, 0.15);
            border: 1px solid rgba(0, 120, 212, 0.5);
            color: white;
            box-shadow: 0 0 20px rgba(0, 120, 212, 0.2);
        }
        LineEdit::placeholder {
            color: rgba(255, 255, 255, 0.5);
        }
        """)
        control_layout.addWidget(self.filter_input)

        self.source_model = NetConnectionModel(self.headers)
        self.proxy_model = NetConnectionProxyModel(self)
        self.proxy_model.setSourceModel(self.source_model)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy_model.setFilterKeyColumn(-1)

        self.table_view = TableView(self)
        self.table_view.setModel(self.proxy_model)

        self.table_view.setAttribute(Qt.WA_TranslucentBackground, True)
        self.table_view.viewport().setAttribute(Qt.WA_TranslucentBackground, True)

        self.table_view.setStyleSheet("""
            TableView {
                background: transparent;
                border: none;
                gridline-color: rgba(255, 255, 255, 0.1);
                color: rgba(255, 255, 255, 0.9);
                font-family: 'Consolas', 'SF Mono', monospace;
                font-size: 12px;
                selection-background-color: rgba(0, 120, 212, 0.3);
                selection-color: white;
                alternate-background-color: transparent;
                show-decoration-selected: 1;
            }
            TableView::item {
                padding: 8px 8px;
                margin: 2px 0;
                border: none;
                color: rgba(255, 255, 255, 0.8);
                background: transparent;
            }
            TableView::item:selected {
                background: rgba(0, 120, 212, 0.2);
                color: white;
                border: none;
                margin: 2px 0;
            }
            TableView::item:hover {
                background: rgba(255, 255, 255, 0.05);
                color: rgba(255, 255, 255, 0.9);
                margin: 2px 0;
            }
            TableView::pane {
                border: none;
                background: transparent;
                margin: 0;
            }
            QHeaderView::section {
                background: transparent;
                border: none;
                padding: 10px 8px;
                color: rgba(255, 255, 255, 0.9);
                font-weight: 600;
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                margin: 0;
            }
        """)

        self.table_view.setBorderVisible(False)
        self.table_view.setBorderRadius(0)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table_view.setAlternatingRowColors(False)
        self.table_view.setSortingEnabled(True)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.verticalHeader().setDefaultSectionSize(0)

        header = self.table_view.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.resizeSection(1, 80)
        header.resizeSection(2, 100)
        header.resizeSection(3, 120)
        header.resizeSection(4, 100)
        header.resizeSection(5, 100)
        header.resizeSection(6, 200)

        layout.addLayout(control_layout)
        layout.addWidget(self.table_view, 1)

        self.setStyleSheet("background: transparent;")
        self.table_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(
            self.showContextMenu)

    def filterData(self, text):
        self.proxy_model.setFilterRegExp(text)

    def updateProcessData(self, process_data):
        self.source_model.updateData(
            self.convert_connections_for_api(process_data))
        self.dataRefreshed.emit()

    def convert_connections_for_api(self, connections):
        api_data = []
        for conn in connections:
            api_item = {
                "Process Name": conn.get("name", ""),
                "PID": conn.get("pid", 0),
                "Local Port": conn.get("local_port", 0),
                "Local IP": conn.get("local_ip", ""),
                "Remote Port": conn.get("remote_port", 0),
                "Connections": conn.get("connections", 0),
                "Upload/Download": f"{conn.get('upload_kbps', 0)} KB / {conn.get('download_kbps', 0)} KB"
            }
            api_data.append(api_item)
        return api_data

    def generateSampleData(self):
        processes = [
            "chrome.exe", "firefox.exe", "explorer.exe", "svchost.exe",
            "python.exe", "code.exe", "steam.exe", "discord.exe",
            "spotify.exe", "notepad.exe", "taskmgr.exe", "msedge.exe"
        ]

        sample_data = []
        for i in range(20):
            process = random.choice(processes)
            pid = random.randint(1000, 8000)
            local_port = random.randint(1000, 65535)
            remote_port = random.randint(1000, 65535)
            connections = random.randint(1, 50)

            # 随机生成上传下载数据
            upload = random.randint(100, 10000)
            download = random.randint(100, 50000)
            upload_download = f"{upload} KB / {download} KB"

            # 随机IP地址
            local_ip = f"192.168.1.{random.randint(1, 254)}"
            remote_ip = f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}"

            sample_data.append({
                "Process Name": process,
                "PID": pid,
                "Local Port": local_port,
                "Local IP": local_ip,
                "Remote Port": remote_port,
                "Connections": connections,
                "Upload/Download": upload_download
            })

        self.source_model.updateData(sample_data)

    def filterData(self, text):
        """根据输入文本过滤数据"""
        self.proxy_model.setFilterRegExp(text)

    def sortData(self, text):
        col = -1
        order = Qt.AscendingOrder

        if text == self.tr("Sort by PID"):
            col = 1
        elif text == self.tr("Sort by Process Name"):
            col = 0
        elif text == self.tr("Sort by Connections"):
            col = 5
            order = Qt.DescendingOrder

        if col >= 0:
            self.proxy_model.sort(col, order)

    def convert_connections_for_api(self, connections):
        api_data = []
        for conn in connections:
            api_item = {
                "Process Name": conn.get("name", ""),
                "PID": conn.get("pid", 0),
                "Local Port": conn.get("local_port", 0),
                "Local IP": conn.get("local_ip", ""),
                "Remote Port": conn.get("remote_port", 0),
                "Connections": conn.get("connections", 0),
                "Upload/Download": f"{conn.get('upload_kbps', 0)} KB / {conn.get('download_kbps', 0)} KB"
            }
            api_data.append(api_item)
        return api_data

    def updateProcessData(self, process_data):
        """
        提供给外部调用的接口，用于更新进程数据

        Args:
            process_data: 字典列表，每个字典包含进程信息
                Example:
                [
                    {
                        "Process Name": "chrome.exe",
                        "PID": 1234,
                        "Local Port": 8080,
                        "Local IP": "192.168.1.10",
                        "Remote Port": 443,
                        "Connections": 5,
                        "Upload/Download": "100 KB / 500 KB"
                    },
                    ...
                ]
        """
        self.source_model.updateData(
            self.convert_connections_for_api(process_data))
        self.dataRefreshed.emit()

    def showContextMenu(self, position):
        index = self.table_view.indexAt(position)
        if not index.isValid():
            return

        source_index = self.proxy_model.mapToSource(index)
        row_data = self.source_model._data[source_index.row()]
        row_info = {
            "Process Name": row_data[0] if len(row_data) > 0 else "",
            "PID": row_data[1] if len(row_data) > 1 else 0,
            "Local Port": row_data[2] if len(row_data) > 2 else 0,
            "Local IP": row_data[3] if len(row_data) > 3 else "",
            "Remote Port": row_data[4] if len(row_data) > 4 else 0,
            "Connections": row_data[5] if len(row_data) > 5 else 0,
            "Upload/Download": row_data[6] if len(row_data) > 6 else ""
        }

        context_menu = RoundMenu(parent=self)

        kill_action = Action(FluentIcon.CLOSE, self.tr("Kill Process"), )
        kill_action.triggered.connect(
            lambda: self.kill_process.emit(int(row_info["PID"])))
        context_menu.addAction(kill_action)

        context_menu.addSeparator()

        copy_menu = RoundMenu(self.tr("Copy info"))
        copy_menu.setIcon(FluentIcon.COPY)

        # Copy Process Name
        copy_name = Action(self.tr("Copy Process Name"), self)
        copy_name.triggered.connect(
            lambda checked, text=row_info["Process Name"]: self.copyToClipboard(text))
        copy_menu.addAction(copy_name)

        # Copy PID
        copy_pid = Action(self.tr("Copy PID"), self)
        copy_pid.triggered.connect(
            lambda checked: self.copyToClipboard(str(row_info["PID"])))
        copy_menu.addAction(copy_pid)

        # Copy Local Port
        copy_local_port = Action(self.tr("Copy Local Port"), self)
        copy_local_port.triggered.connect(
            lambda checked: self.copyToClipboard(str(row_info["Local Port"])))
        copy_menu.addAction(copy_local_port)

        # Copy Local IP
        copy_local_ip = Action(self.tr("Copy Local IP"), self)
        copy_local_ip.triggered.connect(
            lambda checked: self.copyToClipboard(row_info["Local IP"]))
        copy_menu.addAction(copy_local_ip)

        # Copy Remote Port
        copy_remote_port = Action(self.tr("Copy Remote Port"), self)
        copy_remote_port.triggered.connect(
            lambda checked: self.copyToClipboard(str(row_info["Remote Port"])))
        copy_menu.addAction(copy_remote_port)

        context_menu.addMenu(copy_menu)
        context_menu.exec_(self.table_view.mapToGlobal(position))

    def copyToClipboard(self, text):
        from PyQt5.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(str(text))
