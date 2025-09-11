# setting_page.py
import logging

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFontDatabase, QFont, QColor, QPalette, QKeySequence
from PyQt5.QtWidgets import (
    QWidget, QDialog, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QLabel, QPushButton, QShortcut,
    QSizePolicy, QFrame, QFileDialog
)

from qfluentwidgets import (
    FluentIcon, ComboBoxSettingCard, OptionsConfigItem, SearchLineEdit, ScrollArea,
    SwitchSettingCard, PushSettingCard, QConfig, InfoBar, InfoBarPosition,
    LineEdit, RangeConfigItem, RangeValidator, RangeSettingCard,
    OptionsValidator, ColorDialog
)

from tools.font_config import font_config
from tools.setting_config import SCM


logger = logging.getLogger(__name__)

configer = SCM()


class Config(QConfig):
    # 跟随系统设置不知道怎么实现捏
    background_color = OptionsConfigItem(
        "MainWindow", "Color", "跟随系统设置", OptionsValidator(["浅色", "暗色", "跟随系统设置"]), restart=True)
    sizes = OptionsConfigItem(
        "MainWindow", "Sizes", "15", OptionsValidator([str(i) for i in range(12, 31)]), restart=True)
    opacity = RangeConfigItem("MainWindow", "Opacity",
                              100, RangeValidator(0, 100))


class FontSelectorDialog(QDialog):
    """
    Robust FontSelectorDialog that force-paints its own visible content area
    to avoid being turned into a 'black box' by global QSS.
    Replace your old FontSelectorDialog with this one.
    """
    fontSelected = pyqtSignal(str)

    def __init__(self, parent=None, title="选择字体", prompt="选择系统字体"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.selected_font = None
        self.setModal(True)
        self.resize(760, 520)

        # ---------------------------
        # Force window-level safe flags (avoid translucent backgrounds)
        # ---------------------------
        try:
            # ensure window isn't transparent due to global flags
            self.setAttribute(Qt.WA_TranslucentBackground, False)
            self.setWindowOpacity(1.0)
        except Exception:
            pass

        # ---------------------------
        # Build a content frame that we fully control the painting for.
        # We'll put all UI into `self.content` and force its palette/QSS.
        # ---------------------------
        self.content = QFrame(self)
        self.content.setObjectName("font_selector_content")
        self.content.setAutoFillBackground(True)
        self.content.setAttribute(Qt.WA_StyledBackground, True)

        # Choose explicit bg/text colors (white bg, dark text)
        self._bg = QColor("#ffffff")
        self._text = QColor("#111111")

        # Apply palette to content to ensure it paints background
        pal = self.content.palette()
        pal.setColor(QPalette.Window, self._bg)
        pal.setColor(QPalette.WindowText, self._text)
        pal.setColor(QPalette.Base, self._bg)
        pal.setColor(QPalette.Text, self._text)
        self.content.setPalette(pal)

        # Locally scoped stylesheet to further ensure visibility (targets only our content subtree)
        content_qss = f"""
        QFrame#font_selector_content {{ background: {self._bg.name()}; color: {self._text.name()}; }}
        QLineEdit {{ background: #ffffff; color: #000000; border: 1px solid rgba(0,0,0,0.12); border-radius:6px; }}
        QListWidget {{ background: #ffffff; color: #000000; }}
        QLabel {{ color: #000000; }}
        """
        # apply to the content frame only (this will style its children that inherit)
        self.content.setStyleSheet(content_qss)

        # main layout attaches the content frame
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.content)

        # content layout
        content_layout = QVBoxLayout(self.content)
        content_layout.setContentsMargins(14, 14, 14, 14)
        content_layout.setSpacing(10)

        # ---------------------------
        # Search box (prefer SearchLineEdit, fallback to LineEdit)
        # ---------------------------
        try:
            if 'SearchLineEdit' in globals() and SearchLineEdit is not None:
                self.search_box = SearchLineEdit(self.content)
            else:
                raise Exception()
        except Exception:
            # LineEdit imported in your module header earlier
            self.search_box = LineEdit(self.content)
            self.search_box.setPlaceholderText("搜索字体...")

        self.search_box.setFixedHeight(36)
        # enforce background/placeholder/text visibility
        self.search_box.setAutoFillBackground(True)
        self.search_box.setAttribute(Qt.WA_StyledBackground, True)
        # Palette
        sp = self.search_box.palette()
        sp.setColor(QPalette.Base, QColor("#ffffff"))
        sp.setColor(QPalette.Text, QColor("#000000"))
        try:
            sp.setColor(QPalette.PlaceholderText, QColor("#777777"))
        except Exception:
            pass
        self.search_box.setPalette(sp)
        # add explicit stylesheet to avoid global QSS interference
        self.search_box.setStyleSheet("""
            QLineEdit { background: #ffffff; color: #000000; border: 1px solid rgba(0,0,0,0.12); padding:6px; border-radius:6px; }
            QLineEdit:focus { border: 1px solid #168be6; }
        """)
        content_layout.addWidget(self.search_box)

        # ---------------------------
        # Central area: list + preview
        # ---------------------------
        hbox = QHBoxLayout()
        hbox.setSpacing(10)

        # font list
        self.list_widget = QListWidget(self.content)
        self.list_widget.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.list_widget.setAutoFillBackground(True)
        self.list_widget.setAttribute(Qt.WA_StyledBackground, True)

        # ensure viewport paints background
        try:
            vp = self.list_widget.viewport()
            vp.setAutoFillBackground(True)
            vpal = vp.palette()
            vpal.setColor(QPalette.Base, QColor("#ffffff"))
            vpal.setColor(QPalette.Text, QColor("#000000"))
            vp.setPalette(vpal)
        except Exception:
            pass

        hbox.addWidget(self.list_widget, 3)

        # preview
        preview_frame = QFrame(self.content)
        preview_frame.setAutoFillBackground(True)
        preview_frame.setAttribute(Qt.WA_StyledBackground, True)
        preview_layout = QVBoxLayout(preview_frame)
        preview_layout.setContentsMargins(8, 8, 8, 8)
        preview_layout.setSpacing(8)

        preview_label_title = QLabel("预览", preview_frame)
        preview_label_title.setAlignment(Qt.AlignCenter)
        preview_layout.addWidget(preview_label_title)

        self.preview_label = QLabel(
            "The quick brown fox jumps over the lazy dog 0123456789", preview_frame)
        self.preview_label.setWordWrap(True)
        self.preview_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.preview_label.setMinimumWidth(260)
        self.preview_label.setMinimumHeight(140)
        self.preview_label.setStyleSheet(
            "color: #000000; background: transparent;")
        preview_layout.addWidget(self.preview_label, 1)

        self.size_label = QLabel("预览字号: 14", preview_frame)
        self.size_label.setStyleSheet("color: #000000;")
        preview_layout.addWidget(self.size_label)
        hbox.addWidget(preview_frame, 2)

        content_layout.addLayout(hbox)

        # ---------------------------
        # Bottom controls: circular OK/Cancel (right aligned)
        # ---------------------------
        bottom_widget = QWidget(self.content)
        bottom_layout = QHBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.addStretch(1)

        # OK circular button
        self.ok_btn = QPushButton("✓", bottom_widget)
        self.ok_btn.setToolTip("确定 (Enter)")
        self.ok_btn.setCursor(Qt.PointingHandCursor)
        self.ok_btn.clicked.connect(self._on_ok)
        self.ok_btn.setDefault(True)
        self.ok_btn.setAutoDefault(True)
        self.ok_btn.setFixedSize(48, 48)
        self.ok_btn.setStyleSheet("""
            QPushButton {
                border-radius: 24px;
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #39a0ff, stop:1 #0078d4);
                color: white; font-weight:700; font-size:18px;
            }
            QPushButton:hover { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #4db3ff, stop:1 #168be6); }
            QPushButton:pressed { background: #006bb3; }
        """)
        bottom_layout.addWidget(self.ok_btn)
        bottom_layout.addSpacing(12)

        # Cancel circular button
        self.cancel_btn = QPushButton("✕", bottom_widget)
        self.cancel_btn.setToolTip("取消 (Esc)")
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.clicked.connect(self._on_cancel)
        self.cancel_btn.setFixedSize(48, 48)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                border-radius: 24px;
                background: transparent;
                border: 2px solid rgba(0,0,0,0.12);
                color: #222222; font-weight:700; font-size:16px;
            }
            QPushButton:hover { background: rgba(0,0,0,0.04); }
        """)
        bottom_layout.addWidget(self.cancel_btn)

        content_layout.addWidget(bottom_widget)

        # ---------------------------
        # Initialize fonts & signals
        # ---------------------------
        self._preview_size = 14
        self._load_system_fonts()
        self._apply_preview_font()

        self.search_box.textChanged.connect(self._filter_fonts)
        self.list_widget.currentItemChanged.connect(self._on_selection_changed)
        self.list_widget.itemDoubleClicked.connect(
            self._on_item_double_clicked)

        # Esc shortcut
        try:
            self.cancel_shortcut = QShortcut(QKeySequence(Qt.Key_Escape), self)
            self.cancel_shortcut.activated.connect(self._on_cancel)
        except Exception:
            pass

    # ---------------------------
    # font list helpers
    # ---------------------------
    def _load_system_fonts(self):
        db = QFontDatabase()
        families = db.families()
        families = sorted(families, key=lambda s: s.lower())
        self.all_families = families
        self._populate_list(self.all_families)

    def _populate_list(self, families):
        self.list_widget.clear()
        for fam in families:
            item = QListWidgetItem(fam)
            # explicitly set visible foreground
            item.setForeground(QColor("#000000"))
            self.list_widget.addItem(item)

    def _filter_fonts(self, text):
        if not text:
            self._populate_list(self.all_families)
            return
        lowered = text.lower()
        filtered = [f for f in self.all_families if lowered in f.lower()]
        self._populate_list(filtered)

    # ---------------------------
    # interaction
    # ---------------------------
    def _on_selection_changed(self, current, previous=None):
        if current:
            self._update_preview(current.text())

    def _on_item_double_clicked(self, item):
        if item:
            self.selected_font = item.text()
            try:
                self.fontSelected.emit(self.selected_font)
            except Exception:
                pass
            self.accept()

    def _update_preview(self, family):
        try:
            font = QFont(family, self._preview_size)
            self.preview_label.setFont(font)
            self.size_label.setText(f"预览字号: {self._preview_size}")
        except Exception:
            pass

    def _apply_preview_font(self):
        cur = self.list_widget.currentItem()
        if cur:
            self._update_preview(cur.text())
        else:
            if self.list_widget.count() > 0:
                self.list_widget.setCurrentRow(0)
                self._update_preview(self.list_widget.item(0).text())

    def _on_ok(self):
        cur = self.list_widget.currentItem()
        if cur:
            self.selected_font = cur.text()
            try:
                self.fontSelected.emit(self.selected_font)
            except Exception:
                pass
        self.accept()

    def _on_cancel(self):
        self.selected_font = None
        self.reject()


class SettingPage(ScrollArea):
    themeChanged = pyqtSignal(str)  # 发出选项变化信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Setting")
        self.logger = logging.getLogger("setting")
        # configer = SCM()
        self.config = configer.read_config()
        self.font_ = font_config()
        self.cfg = Config()
        self.parent_class = parent
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setAlignment(Qt.AlignTop)
        self.init_window_size = False
        self.Color_card = ComboBoxSettingCard(
            configItem=self.cfg.background_color,
            icon=FluentIcon.BRUSH,
            title="背景色调整",
            content="调整背景颜色",
            texts=["浅色", "暗色", "跟随系统设置"]
        )
        layout.addWidget(self.Color_card)

        self.bgCard = PushSettingCard(
            "选择背景图片",
            FluentIcon.PHOTO,
            "自定义背景",
            "设置自定义背景图片",
        )
        self.bgCard.clicked.connect(self._pick_bg)
        layout.addWidget(self.bgCard)

        self.opacityEdit = RangeSettingCard(
            self.cfg.opacity,
            FluentIcon.TRANSPARENT,
            title="背景不透明度",
            content="修改背景图片的不透明度"
        )
        self.opacityEdit.valueChanged.connect(self._save_opacity_value)
        layout.addWidget(self.opacityEdit)

        self.clearBgCard = PushSettingCard(
            "清除背景",
            FluentIcon.DELETE,
            "清除自定义背景",
            "恢复默认主题背景",
        )
        self.clearBgCard.clicked.connect(
            self.parent_class.clear_global_background)
        self.clearBgCard.clicked.connect(self._clear_bg_pic_to_config)
        layout.addWidget(self.clearBgCard)
        self.lock_ratio_card = SwitchSettingCard(
            icon=FluentIcon.LINK,              # 可以换成合适的图标
            title="锁定横纵比",
            content="生效于图片的比例",
            parent=self
        )
        self.lock_ratio_card.checkedChanged.connect(self.on_lock_ratio_changed)
        layout.addWidget(self.lock_ratio_card)

        self.cd_follow = SwitchSettingCard(
            icon=FluentIcon.ACCEPT,
            title="CD跟随目录",
            content="开启后文件管理器会跟随CD到的新目录 (Beta)",
            parent=self
        )
        self.cd_follow.checkedChanged.connect(self._set_cd_follow)
        layout.addWidget(self.cd_follow)

        self.font_select = PushSettingCard(
            "设置字体",
            FluentIcon.FONT,
            "修改终端字体 (需要重启软件)"
        )
        self.font_select.clicked.connect(self._select_font)
        layout.addWidget(self.font_select)

        self.font_size = ComboBoxSettingCard(
            configItem=self.cfg.sizes,
            icon=FluentIcon.FONT_SIZE,
            title="设置字体大小",
            content="修改终端字体大小 (需要重启软件)",
            texts=[str(i) for i in range(12, 31)]
        )
        self.font_size.comboBox.currentIndexChanged.connect(
            self._set_font_size)
        layout.addWidget(self.font_size)

        self.setWidget(container)
        self.setWidgetResizable(True)
        self.setStyleSheet("border: none;")

        self.cfg.background_color.valueChanged.connect(self._on_card_changed)

        self.choose_color = PushSettingCard(
            "打开取色器",
            FluentIcon.PENCIL_INK,
            "设置字体颜色",
            "设置SSH会话字体颜色(全局)"
        )
        self.choose_color.clicked.connect(self._open_color_dialog)
        layout.addWidget(self.choose_color)

        self.unbelievable_button = PushSettingCard(
            "点我延迟开学",
            FluentIcon.FONT,
            "字面意思"
        )
        self.unbelievable_button.clicked.connect(self._unbelievable)
        layout.addWidget(self.unbelievable_button)

        self._restore_saved_settings()

    def _save_opacity_value(self, value: int):
        configer.revise_config("background_opacity", value)

    def _unbelievable(self):
        InfoBar.error(
            title='想啥呢',
            content=f'''设置时间失败 \n date.set(month=7,day=1) \n Permissions error:Insufficient permissions''',
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=10000,
            parent=self
        )

    def _set_cd_follow(self):
        self.follow_ = self.cd_follow.switchButton.isChecked()
        configer.revise_config("follow_cd", self.follow_)

    def _clear_bg_pic_to_config(self):
        configer.revise_config("bg_pic", None)

    def on_lock_ratio_changed(self):
        self._lock_ratio = self.lock_ratio_card.switchButton.isChecked()
        configer.revise_config("locked_ratio", self._lock_ratio)

    def _restore_saved_settings(self):

        # Change interface value

        if self.config["bg_color"] == "Dark":
            color = "暗色"
        elif self.config["bg_color"] == "Light":
            color = "浅色"
        else:
            color = "跟随系统设置"

        self.cfg.background_color.value = color
        self.cfg.sizes.value = self.config["font_size"]
        self.lock_ratio_card.setChecked(self.config["locked_ratio"])
        self.cd_follow.setChecked(self.config["follow_cd"])
        self.parent_class.set_global_background(self.config["bg_pic"])
        self.opacityEdit.setValue(self.config["background_opacity"])
        # Achieve results
        self._lock_ratio = self.config["locked_ratio"]
        self._restore_background_opacity(self.config["background_opacity"])
        self._set_window_size(
            (self.config["window_last_width"], self.config["window_last_height"]))
        # self.themeChanged.emit(color)

    def _restore_background_opacity(self, value):
        parent = self.parent()
        while parent:
            if hasattr(parent, "set_background_opacity"):
                parent.set_background_opacity(value)
                break
            parent = parent.parent()

    def _set_color(self, color: str):
        parent = self.parent()
        while parent:
            if hasattr(parent, "set_ssh_session_text_color"):
                parent.set_ssh_session_text_color(color)
                break
            parent = parent.parent()
        configer.revise_config("ssh_widget_text_color", color)
        InfoBar.success(
            title='颜色变更成功',
            content='',
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=2000,
            parent=self
        )

    def _open_color_dialog(self):
        dlg = ColorDialog(QColor(0, 255, 255), "选择颜色",
                          self, enableAlpha=False)
        dlg.colorChanged.connect(lambda color: self._set_color(color.name()))
        dlg.exec_()

    def _on_card_changed(self, value):
        self.themeChanged.emit(value)
        value = (
            "Light" if value == "浅色" else
            "Dark" if value == "暗色" else
            value
        )
        configer.revise_config("bg_color", value)

    def _set_font_size(self, index: int):
        size = int(self.font_size.comboBox.currentText())
        # print("选择的字号:", size)
        self.font_.write_font(font_size=size)
        configer.revise_config("font_size", str(size))

    def _pick_bg(self):
        """选择背景图片"""

        path, _ = QFileDialog.getOpenFileName(
            self, "选择背景图片", "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        print(f"已选择背景文件：{path}")
        if not path:
            return
        else:
            configer.revise_config("bg_pic", path)
            self.parent_class.set_global_background(path)

    def _select_font(self):
        """打开文件资源管理器选择字体文件并保存配置"""
        font_dialog = FontSelectorDialog(self)
        font_dialog.fontSelected.connect(self.on_font_selected)
        font_dialog.exec_()

    def on_font_selected(self, font_name):
        """处理字体选择信号"""
        print(f"选择的字体: {font_name}")
        self.font_.write_font(font_path=font_name)

    def save_window_size(self, sizes: tuple):
        width, height = sizes
        configer.revise_config("window_last_width", width)
        configer.revise_config("window_last_height", height)

    def _set_window_size(self, sizes: tuple):
        width, height = sizes
        self.parent().resize(width, height)
        self.init_window_size = True

    def _restart(self):
        pass
