from qfluentwidgets import BreadcrumbBar
from typing import Dict, Optional
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTreeWidgetItem, QStyle
from PyQt5.QtCore import Qt, pyqtSignal
from qfluentwidgets import TreeWidget, RoundMenu, Action, FluentIcon as FIF
from typing import Optional, Dict, Set


def _parse_linux_path(path: str):
    """
    把 '/home/bee' -> ['home','bee']
    根 '/' -> []
    """
    if not path:
        return []
    path = path.strip()
    if path == '/':
        return []
    # 去除开头的斜杠，再按 '/' 分割，去掉空段
    parts = [p for p in path.strip('/').split('/') if p]
    return parts


class File_Navigation_Bar(QWidget):
    bar_path_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.send_signal = True
        self.breadcrumbBar = BreadcrumbBar(self)
        self.breadcrumbBar.currentItemChanged.connect(
            self.updatePathLabel)
        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(20, 20, 20, 20)
        self.vBoxLayout.addWidget(self.breadcrumbBar)

    def updatePathLabel(self, *_):

        if self.send_signal:
            print("updatePathLabel")
            currentIndex = self.breadcrumbBar.currentIndex()
            items = self.breadcrumbBar.items  # items 是 BreadcrumbItem 对象列表
            path_list = [item.text for item in items[:currentIndex + 1]]
            path = "/" + \
                "/".join(path_list[1:]
                         ) if len(path_list) > 1 else path_list[0]  # 拼接路径
            # print("Path Bar 当前路径:", path)
            self.bar_path_changed.emit(path)
        else:
            print("not send_signal")


class FileTreeWidget(QWidget):
    """
    文件树 Widget（可传入初始 file_tree）。
    - refresh_tree(new_tree=None, preserve_expand=True)
    - add_path(path, type='file')
    - remove_path(path)
    内部 model: {'': {...}}
    文件用字符串 "is_file" 标记，目录用 dict。
    """
    directory_selected = pyqtSignal(str)  # path

    def __init__(self, parent=None, file_tree: Optional[Dict] = None):
        super().__init__(parent)
        self.setLayout(QVBoxLayout(self))
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.refresh = Action(FIF.UPDATE, '刷新文件树')
        self.tree = TreeWidget(self)
        self.tree.setHeaderLabels(["文件管理器"])
        self.tree.setColumnCount(1)
        self.layout().addWidget(self.tree)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        # 内部数据模型
        if file_tree is None:
            self.file_tree = {'': {}}
        else:
            # 直接引用传入的 dict（如果需要独立副本，可在调用方传入 copy）
            self.file_tree = file_tree

        # 初始化渲染
        self.refresh_tree()

    # ------------------------
    # 展开状态收集/恢复
    # ------------------------
    def _gather_expanded_paths(self) -> Set[str]:
        """遍历当前 tree，将所有展开的 item 的完整路径收集为 set"""
        expanded = set()

        def recurse(item):
            # item can be QTreeWidgetItem
            for i in range(item.childCount()):
                ch = item.child(i)
                path = ch.data(0, Qt.UserRole)
                if path and ch.isExpanded():
                    expanded.add(path)
                recurse(ch)
        # 顶层 items
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            top = root.child(i)
            path = top.data(0, Qt.UserRole)
            if path and top.isExpanded():
                expanded.add(path)
            recurse(top)
        return expanded

    def _restore_expanded_paths(self, expanded_paths: Set[str]):
        """遍历所有 items，根据路径集合还原展开状态"""
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
        刷新整个树：
        - 如果传入 new_tree，则替换内部模型
        - preserve_expand: 是否保持以前的展开状态（默认 True）
        """
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
    print("刷新树完成")

    def _populate_tree(self, node_dict: Dict, parent_item, parent_path: str):
        """
        递归把 node_dict 添加到 parent_item（parent_item 可以是 TreeWidget 或 QTreeWidgetItem）
        parent_path: 父节点的完整路径（'' 表示根），用于构造当前项的完整路径，例如 '/home' '/home/bee'
        """
        # 排序：目录优先，按字母序
        def sort_key(kv):
            name, val = kv
            is_file = (val == "is_file")
            return (is_file, name.lower())

        for name, val in sorted(node_dict.items(), key=sort_key):
            # 构造完整路径
            if parent_path:
                full_path = parent_path.rstrip('/') + '/' + name
            else:
                full_path = '/' + name

            item = QTreeWidgetItem(parent_item, [name])
            # 存储完整路径到 UserRole（方便恢复状态/查找）
            item.setData(0, Qt.UserRole, full_path)

            if val == "is_file":
                icon = self.style().standardIcon(QStyle.SP_FileIcon)
                item.setIcon(0, icon)
                # 文件不递归
            else:
                icon = self.style().standardIcon(QStyle.SP_DirIcon)
                item.setIcon(0, icon)
                # 如果是目录且非空字典，则递归添加子项
                if isinstance(val, dict) and val:
                    self._populate_tree(val, item, full_path)

    # ------------------------
    # 数据模型操作（add / remove）
    # ------------------------
    def add_path(self, path: str, typ: str = 'file'):
        """
        在内部 file_tree 上添加 path。
        typ: 'file'/'is_file' 表示文件，'dir'/'directory' 表示目录
        会自动创建中间目录（如果中间节点曾被标记为 'is_file'，则会覆盖为目录）
        """
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
        删除指定 path（文件或目录）。如果 path=="/" 则清空根。
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
            # 可选：向上清理空目录（如果需要）
            self.refresh_tree()
        else:
            return

    def get_model(self) -> Dict:
        """返回当前内部 file_tree 引用（注意：是引用而非深拷贝）"""
        return self.file_tree

    def contextMenuEvent(self, e) -> None:
        self.menu = RoundMenu(parent=self)
        self.menu.addActions([self.refresh])
        self.menu.addSeparator()
        self.menu.exec(e.globalPos())

    def switch_to(self, path: str):
        """
        展开并选中指定 path（必须存在于 file_tree 模型中）。
        """
        if not path or path == "/":
            return

        parts = _parse_linux_path(path)
        if not parts:
            return

        # 从根开始遍历
        root = self.tree.invisibleRootItem()
        current_item = None
        current_path = ""

        for i, part in enumerate(parts):
            if current_path:
                current_path = current_path.rstrip("/") + "/" + part
            else:
                current_path = "/" + part

            found = None
            # 遍历当前层的 child
            parent = root if current_item is None else current_item
            for j in range(parent.childCount()):
                child = parent.child(j)
                child_path = child.data(0, Qt.UserRole)
                if child_path == current_path:
                    found = child
                    break

            if found is None:
                print(f"switch_to: {current_path} not found in tree")
                return  # 找不到就提前退出

            # 展开目录（如果不是最后一层）

            found.setExpanded(True)

            current_item = found

        # 最后选中目标节点
        if current_item is not None:
            self.tree.setCurrentItem(current_item)
            self.tree.scrollToItem(current_item)
            current_item.setSelected(True)

    def _on_item_double_clicked(self, item, column):
        """双击 item 时，如果是目录则发射信号"""
        path = item.data(0, Qt.UserRole)
        if not path:
            return

        # 查找该 path 在内部模型中的类型
        node = self.file_tree.get('', {})
        parts = _parse_linux_path(path)
        for part in parts:
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                return

        # 如果是目录（dict 类型），发射信号
        if isinstance(node, dict):
            print(f"文件树被选择：{path}")
            self.directory_selected.emit(path)
