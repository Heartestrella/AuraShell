from PyQt5.QtCore import Qt, pyqtSignal, QRect, QPoint, QEvent, QStringListModel
from PyQt5.QtWidgets import QApplication, QHBoxLayout, QWidget
from qfluentwidgets import TextEdit, ListView, VBoxLayout, ToolButton, FluentIcon


class CommandInput(TextEdit):
    executeCommand = pyqtSignal(str)
    clear_history_ = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # 历史记录数据模型（不直接代表显示顺序，显示顺序由 _refresh_history_model 控制）
        self._history_model = QStringListModel()

        # 列表视图（放到 popup 内）
        self._history_view = ListView(None)
        self._history_view.setModel(self._history_model)
        self._history_view.setSelectionMode(ListView.SingleSelection)
        self._history_view.setEditTriggers(ListView.NoEditTriggers)
        self._history_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._history_view.clicked.connect(self._on_history_index_clicked)
        self._history_view.activated.connect(self._on_history_index_activated)
        # 列表不抢焦点（弹窗显示时输入框仍接收键入）
        self._history_view.setFocusPolicy(Qt.NoFocus)

        # ---- 历史记录弹窗容器（用 Qt.Tool，避免抢占输入法上下文） ----
        flags = Qt.Tool | Qt.FramelessWindowHint
        self._history_popup = QWidget(None, flags)
        self._history_popup.setAttribute(Qt.WA_TranslucentBackground, False)
        self._history_popup.setWindowOpacity(1.0)
        self._history_popup.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self._history_popup.setFocusPolicy(Qt.NoFocus)

        layout = VBoxLayout(self._history_popup)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 顶部工具栏（右上角扫把按钮）
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)

        clear_btn = ToolButton(FluentIcon.BROOM, self)
        clear_btn.setFixedSize(22, 22)
        clear_btn.setFocusPolicy(Qt.NoFocus)
        clear_btn.setToolTip("清空历史")
        clear_btn.setStyleSheet("""
            PushButton {
                border: none;
                color: rgb(180, 180, 180);
                font-weight: bold;
                background: transparent;
                font-size: 14px;
            }
            PushButton:hover {
                color: white;
                background-color: rgb(60, 60, 60);
                border-radius: 11px;
            }
        """)
        clear_btn.clicked.connect(self.clear_history)

        toolbar.addStretch()
        toolbar.addWidget(clear_btn)

        layout.addLayout(toolbar)
        layout.addWidget(self._history_view)

        # 样式美化（减小行高，减少上下间隙）
        self._history_popup.setStyleSheet("""
            QWidget {
                background-color: rgb(29, 29, 29);
                border: 1px solid rgb(50, 50, 50);
                border-radius: 8px;
            }
            ListView::item {
                height: 24px;
                padding: 2px 8px;
                color: rgb(220, 220, 220);
            }
            ListView::item:hover {
                background-color: rgb(45, 45, 45);
                border-radius: 4px;
            }
            ListView::item:selected {
                background-color: rgb(70, 70, 70);
                border-radius: 4px;
                color: white;
            }
        """)

        # 历史命令列表（原始顺序保存在这里）
        self._history = []

        # 安装全局事件过滤器（用于点击外部时关闭历史弹窗）
        QApplication.instance().installEventFilter(self)

        # 连接输入变化信号：实时匹配
        # QTextEdit 的 textChanged 是无参信号，使用 toPlainText() 获取内容
        self.textChanged.connect(self._on_text_changed)

    # ----------------- 历史管理 -----------------

    def add_history(self, cmd):
        if isinstance(cmd, (list, tuple)):
            for c in cmd:
                self.add_history(c)  # 递归调用添加每条
            return

        cmd = (cmd or "").strip()
        if not cmd:
            return

        # 去重并把最新放前（保留原始历史列表的语义）
        if cmd in self._history:
            self._history.remove(cmd)
        self._history.insert(0, cmd)

        # 刷新显示模型（保留当前输入的匹配上下文）
        self._refresh_history_model(self.toPlainText())

    def remove_history(self, cmd: str):
        while cmd in self._history:
            self._history.remove(cmd)
        self._refresh_history_model(self.toPlainText())

    def clear_history(self):
        self._history.clear()
        self._refresh_history_model(self.toPlainText())
        self.hide_history()
        self.clear_history_.emit()
    # ----------------- 实时匹配与刷新模型 -----------------

    def _on_text_changed(self):
        # 实时取当前输入并刷新 model 排序
        current = self.toPlainText()
        self._refresh_history_model(current)

    def _refresh_history_model(self, filter_text: str):
        """
        根据 filter_text 对 self._history 进行临时排序并写入 model。
        排序规则：startswith -> contains -> others（保持原始相对顺序）
        """
        if not self._history:
            self._history_model.setStringList([])
            return

        ft = (filter_text or "").strip().lower()

        if ft == "":
            # 空输入：恢复原始顺序
            display_list = list(self._history)
        else:
            starts = []
            contains = []
            others = []
            for idx, h in enumerate(self._history):
                h_lower = h.lower()
                if h_lower.startswith(ft):
                    starts.append((idx, h))
                elif ft in h_lower:
                    contains.append((idx, h))
                else:
                    others.append((idx, h))
            # 保持原始历史内的相对顺序（已通过 idx 保证）
            display_list = [h for _, h in starts] + \
                [h for _, h in contains] + [h for _, h in others]

        # 更新 model（不会改变 self._history）
        self._history_model.setStringList(display_list)

        # 如果 popup 可见，默认选中第一条（如果存在）
        if self._history_popup.isVisible():
            if self._history_model.rowCount() > 0:
                idx0 = self._history_model.index(0, 0)
                if idx0.isValid():
                    self._history_view.setCurrentIndex(idx0)

    # ----------------- 显示 / 隐藏 -----------------
    def show_history(self):
        if self._history_model.rowCount() == 0:
            return

        self._refresh_history_model(self.toPlainText())
        self._adjust_history_popup_position()
        self._history_popup.show()
        self._history_popup.raise_()
        self.setFocus()

        if not self._history_view.selectionModel().hasSelection():
            idx = self._history_model.index(0, 0)
            if idx.isValid():
                self._history_view.setCurrentIndex(idx)

    def hide_history(self):
        if self._history_popup.isVisible():
            self._history_popup.hide()
            self.setFocus()

    def toggle_history(self):
        if self._history_popup.isVisible():
            self.hide_history()
        else:
            self.show_history()

    # ----------------- 弹窗位置计算 -----------------
    def _adjust_history_popup_position(self):
        global_pos = self.mapToGlobal(QPoint(0, 0))
        input_rect = QRect(global_pos, self.size())

        screen = QApplication.screenAt(global_pos)
        screen_geom = screen.availableGeometry(
        ) if screen else QApplication.desktop().availableGeometry()

        count = max(0, self._history_model.rowCount())
        fm = self.fontMetrics()
        row_h = fm.height() + 4
        max_rows = min(10, max(1, count))
        popup_h = min(300, row_h * max_rows + 30)
        popup_w = max(self.width(), 220)

        x = input_rect.left()
        y_above = input_rect.top() - popup_h
        y_below = input_rect.bottom()

        if y_above >= screen_geom.top():
            y = y_above
        else:
            if y_below + popup_h <= screen_geom.bottom():
                y = y_below
            else:
                y = max(screen_geom.top(), screen_geom.bottom() - popup_h)

        self._history_popup.setGeometry(x, y, popup_w, popup_h)

    def keyPressEvent(self, event):
        # Esc 隐藏弹窗
        if event.key() == Qt.Key_Escape:
            self.hide_history()
            return

        # 如果 popup 可见，把方向键 / 回车 转发给 listview（即使输入框仍然聚焦）
        if self._history_popup.isVisible():
            if event.key() in (Qt.Key_Up, Qt.Key_Down, Qt.Key_Home, Qt.Key_End):
                QApplication.sendEvent(self._history_view, event)
                return
            elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
                self._on_history_index_activated()
                return

        # Alt 切换历史
        if event.key() == Qt.Key_Alt:
            self.toggle_history()
            return

        # 在输入的最开头按上箭头弹出历史（保留原行为）
        if event.key() == Qt.Key_Up:
            cursor = self.textCursor()
            at_start = cursor.position() == 0 and cursor.blockNumber() == 0
            if at_start:
                self.show_history()
                return

        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if not (event.modifiers() & Qt.ShiftModifier):
                command = self.toPlainText()
                self.executeCommand.emit(command)
                self.add_history(command)
                if command.strip():
                    self.add_history(command)
                self.clear()
                return
            else:
                super().keyPressEvent(event)
                return

        super().keyPressEvent(event)

    def focusOutEvent(self, event):
        new_focus = QApplication.focusWidget()
        if new_focus is None or not (
            new_focus is self._history_popup
            or self._history_popup.isAncestorOf(new_focus)
            or new_focus is self
            or self.isAncestorOf(new_focus)
        ):
            self.hide_history()
        super().focusOutEvent(event)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress:
            if self._history_popup.isVisible():
                w = QApplication.widgetAt(event.globalPos())
                if w is None:
                    self.hide_history()
                else:
                    if not (
                        w is self._history_popup
                        or self._history_popup.isAncestorOf(w)
                        or w is self
                        or self.isAncestorOf(w)
                    ):
                        self.hide_history()
        return super().eventFilter(obj, event)

    def _on_history_index_clicked(self, index):
        if index and index.isValid():
            self._fill_from_history(index.data())
            self.hide_history()

    def _on_history_index_activated(self, index=None):
        if index is None:
            index = self._history_view.currentIndex()
        if index and index.isValid():
            self._fill_from_history(index.data())
        self.hide_history()

    def _fill_from_history(self, cmd: str):
        self.setPlainText(cmd)
        cursor = self.textCursor()
        cursor.movePosition(cursor.End)
        self.setTextCursor(cursor)
        self.setFocus()

    def cleanup_history(self):
        try:
            QApplication.instance().removeEventFilter(self)
        except Exception:
            pass
        try:
            self._shortcut_toggle.activated.disconnect()
            self._shortcut_toggle.setParent(None)
        except Exception:
            pass
        try:
            self._history_popup.hide()
        except Exception:
            pass
