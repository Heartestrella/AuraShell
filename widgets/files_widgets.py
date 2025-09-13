
from PyQt5.QtWidgets import QApplication, QWidget, QLayout, QSizePolicy, QRubberBand, QScrollArea, QVBoxLayout
from PyQt5.QtGui import QFont, QPainter, QColor
from PyQt5.QtCore import Qt, QRect, QSize, QPoint, pyqtSignal
from qfluentwidgets import RoundMenu, Action, FluentIcon as FIF, LineEdit
import os
from functools import partial


# ---------------- FlowLayout ----------------


class FlowLayout(QLayout):

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
    # Operation type, file name, directory or not
    action_triggered = pyqtSignal(str, str, str)
    # Operation type, original file name, new file name, whether it is a directory
    rename_action = pyqtSignal(str, str, str, str)

    def __init__(self, name, is_dir, parent=None, explorer=None, icons=None):
        super().__init__(parent)
        self.name = name
        self.is_dir = is_dir
        self.selected = False
        self.parent_explorer = explorer
        self.icons = icons

        self.icon = icons.Folder_Icon if is_dir else icons.File_Icon
        self.setMinimumSize(self.WIDTH, self.HEIGHT)

        self._update_style()
        self.rename_edit = LineEdit(self)
        self.rename_edit.setText(self.name)
        self.rename_edit.setAlignment(Qt.AlignCenter)
        self.rename_edit.hide()
        self.rename_edit.returnPressed.connect(self._apply_rename)
        self.rename_edit.editingFinished.connect(self._apply_rename)
        self._rename_applied = False

    def _update_style(self):
        """Update styles based on the theme"""
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

        if self.selected:
            painter.setBrush(QColor("#cce8ff"))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(self.rect(), 5, 5)

        painter.drawPixmap(
            (self.width() - self.icon.width()) // 2, 5, self.icon)

        font = QFont("Segoe UI", 8)
        painter.setFont(font)

        metrics = painter.fontMetrics()
        text_width = metrics.width(self.name)
        available_width = self.width() - 10

        display_text = self.name
        if text_width > available_width:

            display_text = metrics.elidedText(
                self.name, Qt.ElideMiddle, available_width)

        from qfluentwidgets import isDarkTheme
        if isDarkTheme():
            painter.setPen(QColor(255, 255, 255))
        else:
            painter.setPen(QColor(0, 0, 0))

        painter.drawText(QRect(5, 70, self.width()-10, 30),
                         Qt.AlignCenter, display_text)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            ctrl = QApplication.keyboardModifiers() & Qt.ControlModifier
            self.parent_explorer.select_item(self, ctrl)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.selected_sign.emit({self.name: self.is_dir})
            print(f"Double-click to open: {self.name}")

    def contextMenuEvent(self, e) -> None:
        menu = RoundMenu(parent=self)

        copy_action = Action(FIF.COPY, self.tr("Copy"))
        delete_action = Action(FIF.DELETE, self.tr("Delete"))
        cut_action = Action(FIF.CUT, self.tr("Cut"))
        download_action = Action(FIF.DOWNLOAD, self.tr("Download"))
        copy_path = Action(FIF.FLAG, self.tr("Copy Path"))
        file_info = Action(FIF.INFO, self.tr("File Info"))
        rename = Action(FIF.LABEL, self.tr("Rename"))

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
        if action_type == "rename":
            self._start_rename()
        else:
            self.action_triggered.emit(
                action_type, self.name, str(self.is_dir))

    def _start_rename(self):
        self._rename_applied = False
        self.rename_edit.setText(self.name)
        self.rename_edit.setGeometry(5, 70, self.width()-10, 25)
        self.rename_edit.show()
        self.rename_edit.setFocus()
        self.rename_edit.selectAll()

    def _apply_rename(self):
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

        self.copy_file_path = None
        self.cut_ = False
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)

        self.container = QWidget()
        self.flow_layout = FlowLayout(self.container)
        self.container.setLayout(self.flow_layout)

        self.scroll_area.setWidget(self.container)
        self.icons = icons

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
        self.paste = Action(FIF.PASTE, self.tr("Paste"))
        self.paste.triggered.connect(
            lambda: self._handle_file_action("paste", "", ""))

    def add_files(self, files):
        """
    Accepts:
    - dict: {name: bool_or_marker} (True for directories, False for files)
    - list: [{"name": ..., "is_dir": True/False}, ...]
    - list of tuples: [("name", True), ...]
    Sorts directories first, files last, in ascending order by name (case-insensitive).
        """
        # Temporarily disable updates to improve performance (avoid multiple repaints)
        self.container.setUpdatesEnabled(False)

        # 1) Clear old files (safely hide them first to avoid flicker)
        while self.flow_layout.count():
            item = self.flow_layout.takeAt(0)
            if item:
                w = item.widget()
                if w:
                    w.hide()           # Hide first to avoid top-level flicker
                    w.setParent(None)  # Remove parent
                    w.deleteLater()    # Delete later
        self.selected_items.clear()

        # 2) Normalize input into a list of (name, is_dir)
        entries = []
        if files is None:
            files = {}
        # dict: {name: val}
        if isinstance(files, dict):
            for name, val in files.items():
                # Determine if it is a directory: True or a dict (your file_tree uses dict for directories)
                is_dir = True if (
                    val is True or isinstance(val, dict)) else False
                entries.append((str(name), bool(is_dir)))
        # list: [{"name":..., "is_dir":...}] or [("name", True)]
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
                    # Unrecognized item, try converting to string as filename
                    entries.append((str(entry), False))
        else:
            # Ignore other types
            self.container.setUpdatesEnabled(True)
            return

        # 3) Sort: directories first (not is_dir -> False for directories),
        #    then sort by name case-insensitively
        entries.sort(key=lambda x: (not x[1], x[0].lower()))

        # 4) Create FileItem and add to layout
        for name, is_dir in entries:
            # Use functools.partial to prevent late binding issue with lambda
            item_widget = FileItem(
                name, is_dir, parent=self.container, explorer=self, icons=self.icons)
            # Connect selected_sign to pass item data while avoiding closure issues
            item_widget.selected_sign.connect(
                partial(lambda s, d: self.selected.emit(d), None))
            item_widget.action_triggered.connect(self._handle_file_action)
            item_widget.rename_action.connect(lambda type_, name, new_name, is_dir: self._handle_file_action(
                action_type=type_, file_name=name, is_dir_str=is_dir, new_name=new_name))
            # If you want to emit the specific name, you can do:
            # item_widget.selected_sign.connect(partial(self.selected.emit, {name: is_dir}))
            item_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            # Hide first to avoid flicker when adding to layout
            item_widget.hide()
            self.flow_layout.addWidget(item_widget)
            item_widget.show()

        # Re-enable updates and refresh display
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
        """Actions for processing file items"""
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
                        f"Action type: {action_type}, File path: {full_path}, Is it a directory: {is_dir_str}")
                    self.file_action.emit(action_type, full_path, "", False)

    # ---------------- Box selection logic ----------------

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

    # ---------------- Drag-in file event ----------------
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        file_dict = {}
        for url in urls:
            path = url.toLocalFile()
            print("Drag in the file path:", path)
            is_dir = os.path.isdir(path)
            filename = os.path.basename(path)
            file_dict[filename] = is_dir
            self.upload_file.emit(path, self.path)
        event.acceptProposedAction()

    def contextMenuEvent(self, e) -> None:
        menu = RoundMenu(parent=self)

        refresh_action = Action(FIF.UPDATE, self.tr('Refresh the page'))

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
