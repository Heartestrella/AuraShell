
from PyQt5.QtWidgets import (QApplication, QWidget, QLayout, QSizePolicy,
                             QRubberBand, QScrollArea, QVBoxLayout, QTableView, QHeaderView)
from PyQt5.QtGui import QFont, QPainter, QColor, QStandardItemModel, QStandardItem
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
    # new_dir_name
    mkdir_action = pyqtSignal(str)

    def __init__(self, name, is_dir, parent=None, explorer=None, icons=None):
        super().__init__(parent)
        self.name = name
        self.is_dir = is_dir
        self.selected = False
        self.parent_explorer = explorer
        self.icons = icons
        self.mkdir = False
        self.icon = icons.Folder_Icon if is_dir else icons.File_Icon
        self.setMinimumSize(self.WIDTH, self.HEIGHT)

        self._update_style()
        self.rename_edit = LineEdit(self)
        self.rename_edit.setText(self.name)
        self.rename_edit.setAlignment(Qt.AlignCenter)
        self.rename_edit.hide()
        # self.rename_edit.returnPressed.connect(self._apply_rename)
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

    def _create_context_menu(self):
        """Creates and returns the context menu for the file item."""
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

        menu.addActions([copy_action, cut_action, delete_action,
                        download_action, copy_path, file_info, rename])
        menu.addSeparator()
        return menu

    def contextMenuEvent(self, e):
        # Ensure the item is selected before showing the context menu
        if not self.selected:
            self.parent_explorer.select_item(self)

        menu = self._create_context_menu()
        menu.exec(e.globalPos())

    def _emit_action(self, action_type):
        if action_type == "rename":
            self._start_rename()
        else:
            # Always emit for the source item only. The explorer will handle multi-select.
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
        print("Apply rename")
        if self._rename_applied:
            return

        self._rename_applied = True
        new_name = self.rename_edit.text().strip()
        if self.mkdir:
            self.mkdir_action.emit(new_name)
            self.mkdir = False
            self.rename_edit.hide()
            self.update()
        else:

            if new_name and new_name != self.name:
                self.rename_action.emit(
                    "rename", self.name, new_name, str(self.is_dir))
            self.rename_edit.hide()
            self.update()
# ---------------- FileExplorer ----------------


class FileExplorer(QWidget):
    selected = pyqtSignal(dict)
    # action type , path , copy_to path , cut?
    file_action = pyqtSignal(str, object, str, bool)
    upload_file = pyqtSignal(str, str)  # Source path , Target path
    refresh_action = pyqtSignal()

    def __init__(self, parent=None, path=None, icons=None):
        super().__init__(parent)
        self.view_mode = "icon"  # "icon" or "details"
        self.copy_file_path = None
        self.cut_ = False
        self.icons = icons
        self.path = path

        # Icon view
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.container = QWidget()
        self.flow_layout = FlowLayout(self.container)
        self.container.setLayout(self.flow_layout)
        self.scroll_area.setWidget(self.container)

        # Details view
        self.details_view = QTableView(self)
        self.details_model = QStandardItemModel(self)
        self.details_view.setModel(self.details_model)
        self.details_view.setVisible(False)  # Default hidden
        self.details_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.details_view.setEditTriggers(QTableView.NoEditTriggers)
        self.details_view.setSelectionBehavior(QTableView.SelectRows)
        self.details_view.setSelectionMode(QTableView.ExtendedSelection)
        self.details_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.details_view.customContextMenuRequested.connect(
            self._show_details_view_context_menu)
        self.details_view.doubleClicked.connect(
            self._handle_details_view_double_click)
        self.details_view.verticalHeader().setVisible(False)
        self.details_model.setHorizontalHeaderLabels(
            ['文件名', '大小', '修改时间', '权限', '用户/用户组'])

        from qfluentwidgets import isDarkTheme
        if isDarkTheme():
            self.details_view.setStyleSheet("""
                QTableView {
                    color: white;
                    background-color: transparent;
                    border: none;
                    gridline-color: #454545;
                }
                QTableView::item {
                    border-bottom: 1px solid transparent;
                    padding: 5px;
                }
                QTableView::item:selected {
                    background-color: #555;
                    color: white;
                }
                QHeaderView::section {
                    background-color: transparent;
                    color: white;
                    border: none;
                    border-bottom: 1px solid #555;
                    padding: 5px;
                }
            """)
        else:
            self.details_view.setStyleSheet("""
                QTableView {
                    color: black;
                    background-color: transparent;
                    border: none;
                    gridline-color: #DCDCDC;
                }
                QTableView::item {
                     border-bottom: 1px solid transparent;
                     padding: 5px;
                }
                QTableView::item:selected {
                    background-color: #cce8ff;
                    color: black;
                }
                QHeaderView::section {
                    background-color: transparent;
                    color: black;
                    border: none;
                    border-bottom: 1px solid #ccc;
                    padding: 5px;
                }
            """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.scroll_area)
        main_layout.addWidget(self.details_view)
        self.setLayout(main_layout)
        self.selected_items = set()
        self.rubberBand = QRubberBand(QRubberBand.Rectangle, self)
        self.dragging = False
        self.start_pos = None
        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        self.paste = Action(FIF.PASTE, self.tr("Paste"))
        self.paste.triggered.connect(
            lambda: self._handle_file_action("paste", "", ""))
        self.make_dir = Action(FIF.FOLDER_ADD, self.tr("New Folder"))
        self.make_dir.triggered.connect(self._handle_mkdir)
        # self.make_dir.triggered.connect(
        #     lambda: self._handle_file_action("mkdir", "", ""))

    def _handle_mkdir(self):
        """Create a new folder placeholder and enter rename mode."""
        new_folder_name = "New Folder"

        # Make sure the name is unique to prevent existing folders with the same name
        existing_names = {self.flow_layout.itemAt(
            i).widget().name for i in range(self.flow_layout.count())}
        counter = 1
        candidate_name = new_folder_name
        while candidate_name in existing_names:
            candidate_name = f"{new_folder_name} ({counter})"
            counter += 1

        self.add_files([(candidate_name, True)], clear_old=False)

        new_item = self.flow_layout.itemAt(
            self.flow_layout.count() - 1).widget()

        self.select_item(new_item)
        new_item.mkdir = True
        new_item._start_rename()

    def switch_view(self, view_type):
        """Switch between icon and details view."""
        if view_type == "icon":
            self.view_mode = "icon"
            self.scroll_area.setVisible(True)
            self.details_view.setVisible(False)
        elif view_type == "details":
            self.view_mode = "details"
            self.scroll_area.setVisible(False)
            self.details_view.setVisible(True)
        # Refresh the view with current files
        self.refresh_action.emit()

    def add_files(self, files, clear_old=True):
        """
    Accepts:
    - dict: {name: bool_or_marker} (True for directories, False for files)
    - list: [{"name": ..., "is_dir": True/False}, ...]
    - list of tuples: [("name", True), ...]
    Sorts directories first, files last, in ascending order by name (case-insensitive).
        """
        if self.view_mode == "icon":
            self._add_files_to_icon_view(files, clear_old)
        else:
            self._add_files_to_details_view(files, clear_old)

    def _add_files_to_icon_view(self, files, clear_old=True):
        self.container.setUpdatesEnabled(False)
        if clear_old:
            while self.flow_layout.count():
                item = self.flow_layout.takeAt(0)
                if item and item.widget():
                    item.widget().deleteLater()
            self.selected_items.clear()

        entries = self._normalize_files_data(files)
        entries.sort(key=lambda x: (not x[1], x[0].lower()))

        for name, is_dir, *_ in entries:
            item_widget = FileItem(
                name, is_dir, parent=self.container, explorer=self, icons=self.icons)
            item_widget.selected_sign.connect(
                partial(lambda s, d: self.selected.emit(d), None))
            item_widget.action_triggered.connect(self._handle_file_action)
            item_widget.rename_action.connect(
                lambda type_, name, new_name, is_dir: self._handle_file_action(
                    action_type=type_, file_name=name, is_dir_str=is_dir, new_name=new_name))
            item_widget.mkdir_action.connect(
                lambda new_dir_name: self._handle_file_action(
                    action_type="mkdir", file_name=new_dir_name))
            item_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            self.flow_layout.addWidget(item_widget)

        self.container.setUpdatesEnabled(True)
        self.container.update()

    def _add_files_to_details_view(self, files, clear_old=True):
        self.details_model.setRowCount(0)
        entries = self._normalize_files_data(files)
        # Sort by name, with directories first
        entries.sort(key=lambda x: (not x[1], x[0].lower()))

        for name, is_dir, size, mod_time, perms, owner in entries:
            size_str = self._format_size(size) if not is_dir and size else ""
            item_name = QStandardItem(name)
            # Store is_dir flag in the item itself for later retrieval
            item_name.setData(is_dir, Qt.UserRole)

            row = [
                item_name,
                QStandardItem(size_str),
                QStandardItem(mod_time),
                QStandardItem(perms),
                QStandardItem(owner)
            ]
            self.details_model.appendRow(row)

    def _format_size(self, size_bytes):
        """Format size in bytes to a human-readable string."""
        if not size_bytes:
            return ""
        try:
            size_bytes = int(size_bytes)
            if size_bytes == 0:
                return "0 B"
            size_names = ("B", "KB", "MB", "GB", "TB")
            i = 0
            while size_bytes >= 1024 and i < len(size_names) - 1:
                size_bytes /= 1024.0
                i += 1
            return f"{round(size_bytes, 2)} {size_names[i]}"
        except (ValueError, TypeError):
            return str(size_bytes)

    def _normalize_files_data(self, files):
        """Normalize different input formats to a standard list of tuples."""
        entries = []
        if not files:
            return entries

        if isinstance(files, dict):
            # Assuming dict provides {name: is_dir}
            for name, val in files.items():
                is_dir = True if (
                    val is True or isinstance(val, dict)) else False
                entries.append(
                    (str(name), is_dir, '', '', '', ''))
        elif isinstance(files, (list, tuple)):
            for entry in files:
                if isinstance(entry, dict):
                    name = entry.get("name", "")
                    is_dir = entry.get("is_dir", False)
                    size = entry.get("size", 0)
                    mod_time = entry.get("mtime", "")
                    perms = entry.get("perms", "")
                    owner = entry.get("owner", "")
                    entries.append((name, is_dir, size, mod_time, perms, owner))
                elif isinstance(entry, (list, tuple)) and len(entry) >= 2:
                    # Basic ("name", is_dir) provided
                    name, is_dir = entry[0], bool(entry[1])
                    entries.append(
                        (str(name), is_dir, '', '', '', ''))
        return entries

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

    def _handle_file_action(self, action_type, file_name, is_dir_str=None, new_name=None):
        """Central handler for all file actions, aggregates selections."""
        # Handle single-path actions first
        if action_type in ["rename", "mkdir"]:
            full_path = self._get_full_path(file_name) if file_name else ""
            if action_type == "rename" and new_name:
                self.file_action.emit(action_type, full_path, new_name, False)
            elif action_type == "mkdir" and file_name:
                self.file_action.emit(action_type, full_path, "", False)
            return

        # For other actions, aggregate all selected paths
        paths = []
        if self.view_mode == 'icon' and len(self.selected_items) > 1:
            paths = [self._get_full_path(item.name)
                     for item in self.selected_items]
        elif self.view_mode == 'details' and len(self.details_view.selectionModel().selectedRows()) > 1:
            for index in self.details_view.selectionModel().selectedRows():
                name = self.details_model.item(index.row(), 0).text()
                paths.append(self._get_full_path(name))
        else:
            # Single selection case for non-rename/mkdir actions
            if file_name:
                paths = [self._get_full_path(file_name)]

        if not paths:
            return  # Nothing to do

        # Process aggregated paths
        if action_type == "copy":
            self.copy_file_path = paths
            self.cut_ = False
        elif action_type == "cut":
            self.copy_file_path = paths
            self.cut_ = True
        elif action_type == "paste":
            # copy_file_path is already a list from copy/cut
            self.file_action.emit(
                action_type, self.copy_file_path, self.path, self.cut_)
            if self.cut_:
                self.cut_ = False
                self.copy_file_path = []
        else:  # e.g., "delete", "download", etc.
            print(f"Action: {action_type}, Paths: {paths}")
            self.file_action.emit(action_type, paths, "", False)

    # ---------------- Box selection logic ----------------

    def _handle_details_view_double_click(self, index):
        if not index.isValid():
            return

        name_item = self.details_model.item(index.row(), 0)
        file_name = name_item.text()
        is_dir = name_item.data(Qt.UserRole)
        self.selected.emit({file_name: is_dir})
        print(f"Double-click to open from details view: {file_name}")

    def _show_details_view_context_menu(self, pos):
        index = self.details_view.indexAt(pos)
        if not index.isValid():
            self.contextMenuEvent(self.details_view.mapToGlobal(pos))
            return

        selection_model = self.details_view.selectionModel()
        # If the clicked item is not already part of the selection,
        # clear the previous selection and select only the clicked item.
        if not selection_model.isSelected(index):
            selection_model.clearSelection()
            selection_model.select(
                index, self.details_view.selectionModel().Select | self.details_view.selectionModel().Rows)

        # Now the selection is correct, proceed to show the menu.
        name_item = self.details_model.item(index.row(), 0)
        file_name = name_item.text()
        is_dir = name_item.data(Qt.UserRole)

        # Create a temporary FileItem to generate and show the context menu
        # This reuses the menu logic and now _emit_action handles multi-select
        temp_item = FileItem(
            file_name, is_dir, explorer=self, icons=self.icons)
        # Connect the signal from the temporary item to the actual handler
        temp_item.action_triggered.connect(self._handle_file_action)
        menu = temp_item._create_context_menu()
        menu.exec_(self.details_view.viewport().mapToGlobal(pos))

    def mousePressEvent(self, event):
        # This event is for the icon view's rubber band selection
        if self.view_mode == 'details':
            super().mousePressEvent(event)
            return
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
        details_view_action = Action(
            FIF.VIEW, self.tr('Details View'))
        icon_view_action = Action(
            FIF.APPLICATION, self.tr('Icon View'))

        refresh_action.triggered.connect(
            lambda checked: self.refresh_action.emit())
        details_view_action.triggered.connect(
            lambda: self.switch_view("details"))
        icon_view_action.triggered.connect(
            lambda: self.switch_view("icon"))

        menu.addActions([refresh_action, self.paste, self.make_dir])
        menu.addSeparator()
        menu.addActions([details_view_action, icon_view_action])
        menu.addSeparator()
        menu.exec(e.globalPos())

    def _get_full_path(self, file_name):
        path = os.path.join(self.path, file_name)
        return os.path.normpath(path).replace('\\', '/')

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            # Call the handler directly. Pass a dummy file_name as it will be ignored
            # in multi-select scenarios and is not needed for single-select delete.
            self._handle_file_action('delete', '')

        elif event.key() == Qt.Key_F2:
            # F2 rename should only work for a single selection
            if self.view_mode == 'icon' and len(self.selected_items) == 1:
                item = list(self.selected_items)[0]
                item._start_rename()
            elif self.view_mode == 'details' and len(self.details_view.selectionModel().selectedRows()) == 1:
                # This part is complex because FileItem handles the LineEdit.
                # A more robust solution would be needed to trigger rename from here.
                print("F2 rename in details view needs a dedicated implementation.")
        else:
            super().keyPressEvent(event)
