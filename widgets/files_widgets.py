
from PyQt5.QtWidgets import QApplication, QWidget, QLayout, QSizePolicy, QRubberBand, QScrollArea, QVBoxLayout
from PyQt5.QtGui import QFont, QPainter, QColor
from PyQt5.QtCore import Qt, QRect, QSize, QPoint, pyqtSignal
from qfluentwidgets import RoundMenu, Action, FluentIcon as FIF, LineEdit
import os
from functools import partial
# ---------------- 全局图标 ----------------


# ---------------- FlowLayout ----------------


class FlowLayout(QLayout):
    """自定义流式布局（自动换行）"""

    def __init__(self, parent=None, margin=10, spacing=20):
        super().__init__(parent)
        self.itemList = []
        self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)

    def addItem(self, item):
        self.itemList.append(item)

    def count(self):
        return len(self.itemList)

    def itemAt(self, index):
        return self.itemList[index] if 0 <= index < len(self.itemList) else None

    def takeAt(self, index):
        return self.itemList.pop(index) if 0 <= index < len(self.itemList) else None

    def expandingDirections(self):
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self.doLayout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self):
        return QSize(400, 300)

    def doLayout(self, rect, testOnly):
        x, y = rect.x(), rect.y()
        lineHeight = 0
        for item in self.itemList:
            wid = item.widget()
            spaceX = self.spacing()
            spaceY = self.spacing()
            nextX = x + wid.sizeHint().width() + spaceX
            if nextX - spaceX > rect.right() and lineHeight > 0:
                x = rect.x()
                y = y + lineHeight + spaceY
                nextX = x + wid.sizeHint().width() + spaceX
                lineHeight = 0
            if not testOnly:
                item.setGeometry(QRect(QPoint(x, y), wid.sizeHint()))
            x = nextX
            lineHeight = max(lineHeight, wid.sizeHint().height())
        return y + lineHeight - rect.y()

# ---------------- FileItem ----------------


class FileItem(QWidget):
    WIDTH, HEIGHT = 80, 100
    selected_sign = pyqtSignal(dict)
    action_triggered = pyqtSignal(str, str, str)  # 操作类型, 文件名, 是否目录
    rename_action = pyqtSignal(str, str, str, str)  # 操作类型, 原文件名, 新文件名，是否目录

    def __init__(self, name, is_dir, parent=None, explorer=None, icons=None):
        super().__init__(parent)
        self.name = name
        self.is_dir = is_dir
        self.selected = False
        self.parent_explorer = explorer
        self.icons = icons

        self.icon = icons.Folder_Icon if is_dir else icons.File_Icon
        self.setMinimumSize(self.WIDTH, self.HEIGHT)

        # 设置样式表，根据主题调整文字颜色
        self._update_style()
        self.rename_edit = LineEdit(self)
        self.rename_edit.setText(self.name)
        self.rename_edit.setAlignment(Qt.AlignCenter)
        self.rename_edit.hide()
        self.rename_edit.returnPressed.connect(self._apply_rename)
        self.rename_edit.editingFinished.connect(self._apply_rename)
        self._rename_applied = False

    def _update_style(self):
        """根据主题更新样式"""
        from qfluentwidgets import isDarkTheme
        if isDarkTheme():
            self.setStyleSheet("""
                FileItem {
                    color: white;
                    background: transparent;
                }
                FileItem:hover {
                    background: rgba(255, 255, 255, 0.1);
                }
            """)
        else:
            self.setStyleSheet("""
                FileItem {
                    color: black;
                    background: transparent;
                }
                FileItem:hover {
                    background: rgba(0, 0, 0, 0.05);
                }
            """)

    def sizeHint(self):
        return QSize(self.WIDTH, self.HEIGHT)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 绘制选中背景
        if self.selected:
            painter.setBrush(QColor("#cce8ff"))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(self.rect(), 5, 5)

        # 绘制图标
        painter.drawPixmap(
            (self.width() - self.icon.width()) // 2, 5, self.icon)

        # 绘制文件名 - 处理过长文件名
        font = QFont("Segoe UI", 8)  # 使用稍小的字体
        painter.setFont(font)

        # 获取字体度量
        metrics = painter.fontMetrics()
        text_width = metrics.width(self.name)
        available_width = self.width() - 10  # 左右留5像素边距

        # 处理文本过长的情况
        display_text = self.name
        if text_width > available_width:
            # 使用省略号缩短文本
            display_text = metrics.elidedText(
                self.name, Qt.ElideMiddle, available_width)

        # 设置文本颜色（从样式表获取或根据主题设置）
        from qfluentwidgets import isDarkTheme
        if isDarkTheme():
            painter.setPen(QColor(255, 255, 255))  # 白色
        else:
            painter.setPen(QColor(0, 0, 0))  # 黑色

        # 绘制文本
        painter.drawText(QRect(5, 70, self.width()-10, 30),
                         Qt.AlignCenter, display_text)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            ctrl = QApplication.keyboardModifiers() & Qt.ControlModifier
            self.parent_explorer.select_item(self, ctrl)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.selected_sign.emit({self.name: self.is_dir})
            print(f"双击打开: {self.name}")

    def contextMenuEvent(self, e) -> None:
        menu = RoundMenu(parent=self)

        copy_action = Action(FIF.COPY, '复制')
        delete_action = Action(FIF.DELETE, '删除')
        cut_action = Action(FIF.CUT, "剪切")
        download_action = Action(FIF.DOWNLOAD, "下载")
        copy_path = Action(FIF.FLAG, "复制路径")
        file_info = Action(FIF.INFO, "详细信息")
        rename = Action(FIF.LABEL, "重命名")
        copy_action.triggered.connect(lambda: self._emit_action('copy'))
        delete_action.triggered.connect(lambda: self._emit_action('delete'))
        cut_action.triggered.connect(lambda: self._emit_action('cut'))
        download_action.triggered.connect(
            lambda: self._emit_action('download'))
        copy_path.triggered.connect(
            lambda: self._emit_action('copy_path'))
        file_info.triggered.connect(
            lambda: self._emit_action('info'))
        rename.triggered.connect(lambda: self._emit_action('rename'))
        menu.addActions([copy_action, cut_action,
                        delete_action, download_action, copy_path, file_info, rename])
        menu.addSeparator()
        menu.exec(e.globalPos())

    def _emit_action(self, action_type):
        """发射动作信号"""
        if action_type == "rename":
            self._start_rename()
        else:
            self.action_triggered.emit(
                action_type, self.name, str(self.is_dir))

    def _start_rename(self):
        """进入重命名模式"""
        self._rename_applied = False
        self.rename_edit.setText(self.name)
        self.rename_edit.setGeometry(5, 70, self.width()-10, 25)
        self.rename_edit.show()
        self.rename_edit.setFocus()
        self.rename_edit.selectAll()

    def _apply_rename(self):
        """提交重命名"""
        if self._rename_applied:
            return

        self._rename_applied = True
        new_name = self.rename_edit.text().strip()
        if new_name and new_name != self.name:
            self.rename_action.emit(
                "rename", self.name, new_name, str(self.is_dir))
        self.rename_edit.hide()
        self.update()
# ---------------- FileExplorer ----------------


class FileExplorer(QWidget):
    selected = pyqtSignal(dict)
    # action type , path , copy_to path , cut?
    file_action = pyqtSignal(str, str, str, bool)
    upload_file = pyqtSignal(str, str)  # Source path , Target path
    refresh_action = pyqtSignal()

    def __init__(self, parent=None, path=None, icons=None):
        super().__init__(parent)
        # 滚动区域
        self.copy_file_path = None
        self.cut_ = False
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)

        # 容器 widget 放 FlowLayout
        self.container = QWidget()
        self.flow_layout = FlowLayout(self.container)
        self.container.setLayout(self.flow_layout)

        self.scroll_area.setWidget(self.container)
        self.icons = icons
        # 主布局

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.scroll_area)
        self.setLayout(main_layout)

        self.path = path
        self.selected_items = set()
        self.rubberBand = QRubberBand(QRubberBand.Rectangle, self)
        self.dragging = False
        self.start_pos = None
        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        self.paste = Action(FIF.PASTE, "粘贴")
        self.paste.triggered.connect(
            lambda: self._handle_file_action("paste", "", ""))

    def add_files(self, files):
        """
        接受：
        - dict: {name: bool_or_marker}  (True 表示目录，False 表示文件)
        - list: [{"name": ..., "is_dir": True/False}, ...]
        - list of tuples: [("name", True), ...]
        将目录排序在前，文件在后，均按名字（不区分大小写）升序。
        """
        # 临时关闭更新以提升性能（避免多次重绘）
        self.container.setUpdatesEnabled(False)

        # 1) 清空旧文件（安全隐藏，避免闪现）
        while self.flow_layout.count():
            item = self.flow_layout.takeAt(0)
            if item:
                w = item.widget()
                if w:
                    w.hide()          # 先隐藏，避免顶层闪现
                    w.setParent(None)  # 移除父窗口
                    w.deleteLater()   # 延迟删除
        self.selected_items.clear()

        # 2) 归一化输入到 (name, is_dir) 列表
        entries = []
        if files is None:
            files = {}
        # dict: {name: val}
        if isinstance(files, dict):
            for name, val in files.items():
                # 判定为目录的条件：值为 True, 或者是 dict（你的 file_tree 里目录用 dict 表示）
                is_dir = True if (
                    val is True or isinstance(val, dict)) else False
                entries.append((str(name), bool(is_dir)))
        # list: [{"name":..., "is_dir":...}] 或 [("name", True)]
        elif isinstance(files, (list, tuple)):
            for entry in files:
                if isinstance(entry, dict):
                    name = entry.get("name") or entry.get(
                        "path") or entry.get("filename")
                    is_dir = entry.get("is_dir") or entry.get(
                        "isDir") or entry.get("is_directory") or False
                    entries.append((str(name), bool(is_dir)))
                elif isinstance(entry, (list, tuple)) and len(entry) >= 2:
                    entries.append((str(entry[0]), bool(entry[1])))
                else:
                    # 不识别的条目，尝试 str() 处理为文件名
                    entries.append((str(entry), False))
        else:
            # 其它类型直接忽略
            self.container.setUpdatesEnabled(True)
            return

        # 3) 排序：目录在前 (not is_dir -> False for directories),
        #    然后按名字不区分大小写排序
        entries.sort(key=lambda x: (not x[1], x[0].lower()))

        # 4) 创建 FileItem 并添加到布局
        for name, is_dir in entries:
            # 使用 functools.partial 防止 lambda 闭包晚绑定问题
            item_widget = FileItem(
                name, is_dir, parent=self.container, explorer=self, icons=self.icons)
            # selected_sign 需要传递条目数据时，避免闭包问题
            item_widget.selected_sign.connect(
                partial(lambda s, d: self.selected.emit(d), None))
            item_widget.action_triggered.connect(self._handle_file_action)
            item_widget.rename_action.connect(lambda type_, name, new_name, is_dir: self._handle_file_action(
                action_type=type_, file_name=name, is_dir_str=is_dir, new_name=new_name))
            # 如果你需要把具体 name 传出去，可以这样：
            # item_widget.selected_sign.connect(partial(self.selected.emit, {name: is_dir}))
            item_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            # 先隐藏，避免在 addWidget 的瞬间出现（更稳妥）
            item_widget.hide()
            self.flow_layout.addWidget(item_widget)
            item_widget.show()

        # 恢复更新并刷新显示
        self.container.setUpdatesEnabled(True)
        self.container.update()

    def select_item(self, item, ctrl=False):
        if ctrl:
            if item in self.selected_items:
                self.selected_items.remove(item)
                item.selected = False
            else:
                self.selected_items.add(item)
                item.selected = True
        else:
            for i in self.selected_items:
                i.selected = False
                i.update()
            self.selected_items = {item}
            item.selected = True
        item.update()

    def _handle_file_action(self, action_type, file_name, is_dir_str, new_name=None):
        """处理文件项的动作"""
        if file_name:
            if self.path.endswith('/'):
                full_path = self.path + file_name
            else:
                full_path = self.path + '/' + file_name

            full_path = os.path.normpath(full_path).replace('\\', '/')

        if action_type == "rename":
            if new_name:
                self.file_action.emit(action_type, full_path, new_name, False)

        else:

            if action_type == "copy":
                self.copy_file_path = full_path
                self.cut_ = False
            elif action_type == "cut":
                self.copy_file_path = full_path
                self.cut_ = True
            else:

                if action_type == "paste":
                    self.file_action.emit(
                        action_type, self.copy_file_path, self.path, self.cut_)
                    if self.cut_:
                        # reset
                        self.cut_ = False
                        self.copy_file_path = ""
                else:
                    print(
                        f"操作类型: {action_type}, 文件路径: {full_path}, 是否是目录: {is_dir_str}")
                    self.file_action.emit(action_type, full_path, "", False)

    # ---------------- 框选逻辑 ----------------

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            ctrl = QApplication.keyboardModifiers() & Qt.ControlModifier
            in_item = False
            for i in range(self.flow_layout.count()):
                widget = self.flow_layout.itemAt(i).widget()
                if widget.geometry().contains(event.pos()):
                    in_item = True
                    break
            if not in_item:
                self.dragging = True
                self.start_pos = event.pos()
                if not ctrl:
                    for item in self.selected_items:
                        item.selected = False
                        item.update()
                    self.selected_items.clear()
                self.rubberBand.setGeometry(QRect(self.start_pos, QSize()))
                self.rubberBand.show()

    def mouseMoveEvent(self, event):
        if self.dragging:
            rect = QRect(self.start_pos, event.pos()).normalized()
            self.rubberBand.setGeometry(rect)
            for i in range(self.flow_layout.count()):
                widget = self.flow_layout.itemAt(i).widget()
                if rect.intersects(widget.geometry()):
                    if widget not in self.selected_items:
                        self.selected_items.add(widget)
                        widget.selected = True
                        widget.update()
                else:
                    if widget in self.selected_items and not (Qt.ControlModifier & QApplication.keyboardModifiers()):
                        self.selected_items.remove(widget)
                        widget.selected = False
                        widget.update()

    def mouseReleaseEvent(self, event):
        if self.dragging:
            self.dragging = False
            self.rubberBand.hide()

    # ---------------- 拖入文件事件 ----------------
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        file_dict = {}
        for url in urls:
            path = url.toLocalFile()
            print("拖入文件路径:", path)
            is_dir = os.path.isdir(path)
            filename = os.path.basename(path)
            file_dict[filename] = is_dir
            self.upload_file.emit(path, self.path)
        event.acceptProposedAction()

    def contextMenuEvent(self, e) -> None:
        menu = RoundMenu(parent=self)

        refresh_action = Action(FIF.UPDATE, '刷新页面')

        refresh_action.triggered.connect(
            lambda checked: self.refresh_action.emit())
        # copy_action.triggered.connect(lambda: self._emit_action('copy'))
        # delete_action.triggered.connect(lambda: self._emit_action('delete'))
        # cut_action.triggered.connect(lambda: self._emit_action('cut'))
        # download_action.triggered.connect(
        #     lambda: self._emit_action('download'))

        menu.addActions([refresh_action, self.paste])
        menu.addSeparator()
        menu.exec(e.globalPos())
