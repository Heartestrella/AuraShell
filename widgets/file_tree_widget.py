from qfluentwidgets import BreadcrumbBar, LineEdit, TransparentToolButton
from typing import Dict, Optional
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTreeWidgetItem, QStyle, QFrame
from qfluentwidgets import isDarkTheme
from PyQt5.QtCore import Qt, pyqtSignal
from qfluentwidgets import TreeWidget, RoundMenu, Action, FluentIcon as FIF
from typing import Optional, Dict, Set


def _parse_linux_path(path: str):
    """
    Change '/home/bee' -> ['home','bee']
    root '/' -> []
    """
    if not path:
        return []
    path = path.strip()
    if path == '/':
        return []
    parts = [p for p in path.strip('/').split('/') if p]
    return parts


class File_Navigation_Bar(QWidget):
    bar_path_changed = pyqtSignal(str)
    new_folder_clicked = pyqtSignal()
    refresh_clicked = pyqtSignal()
    view_switch_clicked = pyqtSignal()
    upload_mode_toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.send_signal = True
        self.current_path = "/"
        self._is_submitting = False

        # Create a container for the border
        self.breadcrumb_container = QFrame(self)

        # Beautify the container with QSS
        if isDarkTheme():
            self.breadcrumb_container.setStyleSheet("""
                QFrame {
                    border: 1px solid #4a4a4a;
                    border-radius: 4px;
                    background-color: transparent;
                }
                QFrame:hover {
                    background-color: rgba(255, 255, 255, 0.08);
                }
            """)
        else:
            self.breadcrumb_container.setStyleSheet("""
                QFrame {
                    border: 1px solid #dcdcdc;
                    border-radius: 4px;
                    background-color: transparent;
                }
                QFrame:hover {
                    background-color: rgba(0, 0, 0, 0.05);
                }
            """)

        # Place the BreadcrumbBar inside the container
        container_layout = QHBoxLayout(self.breadcrumb_container)
        container_layout.setContentsMargins(2, 2, 2, 2)
        self.breadcrumbBar = BreadcrumbBar(self.breadcrumb_container)
        self.breadcrumbBar.setStyleSheet(
            "background-color: transparent; border: none;")
        container_layout.addWidget(self.breadcrumbBar)
        self.path_edit = LineEdit(self)
        self.path_edit.hide()

        self.hBoxLayout = QHBoxLayout(self)
        self.hBoxLayout.setContentsMargins(10, 5, 10, 5)
        self.hBoxLayout.addWidget(self.breadcrumb_container, 1)
        self.hBoxLayout.addWidget(self.path_edit)

        self.view_switch_button = TransparentToolButton(FIF.VIEW, self)
        self.hBoxLayout.addWidget(self.view_switch_button)

        self.upload_mode_button = TransparentToolButton(
            FIF.ZIP_FOLDER, self)
        self.upload_mode_button.setCheckable(True)
        self.upload_mode_button.setProperty('isChecked', False)
        style = """
            TransparentToolButton[isChecked="true"] {
                background-color: rgba(0, 0, 0, 0.1);
            }
        """
        if isDarkTheme():
            style = """
            TransparentToolButton[isChecked="true"] {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """
        self.upload_mode_button.setStyleSheet(style)
        self.hBoxLayout.addWidget(self.upload_mode_button)

        self.new_folder_button = TransparentToolButton(FIF.FOLDER_ADD, self)
        self.new_folder_button.setToolTip(self.tr('New folder'))
        self.refresh_button = TransparentToolButton(FIF.UPDATE, self)
        self.refresh_button.setToolTip(self.tr('Refresh') + '(F5)')

        self.hBoxLayout.addWidget(self.new_folder_button)
        self.hBoxLayout.addWidget(self.refresh_button)

        self.new_folder_button.clicked.connect(self.new_folder_clicked.emit)
        self.refresh_button.clicked.connect(self.refresh_clicked.emit)
        self.view_switch_button.clicked.connect(self.view_switch_clicked.emit)
        self.upload_mode_button.toggled.connect(self.upload_mode_toggled.emit)

        self.breadcrumbBar.currentItemChanged.connect(self.updatePathLabel)
        self.path_edit.returnPressed.connect(self._submit_path_from_edit)
        self.path_edit.editingFinished.connect(self._submit_path_from_edit)

    def update_view_switch_button(self, current_mode: str):
        if current_mode == "icon":
            self.view_switch_button.setIcon(FIF.VIEW)
            self.view_switch_button.setToolTip(self.tr('Details View'))
        else:
            self.view_switch_button.setIcon(FIF.APPLICATION)
            self.view_switch_button.setToolTip(self.tr('Icon View'))

    def update_upload_mode_button(self, is_checked: bool):
        self.upload_mode_button.setChecked(is_checked)
        self.upload_mode_button.setProperty('isChecked', is_checked)
        self.upload_mode_button.setStyle(QApplication.style())
        if is_checked:
            self.upload_mode_button.setToolTip(
                self.tr('Compression Upload mode is on'))
        else:
            self.upload_mode_button.setToolTip(
                self.tr('Compression Upload mode is off'))

    def mousePressEvent(self, event):
        if not self.path_edit.isVisible() and self.breadcrumb_container.geometry().contains(event.pos()):
            self.path_edit.setText(self.current_path)
            self.breadcrumb_container.hide()
            self.path_edit.show()
            self.path_edit.setFocus()
            self.path_edit.selectAll()
        super().mousePressEvent(event)

    def _submit_path_from_edit(self):
        if self._is_submitting:
            return
        self._is_submitting = True
        new_path = self.path_edit.text().strip()
        if new_path:
            self.current_path = new_path
            self.bar_path_changed.emit(new_path)
        self._hide_path_edit()
        self._is_submitting = False

    def _hide_path_edit(self):
        self.path_edit.hide()
        self.breadcrumb_container.show()

    def updatePathLabel(self, *_):
        if self.send_signal:
            currentIndex = self.breadcrumbBar.currentIndex()
            items = self.breadcrumbBar.items
            path_list = [item.text for item in items[:currentIndex + 1]]
            path = "/" + \
                "/".join(path_list[1:]) if len(path_list) > 1 else (
                    path_list[0] if path_list else "/")
            if path == "//":
                path = "/"
            self.current_path = path
            self.bar_path_changed.emit(path)

    def set_path(self, path: str):
        self.current_path = path


class FileTreeWidget(QWidget):
    """
File tree widget (can pass in an initial file_tree).\n
- refresh_tree(new_tree=None, preserve_expand=True)\n
- add_path(path, type='file')\n
- remove_path(path)\n
Internal model: {'': {...}}\n
Files are marked with the string "is_file"; directories are marked with a dict.
    """
    directory_selected = pyqtSignal(str)  # path

    def __init__(self, parent=None, file_tree: Optional[Dict] = None):
        super().__init__(parent)
        self.setLayout(QVBoxLayout(self))
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.refresh = Action(FIF.UPDATE, self.tr('Refresh the file tree'))
        self.tree = TreeWidget(self)
        self.tree.setHeaderLabels([self.tr("File Manager")])
        self.tree.setColumnCount(1)
        self.layout().addWidget(self.tree)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        # Internal data model
        if file_tree is None:
            self.file_tree = {'': {}}
        else:
            self.file_tree = file_tree

        # Initialize rendering
        self.refresh_tree()

    # ------------------------
    # Expand state collection/recovery
    # ------------------------
    def _gather_expanded_paths(self) -> Set[str]:
        """Traverse the current tree and collect the full paths of all expanded items into a set"""
        expanded = set()

        def recurse(item):
            # item can be QTreeWidgetItem
            for i in range(item.childCount()):
                ch = item.child(i)
                path = ch.data(0, Qt.UserRole)
                if path and ch.isExpanded():
                    expanded.add(path)
                recurse(ch)

        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            top = root.child(i)
            path = top.data(0, Qt.UserRole)
            if path and top.isExpanded():
                expanded.add(path)
            recurse(top)
        return expanded

    def _restore_expanded_paths(self, expanded_paths: Set[str]):
        """Traverse all items and restore the expanded state according to the path collection"""
        def recurse(item):
            for i in range(item.childCount()):
                ch = item.child(i)
                path = ch.data(0, Qt.UserRole)
                if path and path in expanded_paths:
                    ch.setExpanded(True)
                else:
                    ch.setExpanded(False)
                recurse(ch)
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            top = root.child(i)
            path = top.data(0, Qt.UserRole)
            if path and path in expanded_paths:
                top.setExpanded(True)
            else:
                top.setExpanded(False)
            recurse(top)

    # ------------------------
    # 渲染函数
    # ------------------------
    def refresh_tree(self, new_tree: Optional[Dict] = None, preserve_expand: bool = True):
        """
        Refresh the entire tree:\n
        - If new_tree is passed, replace the internal model\n
        - preserve_expand: Whether to preserve the previous expanded state (default True)        """
        if new_tree is not None:
            self.file_tree = new_tree

        # 收集当前展开状态
        expanded_paths = set()
        if preserve_expand:
            expanded_paths = self._gather_expanded_paths()

        # 清空 UI
        self.tree.clear()

        # 填入根节点下的子项（忽略顶层 '' 键本身）
        root_dict = self.file_tree.get('', {})
        self._populate_tree(root_dict, self.tree, parent_path='')

        # 恢复展开状态（如果需要）
        if preserve_expand:
            self._restore_expanded_paths(expanded_paths)
    print("Refresh tree complete")

    def _populate_tree(self, node_dict: Dict, parent_item, parent_path: str):
        """
        Recursively append node_dict to parent_item (parent_item can be a TreeWidget or QTreeWidgetItem).
        parent_path: The full path of the parent node ('' represents the root), used to construct the full path of the current item, e.g. '/home' '/home/bee'        """
        def sort_key(kv):
            name, val = kv
            is_file = (val == "is_file")
            return (is_file, name.lower())

        for name, val in sorted(node_dict.items(), key=sort_key):
            if parent_path:
                full_path = parent_path.rstrip('/') + '/' + name
            else:
                full_path = '/' + name

            item = QTreeWidgetItem(parent_item, [name])
            item.setData(0, Qt.UserRole, full_path)

            if val == "is_file":
                icon = self.style().standardIcon(QStyle.SP_FileIcon)
                item.setIcon(0, icon)
            else:
                icon = self.style().standardIcon(QStyle.SP_DirIcon)
                item.setIcon(0, icon)
                if isinstance(val, dict) and val:
                    self._populate_tree(val, item, full_path)

    # ------------------------
    # Data model operations (add/remove)
    # ------------------------
    def add_path(self, path: str, typ: str = 'file'):
        """
        Adds path to the internal file_tree.\n
        typ: 'file'/'is_file' for files, 'dir'/'directory' for directories.\n
        Intermediate directories are automatically created (if an intermediate node was previously marked 'is_file', it will be overwritten as a directory).        """
        if not path:
            return

        parts = _parse_linux_path(path)
        if not parts:
            # path == '/'
            if '' not in self.file_tree:
                self.file_tree[''] = {}
            self.refresh_tree()
            return

        t = typ.lower()
        is_file = t in ('file', 'is_file', 'f')
        final_value = "is_file" if is_file else {}

        if '' not in self.file_tree:
            self.file_tree[''] = {}

        node = self.file_tree['']
        for i, part in enumerate(parts):
            last = (i == len(parts) - 1)
            if last:
                node[part] = final_value
            else:
                if part not in node or node[part] == "is_file":
                    node[part] = {}
                node = node[part]

        self.refresh_tree()

    def remove_path(self, path: str):
        """
        Delete the specified path (file or directory). If path=="/", the root is cleared
        """
        if not path:
            return

        parts = _parse_linux_path(path)
        if not parts:
            self.file_tree[''] = {}
            self.refresh_tree()
            return

        node = self.file_tree.get('', {})
        parents = []
        for part in parts[:-1]:
            if isinstance(node, dict) and part in node:
                parents.append((node, part))
                node = node[part]
            else:
                return

        last = parts[-1]
        if isinstance(node, dict) and last in node:
            del node[last]
            self.refresh_tree()
        else:
            return

    def get_model(self) -> Dict:
        """Returns the current internal file_tree reference"""
        return self.file_tree

    def contextMenuEvent(self, e) -> None:
        self.menu = RoundMenu(parent=self)
        self.menu.addActions([self.refresh])
        self.menu.addSeparator()
        self.menu.exec(e.globalPos())

    def switch_to(self, path: str):
        """
        Expand and select the specified path (must exist in the file_tree model)
        """
        if not path or path == "/":
            return

        parts = _parse_linux_path(path)
        if not parts:
            return

        root = self.tree.invisibleRootItem()
        current_item = None
        current_path = ""

        for i, part in enumerate(parts):
            if current_path:
                current_path = current_path.rstrip("/") + "/" + part
            else:
                current_path = "/" + part

            found = None
            parent = root if current_item is None else current_item
            for j in range(parent.childCount()):
                child = parent.child(j)
                child_path = child.data(0, Qt.UserRole)
                if child_path == current_path:
                    found = child
                    break

            if found is None:
                print(f"switch_to: {current_path} not found in tree")
                return  # Exit early if not found

            # Expand the directory (if it is not the last level)

            found.setExpanded(True)

            current_item = found

        # Finally select the target node
        if current_item is not None:
            self.tree.setCurrentItem(current_item)
            self.tree.scrollToItem(current_item)
            current_item.setSelected(True)

    def _on_item_double_clicked(self, item, column):
        """When you double-click an item, if it is a directory, a signal is emitted"""
        path = item.data(0, Qt.UserRole)
        if not path:
            return

        # Find the type of the path in the internal model
        node = self.file_tree.get('', {})
        parts = _parse_linux_path(path)
        for part in parts:
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                return

        # If it is a directory (dict type), emit a signal
        if isinstance(node, dict):
            print(f"文件树被选择：{path}")
            self.directory_selected.emit(path)
