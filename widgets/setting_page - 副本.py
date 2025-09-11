# setting_page.py
import logging

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFontDatabase, QFont, QColor
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QFileDialog, QListWidget, QListWidgetItem,
    QLabel, QHBoxLayout, QSizePolicy, QFrame,  QDialog
)

from qfluentwidgets import (
    FluentIcon, ComboBoxSettingCard, OptionsConfigItem, Dialog, ScrollArea,
    SwitchSettingCard, PushSettingCard, QConfig, InfoBar, InfoBarPosition,
    LineEdit, RangeConfigItem, RangeValidator, RangeSettingCard,
    OptionsValidator, ColorDialog
)

from tools.font_config import font_config
from tools.setting_config import SCM

# qfluentwidgets (部分组件有可能在低版本中不存在，做兼容)
try:
    from qfluentwidgets import SearchLineEdit, PushButton
    _HAS_QFLUENT = True
except Exception:
    SearchLineEdit = None
    from PyQt5.QtWidgets import QPushButton as PushButton
    _HAS_QFLUENT = False

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
    fontSelected = pyqtSignal(str)

    def __init__(self, parent=None, title="选择字体", prompt="选择系统字体"):
        super().__init__(parent)
        self.parent = parent
        self.selected_font = None

        # 选择对话基类（qfluentwidgets.Dialog 或 QDialog）
        if _HAS_QFLUENT:
            self.dlg = Dialog(title, prompt, parent)
            self._is_qfluent = True
        else:
            self.dlg = QDialog(parent)
            self.dlg.setWindowTitle(title)
            self._is_qfluent = False

        # 内容容器（不包含底部确认/取消按钮）
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(8, 8, 8, 8)
        container_layout.setSpacing(8)

        # 搜索框（优先 SearchLineEdit）
        if SearchLineEdit is not None:
            self.search_box = SearchLineEdit(container)
        else:
            self.search_box = LineEdit(container)
            self.search_box.setPlaceholderText("搜索字体...")
        self.search_box.setFixedHeight(34)
        container_layout.addWidget(self.search_box)

        # 主显示区：字体列表 + 预览
        hbox = QHBoxLayout()
        hbox.setSpacing(8)

        self.list_widget = QListWidget()
        self.list_widget.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding)
        hbox.addWidget(self.list_widget, 3)

        preview_frame = QFrame()
        preview_layout = QVBoxLayout(preview_frame)
        preview_layout.setContentsMargins(8, 8, 8, 8)
        preview_layout.setSpacing(8)

        preview_label_title = QLabel("预览")
        preview_label_title.setAlignment(Qt.AlignCenter)
        preview_layout.addWidget(preview_label_title)

        self.preview_label = QLabel(
            "The quick brown fox jumps over the lazy dog 0123456789")
        self.preview_label.setWordWrap(True)
        self.preview_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.preview_label.setMinimumWidth(240)
        self.preview_label.setMinimumHeight(120)
        preview_layout.addWidget(self.preview_label, 1)

        self.size_label = QLabel("预览字号: 14")
        preview_layout.addWidget(self.size_label)
        hbox.addWidget(preview_frame, 2)

        container_layout.addLayout(hbox)

        # 如果没有 qfluentwidgets，我们需要在内容区添加自定义按钮（QDialog 用）
        if not self._is_qfluent:
            btn_layout = QHBoxLayout()
            btn_layout.addStretch(1)
            self.cancel_btn = PushButton("取消", container)
            self.ok_btn = PushButton("确定", container)
            btn_layout.addWidget(self.cancel_btn)
            btn_layout.addWidget(self.ok_btn)
            container_layout.addLayout(btn_layout)
        else:
            # qfluentwidgets.Dialog 自带按钮，直接引用它们（它们在 Dialog 实例上）
            # 注意：不同 qfluentwidgets 版本名称可能为 yesButton/cancelButton
            # 这里做一次安全获取
            try:
                self.ok_btn = self.dlg.yesButton
                self.cancel_btn = self.dlg.cancelButton
            except Exception:
                # 部分版本名字可能不同，尝试其它常用名字
                self.ok_btn = getattr(self.dlg, "okButton", None) or getattr(
                    self.dlg, "yesButton", None)
                self.cancel_btn = getattr(self.dlg, "closeButton", None) or getattr(
                    self.dlg, "cancelButton", None)

            # 设置按钮文本保证一致
            if hasattr(self.ok_btn, "setText"):
                try:
                    self.ok_btn.setText("确定")
                except Exception:
                    pass
            if hasattr(self.cancel_btn, "setText"):
                try:
                    self.cancel_btn.setText("取消")
                except Exception:
                    pass

        # 将 container 放入对话
        if self._is_qfluent:
            # qfluentwidgets 提供 setContentWidget 接口（标准用法）
            try:
                self.dlg.setContentWidget(container)
            except Exception:
                # 如果版本差异，退回到把 container 加进 layout
                try:
                    self.dlg.layout().addWidget(container)
                except Exception:
                    self.dlg.setLayout(container_layout)
        else:
            self.dlg.setLayout(container_layout)

        # 加载字体列表
        self._load_system_fonts()

        # 连接信号
        self.search_box.textChanged.connect(self._filter_fonts)
        self.list_widget.currentItemChanged.connect(self._on_selection_changed)
        self.list_widget.itemDoubleClicked.connect(
            self._on_item_double_clicked)
        # ok/cancel 连接（不论是内置按钮还是自建按钮，ok_btn/cancel_btn 已被赋值）
        if self.ok_btn is not None:
            self.ok_btn.clicked.connect(self._on_ok)
        if self.cancel_btn is not None:
            self.cancel_btn.clicked.connect(self._on_cancel)

        # 初始预览字号
        self._preview_size = 14
        self._apply_preview_font()

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
            self.list_widget.addItem(item)

    def _filter_fonts(self, text):
        if not text:
            self._populate_list(self.all_families)
            return
        lowered = text.lower()
        filtered = [f for f in self.all_families if lowered in f.lower()]
        self._populate_list(filtered)

    def _on_selection_changed(self, current, previous=None):
        if current:
            fam = current.text()
            self._update_preview(fam)

    def _on_item_double_clicked(self, item):
        if item:
            self.selected_font = item.text()
            # 发出信号
            self.fontSelected.emit(self.selected_font)
            self._accept()

    def _update_preview(self, family):
        try:
            font = QFont(family, self._preview_size)
            self.preview_label.setFont(font)
            self.size_label.setText(f"字号: {self._preview_size}")
        except Exception:
            pass

    def _apply_preview_font(self):
        cur_item = self.list_widget.currentItem()
        if cur_item:
            self._update_preview(cur_item.text())
        else:
            if self.list_widget.count() > 0:
                self.list_widget.setCurrentRow(0)
                self._update_preview(self.list_widget.item(0).text())

    def _on_ok(self):
        cur = self.list_widget.currentItem()
        if cur:
            self.selected_font = cur.text()
            # 发出信号
            self.fontSelected.emit(self.selected_font)
        self._accept()

    def _on_cancel(self):
        self.selected_font = None
        self._reject()

    # exec / accept / reject 封装，兼容两种对话类型
    def exec(self):
        if self._is_qfluent:
            return self.dlg.exec()
        else:
            return self.dlg.exec_()

    def _accept(self):
        if self._is_qfluent:
            try:
                self.dlg.accept()
            except Exception:
                self.dlg.done(1)
        else:
            self.dlg.accept()

    def _reject(self):
        if self._is_qfluent:
            try:
                self.dlg.reject()
            except Exception:
                self.dlg.done(0)
        else:
            self.dlg.reject()


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
        dlg = ColorDialog(QColor(0, 255, 255), "Choose Background Color",
                          self, enableAlpha=False)  # 初始颜色 & 父级
        dlg.colorChanged.connect(
            lambda color: self._set_color(color.name()))

        dlg.exec()

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
        font_dialog.exec()

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
