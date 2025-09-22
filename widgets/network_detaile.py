
import random
from PyQt5.QtCore import Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QVBoxLayout, QWidget, QHeaderView
from qfluentwidgets import TableView, setTheme, Theme, PrimaryPushButton, LineEdit, ComboBox


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

        # 移除所有颜色设置，保持透明
        # elif role == Qt.BackgroundRole:
        #     # 交替行颜色 - 已移除
        #     pass

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._headers[section]
        return None

    def updateData(self, new_data):
        """更新表格数据的接口"""
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
    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr("Process Network Connections Monitor"))
        self.resize(1000, 600)

        # 设置主题
        setTheme(Theme.DARK)

        # 定义表头
        self.headers = [
            self.tr("Process Name"),
            self.tr("PID"),
            self.tr("Local Port"),
            self.tr("Local IP"),
            self.tr("Remote Port"),
            self.tr("Connections"),
            self.tr("Upload/Download")
        ]

        # 创建UI
        self.initUI()

        # 生成示例数据
        self.generateSampleData()

    def initUI(self):
        # 设置透明背景
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 创建控制面板
        control_layout = QVBoxLayout()
        control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.setSpacing(5)

        # 搜索框 - 透明样式
        self.filter_input = LineEdit(self)
        self.filter_input.setPlaceholderText(
            self.tr("Filter by process name or PID..."))
        self.filter_input.textChanged.connect(self.filterData)
        self.filter_input.setStyleSheet("""
            LineEdit {
            /* 毛玻璃背景 */
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);           /* 毛玻璃模糊 */
            -webkit-backdrop-filter: blur(10px);   /* WebKit 兼容 */
            
            /* 半透明边框 */
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 20px;                   /* 圆角 */
            
            /* 文字和图标颜色 */
            color: rgba(255, 255, 255, 0.9);
            padding: 12px 16px;                    /* 内边距 */
            font-size: 13px;
            min-height: 20px;
            
            /* 聚焦效果 */
        }
        LineEdit:focus {
            background: rgba(255, 255, 255, 0.15);
            border: 1px solid rgba(0, 120, 212, 0.5);
            color: white;
            box-shadow: 0 0 20px rgba(0, 120, 212, 0.2);  /* 聚焦发光 */
        }
        LineEdit::placeholder {
            color: rgba(255, 255, 255, 0.5);
        }
        
        /* 光标样式 */
        LineEdit QCursor {
            color: rgba(255, 255, 255, 0.7);
        }
        """)
        control_layout.addWidget(self.filter_input)

        # 创建表格视图
        self.source_model = NetConnectionModel(self.headers)
        self.proxy_model = QSortFilterProxyModel(self)
        self.proxy_model.setSourceModel(self.source_model)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy_model.setFilterKeyColumn(-1)  # 过滤所有列

        self.table_view = TableView(self)
        self.table_view.setModel(self.proxy_model)

        # 设置表格为透明
        self.table_view.setAttribute(Qt.WA_TranslucentBackground, True)
        self.table_view.viewport().setAttribute(Qt.WA_TranslucentBackground, True)

        # 表格透明样式
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
        show-decoration-selected: 1;  /* 启用选中装饰 */
    }
    
    /* 关键：设置行间距 */
    TableView::item {
        padding: 8px 8px;           /* 单元格内边距 */
        margin: 2px 0;              /* 行间距：上下各2px */
        border: none;
        color: rgba(255, 255, 255, 0.8);
        background: transparent;    /* 确保透明 */
    }
    
    TableView::item:selected {
        background: rgba(0, 120, 212, 0.2);
        color: white;
        border: none;
        margin: 2px 0;              /* 选中状态也保持间距 */
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
    
    /* 表头样式 */
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

        # 表头透明样式
        self.table_view.horizontalHeader().setStyleSheet("""
            QHeaderView::section {
                background: transparent;
                border: none;
                padding: 8px;
                color: rgba(255, 255, 255, 0.9);
                font-weight: 600;
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            }
            QHeaderView::section:hover {
                background: rgba(255, 255, 255, 0.05);
            }
            QHeaderView::section:selected {
                background: rgba(0, 120, 212, 0.2);
            }
        """)

        # 设置表格属性
        self.table_view.setBorderVisible(False)
        self.table_view.setBorderRadius(0)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table_view.setAlternatingRowColors(False)  # 移除交替颜色
        self.table_view.setSortingEnabled(True)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.verticalHeader().setDefaultSectionSize(0)

        # 设置列宽
        header = self.table_view.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # 进程名自适应
        header.resizeSection(1, 80)   # PID
        header.resizeSection(2, 100)  # 本地端口
        header.resizeSection(3, 120)  # 本地IP
        header.resizeSection(4, 100)  # 远程端口
        header.resizeSection(5, 100)  # 连接数
        header.resizeSection(6, 200)  # 上传/下载

        # 添加到布局
        layout.addLayout(control_layout)
        layout.addWidget(self.table_view, 1)

        # 设置整体布局透明
        self.setStyleSheet("background: transparent;")

    def generateSampleData(self):
        """生成示例数据"""
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

        # 更新表格数据
        self.source_model.updateData(sample_data)

    def filterData(self, text):
        """根据输入文本过滤数据"""
        self.proxy_model.setFilterRegExp(text)

    def sortData(self, text):
        """根据选择排序数据"""
        col = -1
        order = Qt.AscendingOrder

        if text == self.tr("Sort by PID"):
            col = 1
        elif text == self.tr("Sort by Process Name"):
            col = 0
        elif text == self.tr("Sort by Connections"):
            col = 5
            order = Qt.DescendingOrder  # 默认降序

        if col >= 0:
            self.proxy_model.sort(col, order)

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
        self.source_model.updateData(process_data)

    def tr(self, text):
        """翻译函数"""
        # 保持英文表头
        return text
