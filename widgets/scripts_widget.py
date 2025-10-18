from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QGridLayout, QFileDialog)
from PyQt5.QtCore import Qt, pyqtSignal, QSize

from datetime import datetime
import json
import os
from pathlib import Path
from qfluentwidgets import (PrimaryPushButton, PushButton, ToolButton, LineEdit, TextEdit, MessageBox,
                            FluentIcon as FIF, ScrollArea, InfoBar, SearchLineEdit, ComboBox, CardWidget,
                            StrongBodyLabel, BodyLabel, CaptionLabel, CheckBox, SpinBox, Dialog)

SCRIPTS_DIR = Path.home() / ".config" / "pyqt-ssh"


class CommandScriptWindow(QWidget):
    saveRequested = pyqtSignal(dict)

    def __init__(self, parent=None, script_data=None, categories=None):
        super().__init__(parent)
        self.script_data = script_data or {}
        self.categories = categories or []
        self.is_edit_mode = bool(script_data)
        self.original_name = script_data.get('name', '') if script_data else ''

        # 设置窗口属性 - 移除帮助按钮，使用默认层级
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint |
                            Qt.WindowCloseButtonHint)
        self.setWindowTitle(self.tr("Edit Script")
                            if self.is_edit_mode else self.tr("Add Script"))
        self.setMinimumSize(600, 500)

        # 设置协调的暗色主题
        self.setup_dark_theme()

        self.setup_ui()

    def setup_dark_theme(self):
        """设置协调的暗色主题样式"""
        self.setStyleSheet(""" 
            CommandScriptWindow {
                background-color: #1e1e1e;
                color: #e8e8e8;
            }
            
            StrongBodyLabel, BodyLabel {
                color: #e8e8e8;
            }
            
            CaptionLabel {
                color: #a0a0a0;
            }
            
            LineEdit {
                background-color: #2d2d2d;
                border: 1px solid #3e3e3e;
                border-radius: 6px;
                padding: 8px 12px;
                color: #e8e8e8;
                font-size: 14px;
                selection-background-color: #0078d4;
            }
            
            LineEdit:focus {
                border: 1px solid #0078d4;
                background-color: #252525;
            }
            
            LineEdit:disabled {
                background-color: #2a2a2a;
                color: #707070;
            }
            
            TextEdit {
                background-color: #2d2d2d;
                border: 1px solid #3e3e3e;
                border-radius: 6px;
                padding: 12px;
                color: #e8e8e8;
                font-size: 13px;
                font-family: 'Cascadia Code', 'Consolas', 'Monaco', monospace;
                selection-background-color: #0078d4;
            }
            
            TextEdit:focus {
                border: 1px solid #0078d4;
                background-color: #252525;
            }
            
            PushButton {
                background-color: #323232;
                border: 1px solid #404040;
                border-radius: 6px;
                padding: 10px 20px;
                color: #e8e8e8;
                font-size: 14px;
                font-weight: 500;
            }
            
            PushButton:hover {
                background-color: #3a3a3a;
                border-color: #4a4a4a;
            }
            
            PushButton:pressed {
                background-color: #282828;
            }
            
            PrimaryPushButton {
                background-color: #0078d4;
                border: 1px solid #0078d4;
                border-radius: 6px;
                padding: 10px 20px;
                color: #ffffff;
                font-size: 14px;
                font-weight: 500;
            }
            
            PrimaryPushButton:hover {
                background-color: #106ebe;
                border-color: #106ebe;
            }
            
            PrimaryPushButton:pressed {
                background-color: #005a9e;
            }
            
            ToolButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
                color: #cccccc;
            }
            
            ToolButton:hover {
                background-color: #383838;
            }
            
            ToolButton:pressed {
                background-color: #2a2a2a;
            }
            
            CheckBox {
                color: #e8e8e8;
                spacing: 8px;
                font-size: 14px;
            }
            
            CheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #555555;
                border-radius: 4px;
                background-color: #2d2d2d;
            }
            
            CheckBox::indicator:hover {
                border-color: #666666;
            }
            
            CheckBox::indicator:checked {
                background-color: #0078d4;
                border-color: #0078d4;
            }
            
            CheckBox::indicator:checked:hover {
                background-color: #106ebe;
                border-color: #106ebe;
            }
            
            SpinBox {
                background-color: #2d2d2d;
                border: 1px solid #3e3e3e;
                border-radius: 6px;
                padding: 8px 12px;
                color: #e8e8e8;
                font-size: 14px;
            }
            
            SpinBox:focus {
                border: 1px solid #0078d4;
                background-color: #252525;
            }
            
            SpinBox::up-button, SpinBox::down-button {
                background-color: #383838;
                border: 1px solid #454545;
                border-radius: 3px;
                width: 20px;
                margin: 2px;
            }
            
            SpinBox::up-button:hover, SpinBox::down-button:hover {
                background-color: #404040;
            }
            
            SpinBox::up-button:pressed, SpinBox::down-button:pressed {
                background-color: #2a2a2a;
            }
            
            CardWidget {
                background-color: #252525;
                border: 1px solid #383838;
                border-radius: 8px;
            }
        """)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 基本信息卡片
        basic_card = CardWidget()
        basic_card_layout = QVBoxLayout(basic_card)
        basic_card_layout.setContentsMargins(20, 15, 20, 15)
        basic_card_layout.setSpacing(12)

        basic_title = StrongBodyLabel(self.tr("Basic Information"))
        basic_title.setStyleSheet("font-size: 14px; font-weight: 600;")
        basic_card_layout.addWidget(basic_title)

        form_layout = QGridLayout()
        form_layout.setVerticalSpacing(12)
        form_layout.setHorizontalSpacing(15)

        form_layout.addWidget(BodyLabel(self.tr("Name:")), 0, 0, Qt.AlignRight)
        self.name_edit = LineEdit()
        self.name_edit.setPlaceholderText(self.tr("Required"))
        self.name_edit.setClearButtonEnabled(True)
        form_layout.addWidget(self.name_edit, 0, 1)

        form_layout.addWidget(
            BodyLabel(self.tr("Description:")), 1, 0, Qt.AlignRight)
        self.desc_edit = LineEdit()
        self.desc_edit.setPlaceholderText(self.tr("Optional"))
        self.desc_edit.setClearButtonEnabled(True)
        form_layout.addWidget(self.desc_edit, 1, 1)

        form_layout.addWidget(
            BodyLabel(self.tr("Category:")), 2, 0, Qt.AlignRight)
        category_layout = QHBoxLayout()
        self.category_edit = LineEdit()
        self.category_edit.setPlaceholderText(self.tr("Enter category"))
        self.category_edit.setClearButtonEnabled(True)
        category_layout.addWidget(self.category_edit)

        self.add_category_btn = ToolButton(FIF.ADD)
        self.add_category_btn.setToolTip(self.tr("Use this category"))
        self.add_category_btn.setFixedSize(32, 32)
        category_layout.addWidget(self.add_category_btn)
        category_layout.addStretch(1)
        form_layout.addLayout(category_layout, 2, 1)

        basic_card_layout.addLayout(form_layout)
        layout.addWidget(basic_card)

        # 命令内容卡片
        command_card = CardWidget()
        command_card_layout = QVBoxLayout(command_card)
        command_card_layout.setContentsMargins(20, 15, 20, 15)
        command_card_layout.setSpacing(12)

        command_title = StrongBodyLabel(self.tr("Command Content"))
        command_title.setStyleSheet("font-size: 14px; font-weight: 600;")
        command_card_layout.addWidget(command_title)

        command_desc = CaptionLabel(self.tr(
            "Enter commands to execute, use semicolon or newline to separate multiple commands"))
        command_card_layout.addWidget(command_desc)

        self.command_edit = TextEdit()
        self.command_edit.setPlaceholderText(
            self.tr("Enter command content..."))
        self.command_edit.setMinimumHeight(120)
        self.command_edit.setMaximumHeight(200)
        command_card_layout.addWidget(self.command_edit)

        layout.addWidget(command_card)

        # 高级选项卡片
        advanced_card = CardWidget()
        advanced_card_layout = QVBoxLayout(advanced_card)
        advanced_card_layout.setContentsMargins(20, 15, 20, 15)
        advanced_card_layout.setSpacing(12)

        advanced_header = QHBoxLayout()
        advanced_title = StrongBodyLabel(self.tr("Advanced Options"))
        advanced_title.setStyleSheet("font-size: 14px; font-weight: 600;")

        self.advanced_toggle = ToolButton(FIF.CHEVRON_RIGHT_MED)
        self.advanced_toggle.setCheckable(True)
        self.advanced_toggle.setToolTip(self.tr("Show/Hide advanced options"))

        advanced_header.addWidget(advanced_title)
        advanced_header.addStretch(1)
        advanced_header.addWidget(self.advanced_toggle)
        advanced_card_layout.addLayout(advanced_header)

        self.advanced_content = QWidget()
        advanced_content_layout = QGridLayout(self.advanced_content)
        advanced_content_layout.setContentsMargins(0, 10, 0, 0)
        advanced_content_layout.setVerticalSpacing(10)
        advanced_content_layout.setHorizontalSpacing(15)

        advanced_content_layout.addWidget(
            BodyLabel(self.tr("Timeout:")), 0, 0, Qt.AlignRight)
        timeout_layout = QHBoxLayout()
        self.timeout_spin = SpinBox()
        self.timeout_spin.setRange(0, 3600)
        self.timeout_spin.setValue(30)
        self.timeout_spin.setSuffix(self.tr(" seconds"))
        self.timeout_spin.setToolTip(self.tr("0 means no timeout"))
        timeout_layout.addWidget(self.timeout_spin)
        timeout_layout.addStretch(1)
        advanced_content_layout.addLayout(timeout_layout, 0, 1)

        self.confirm_check = CheckBox(self.tr("Confirm before execution"))
        self.confirm_check.setToolTip(
            self.tr("Show confirmation dialog before executing this script"))
        advanced_content_layout.addWidget(self.confirm_check, 1, 0, 1, 2)

        self.auto_execute_check = CheckBox(
            self.tr("Execute automatically after creation"))
        self.auto_execute_check.setToolTip(
            self.tr("Execute script automatically after saving"))
        advanced_content_layout.addWidget(self.auto_execute_check, 2, 0, 1, 2)

        advanced_card_layout.addWidget(self.advanced_content)
        self.advanced_content.hide()

        layout.addWidget(advanced_card)
        layout.addStretch(1)

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch(1)

        self.cancel_btn = PushButton(self.tr("Cancel"))
        self.save_btn = PrimaryPushButton(self.tr("Save"))

        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.save_btn)

        layout.addLayout(button_layout)

        self.set_initial_values()

        # 连接信号
        self.save_btn.clicked.connect(self.on_save)
        self.cancel_btn.clicked.connect(self.close)
        self.add_category_btn.clicked.connect(self.use_category)
        self.advanced_toggle.toggled.connect(self.toggle_advanced)

    def set_initial_values(self):
        if self.script_data:
            self.name_edit.setText(self.script_data.get('name', ''))
            self.desc_edit.setText(self.script_data.get('description', ''))
            self.command_edit.setText(self.script_data.get('command', ''))
            self.timeout_spin.setValue(self.script_data.get('timeout', 30))
            self.confirm_check.setChecked(
                self.script_data.get('confirm', False))
            self.auto_execute_check.setChecked(
                self.script_data.get('auto_execute', False))

            category = self.script_data.get('category', '')
            if category:
                self.category_edit.setText(category)

        if self.is_edit_mode:
            self.auto_execute_check.setEnabled(False)
            self.auto_execute_check.setToolTip(
                self.tr("Auto execute not available in edit mode"))

    def toggle_advanced(self, checked):
        self.advanced_content.setVisible(checked)
        self.advanced_toggle.setIcon(
            FIF.CHEVRON_DOWN_MED if checked else FIF.CHEVRON_RIGHT_MED)
        if checked:
            self.setMinimumHeight(650)
        else:
            self.setMinimumHeight(500)

    def use_category(self):
        current_text = self.category_edit.text().strip()
        if current_text:
            InfoBar.success(self.tr("Success"), self.tr(
                "Category set"), duration=1500, parent=self)

    def on_save(self):
        script_data = self.get_script_data()

        if not script_data['name']:
            self.show_error(self.tr("Script name cannot be empty"))
            return

        if not script_data['command']:
            self.show_error(self.tr("Command content cannot be empty"))
            return

        self.saveRequested.emit(script_data)
        self.close()

    def get_script_data(self):
        data = {
            'name': self.name_edit.text().strip(),
            'description': self.desc_edit.text().strip(),
            'category': self.category_edit.text().strip(),
            'command': self.command_edit.toPlainText().strip(),
            'timeout': self.timeout_spin.value(),
            'confirm': self.confirm_check.isChecked(),
            'auto_execute': self.auto_execute_check.isChecked()
        }

        if self.is_edit_mode:
            data['original_name'] = self.original_name

        return data

    def show_error(self, message):
        InfoBar.error(self.tr("Error"), message, duration=3000, parent=self)

    def showEvent(self, event):
        """显示事件，用于居中窗口"""
        super().showEvent(event)

        # 居中显示
        if self.parent():
            parent_rect = self.parent().frameGeometry()
            my_rect = self.frameGeometry()
            my_rect.moveCenter(parent_rect.center())
            self.move(my_rect.topLeft())


class CommandScriptItem(CardWidget):
    itemClicked = pyqtSignal(dict)
    itemEditRequested = pyqtSignal(dict)
    itemDeleteRequested = pyqtSignal(dict)
    itemExecuteRequested = pyqtSignal(dict)

    def __init__(self, script_data, parent=None):
        super().__init__(parent)
        self.script_data = script_data
        self.setup_ui()

    def setup_ui(self):
        self.setFixedHeight(120)
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)

        # 第一行：名称和操作按钮
        first_row = QHBoxLayout()

        # 名称
        self.name_label = StrongBodyLabel(self.script_data.get('name', ''))
        self.name_label.setStyleSheet(
            "font-size: 15px; font-weight: 600; color: #e8e8e8;")

        first_row.addWidget(self.name_label)
        first_row.addStretch(1)

        # 操作按钮
        button_layout = QHBoxLayout()
        button_layout.setSpacing(4)

        self.execute_btn = ToolButton(FIF.PLAY)
        self.execute_btn.setToolTip(self.tr("Execute"))
        self.execute_btn.setFixedSize(28, 28)
        self.execute_btn.setStyleSheet(
            "ToolButton { background-color: rgba(0, 120, 212, 0.1); }")

        self.edit_btn = ToolButton(FIF.EDIT)
        self.edit_btn.setToolTip(self.tr("Edit"))
        self.edit_btn.setFixedSize(28, 28)

        self.delete_btn = ToolButton(FIF.DELETE)
        self.delete_btn.setToolTip(self.tr("Delete"))
        self.delete_btn.setFixedSize(28, 28)
        self.delete_btn.setStyleSheet(
            "ToolButton { background-color: rgba(232, 17, 35, 0.1); }")

        button_layout.addWidget(self.execute_btn)
        button_layout.addWidget(self.edit_btn)
        button_layout.addWidget(self.delete_btn)
        first_row.addLayout(button_layout)

        layout.addLayout(first_row)

        # 第二行：分类和描述
        second_row = QHBoxLayout()

        # 分类标签
        category = self.script_data.get('category', '')
        if category:
            self.category_label = CaptionLabel(category)
            self.category_label.setStyleSheet("""
                color: #0078D4; 
                background-color: rgba(0, 120, 212, 0.15);
                padding: 3px 10px;
                border-radius: 12px;
                font-size: 11px;
                font-weight: 500;
            """)
        else:
            self.category_label = CaptionLabel(self.tr("Uncategorized"))
            self.category_label.setStyleSheet("""
                color: #a0a0a0;
                background-color: rgba(160, 160, 160, 0.15);
                padding: 3px 10px;
                border-radius: 12px;
                font-size: 11px;
                font-weight: 500;
            """)

        second_row.addWidget(self.category_label)

        # 描述
        description = self.script_data.get('description', '')
        if description:
            self.desc_label = BodyLabel(description)
            self.desc_label.setStyleSheet(
                "color: #a0a0a0; font-size: 12px; margin-left: 8px;")
            self.desc_label.setWordWrap(True)
            second_row.addWidget(self.desc_label, 1)

        second_row.addStretch(1)
        layout.addLayout(second_row)

        # 第三行：命令预览
        command = self.script_data.get('command', '')
        if command:
            preview = command[:100] + "..." if len(command) > 100 else command
            self.command_label = CaptionLabel(preview)
            self.command_label.setStyleSheet("""
                color: #888; 
                font-family: 'Cascadia Code', 'Consolas', 'Monaco', monospace;
                font-size: 11px;
                background-color: rgba(255, 255, 255, 0.03);
                padding: 6px 8px;
                border-radius: 4px;
                border-left: 3px solid #0078d4;
                margin-top: 4px;
            """)
            self.command_label.setWordWrap(True)
            layout.addWidget(self.command_label)

        layout.addStretch(1)

        # 底部信息栏
        bottom_layout = QHBoxLayout()

        # 高级选项指示器
        if self.script_data.get('timeout', 30) != 30 or self.script_data.get('confirm', False):
            advanced_indicator = CaptionLabel(self.tr("⚙ Advanced"))
            advanced_indicator.setStyleSheet(
                "color: #FFB900; font-size: 11px;")
            bottom_layout.addWidget(advanced_indicator)

        bottom_layout.addStretch(1)

        # 时间信息
        created_time = self.script_data.get('created_time', '')
        time_text = created_time if created_time else self.tr(
            "Recently created")
        time_info = CaptionLabel(time_text)
        time_info.setStyleSheet("color: #666; font-size: 10px;")
        bottom_layout.addWidget(time_info)

        layout.addLayout(bottom_layout)

        # 连接信号
        self.execute_btn.clicked.connect(
            lambda: self.itemExecuteRequested.emit(self.script_data))
        self.edit_btn.clicked.connect(
            lambda: self.itemEditRequested.emit(self.script_data))
        self.delete_btn.clicked.connect(
            lambda: self.itemDeleteRequested.emit(self.script_data))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.itemClicked.emit(self.script_data)
        super().mousePressEvent(event)


class CommandScriptWidget(QWidget):
    scriptSelected = pyqtSignal(str)
    scriptExecuteRequested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scripts_file = SCRIPTS_DIR / "command_scripts.json"
        self.export_dir = "_ssh_download"
        self.scripts_data = []
        self.setup_ui()
        self.load_scripts()

    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.show_list_view()

    def show_list_view(self):
        self.clear_layout()

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        toolbar = QFrame()
        toolbar.setObjectName("toolbar")
        toolbar.setFixedHeight(60)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(20, 0, 20, 0)

        title_label = StrongBodyLabel(self.tr("Command Scripts"))
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")

        self.search_edit = SearchLineEdit()
        self.search_edit.setPlaceholderText(self.tr("Search scripts..."))
        self.search_edit.setFixedWidth(220)

        self.category_combo = ComboBox()
        self.category_combo.setPlaceholderText(self.tr("All categories"))
        self.category_combo.setMinimumWidth(140)

        self.add_btn = PrimaryPushButton(FIF.ADD, self.tr("New Script"))
        self.import_btn = PushButton(FIF.DOWNLOAD, self.tr("Import"))
        self.export_btn = PushButton(FIF.SHARE, self.tr("Export"))

        toolbar_layout.addWidget(title_label)
        toolbar_layout.addStretch(1)
        toolbar_layout.addWidget(self.search_edit)
        toolbar_layout.addWidget(self.category_combo)
        toolbar_layout.addWidget(self.import_btn)
        toolbar_layout.addWidget(self.export_btn)
        toolbar_layout.addWidget(self.add_btn)

        layout.addWidget(toolbar)

        self.scroll_area = ScrollArea()
        self.scroll_area.setObjectName("scriptScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.list_widget = QWidget()
        self.list_layout = QVBoxLayout(self.list_widget)
        self.list_layout.setContentsMargins(20, 20, 20, 20)
        self.list_layout.setSpacing(12)
        self.list_layout.addStretch(1)

        self.scroll_area.setWidget(self.list_widget)
        layout.addWidget(self.scroll_area, 1)

        self.empty_widget = QWidget()
        empty_layout = QVBoxLayout(self.empty_widget)
        empty_layout.setAlignment(Qt.AlignCenter)

        empty_icon = QLabel("📝")
        empty_icon.setStyleSheet("font-size: 48px;")
        empty_icon.setAlignment(Qt.AlignCenter)

        empty_label = StrongBodyLabel(self.tr("No scripts"))
        empty_label.setAlignment(Qt.AlignCenter)
        empty_label.setStyleSheet("font-size: 16px; margin: 10px;")

        empty_desc = BodyLabel(
            self.tr("Click 'New Script' to create your first command script"))
        empty_desc.setAlignment(Qt.AlignCenter)
        empty_desc.setStyleSheet("color: gray; margin: 5px;")

        empty_layout.addWidget(empty_icon)
        empty_layout.addWidget(empty_label)
        empty_layout.addWidget(empty_desc)
        empty_layout.addStretch(1)

        self.list_layout.insertWidget(0, self.empty_widget)

        self.main_layout.addLayout(layout)

        self.add_btn.clicked.connect(self.show_add_script_dialog)
        self.search_edit.textChanged.connect(self.filter_scripts)
        self.category_combo.currentTextChanged.connect(self.filter_scripts)
        self.import_btn.clicked.connect(self.import_scripts)
        self.export_btn.clicked.connect(self.export_scripts)

        self.setStyleSheet("""
            #toolbar {
                background-color: rgba(255, 255, 255, 0.03);
                border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            }
            #scriptScrollArea {
                border: none;
                background-color: transparent;
            }
        """)

    def import_scripts(self):
        """从文件导入脚本 - 用户选择文件"""
        try:
            # 打开文件选择对话框
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                self.tr("Import Scripts"),
                "",  # 从当前目录开始
                self.tr("JSON Files (*.json);;All Files (*)")
            )

            if not file_path:
                return False  # 用户取消了选择

            # 读取文件
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)

            # 验证文件格式
            if "scripts" not in import_data:
                self.show_error(
                    self.tr("Import Failed"),
                    self.tr("Invalid script file format")
                )
                return False

            scripts_to_import = import_data.get("scripts", [])
            if not scripts_to_import:
                self.show_info(
                    self.tr("Import Info"),
                    self.tr("No scripts found in the import file")
                )
                return True

            # 导入脚本
            imported_count = 0
            skipped_count = 0

            for script in scripts_to_import:
                if self._import_single_script(script):
                    imported_count += 1
                else:
                    skipped_count += 1

            # 保存更新后的数据
            if imported_count > 0:
                self.save_scripts()
                self.refresh_list()
                self.update_category_combo()

            # 显示导入结果
            if imported_count > 0:
                self.show_success(
                    self.tr("Import Successful"),
                    self.tr("Imported {} scripts, skipped {} duplicates").format(
                        imported_count, skipped_count)
                )
            else:
                self.show_info(
                    self.tr("Import Complete"),
                    self.tr("No new scripts imported ({} duplicates skipped)").format(
                        skipped_count)
                )

            return True

        except Exception as e:
            self.show_error(
                self.tr("Import Failed"),
                self.tr("Failed to import scripts: {}").format(str(e))
            )
            return False

    def export_scripts(self):
        """导出所有脚本到文件 - 用户选择保存位置"""
        try:
            # 打开文件保存对话框
            default_filename = f"command_scripts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                self.tr("Export Scripts"),
                default_filename,
                self.tr("JSON Files (*.json);;All Files (*)")
            )

            if not file_path:
                return False  # 用户取消了选择

            # 确保文件扩展名
            if not file_path.endswith('.json'):
                file_path += '.json'

            # 准备导出数据
            export_data = {
                "export_info": {
                    "version": "1.0",
                    "export_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "total_scripts": len(self.scripts_data),
                    "app_name": "PSSH Command Scripts"
                },
                "scripts": self.scripts_data
            }

            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)

            # 显示成功信息
            self.show_success(
                self.tr("Export Successful"),
                self.tr("Scripts exported to: {}").format(file_path)
            )

            return True

        except Exception as e:
            self.show_error(
                self.tr("Export Failed"),
                self.tr("Failed to export scripts: {}").format(str(e))
            )
            return False

    def show_add_script_dialog(self):
        categories = self.get_all_categories()

        # 创建独立窗口
        self.script_window = CommandScriptWindow(
            self.window(), categories=categories)
        self.script_window.saveRequested.connect(self.on_script_saved)
        self.script_window.show()

    def show_edit_script_dialog(self, script_data):
        categories = self.get_all_categories()

        # 创建独立窗口
        self.script_window = CommandScriptWindow(
            self.window(), script_data=script_data, categories=categories)
        self.script_window.saveRequested.connect(self.on_script_updated)
        self.script_window.show()

    def on_script_saved(self, script_data):
        if any(s['name'] == script_data['name'] for s in self.scripts_data):
            self.show_error(self.tr("Error"), self.tr(
                "Script name already exists"))
            return

        # 添加创建时间戳
        script_data['created_time'] = datetime.now().strftime("%Y-%m-%d %H:%M")

        self.scripts_data.append(script_data)
        if self.save_scripts():
            self.refresh_list()
            self.update_category_combo()
            self.show_success(self.tr("Success"), self.tr("Script created"))

            if script_data.get('auto_execute', False):
                self.scriptExecuteRequested.emit(script_data['command'])

    def on_script_updated(self, script_data):
        original_name = script_data.get('original_name', '')
        if not original_name:
            self.show_error(self.tr("Error"), self.tr("Script not found"))
            return

        if any(s['name'] == script_data['name'] and s['name'] != original_name for s in self.scripts_data):
            self.show_error(self.tr("Error"), self.tr(
                "Script name already exists"))
            return

        from datetime import datetime
        script_data['modified_time'] = datetime.now().strftime(
            "%Y-%m-%d %H:%M")

        for i, script in enumerate(self.scripts_data):
            if script.get('name') == original_name:
                # 保留原有的创建时间
                if 'created_time' in script:
                    script_data['created_time'] = script['created_time']
                self.scripts_data[i] = script_data
                break

        if self.save_scripts():
            self.refresh_list()
            self.update_category_combo()
            self.show_success(self.tr("Success"), self.tr("Script updated"))

    def clear_layout(self):
        while self.main_layout.count():
            item = self.main_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self.clear_sublayout(item.layout())

    def clear_sublayout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self.clear_sublayout(item.layout())

    def load_scripts(self):
        try:
            if os.path.exists(self.scripts_file):
                with open(self.scripts_file, 'r', encoding='utf-8') as f:
                    self.scripts_data = json.load(f)
            else:
                self.scripts_data = []
        except:
            self.scripts_data = []

        self.refresh_list()
        self.update_category_combo()

    def save_scripts(self):
        try:
            with open(self.scripts_file, 'w', encoding='utf-8') as f:
                json.dump(self.scripts_data, f, ensure_ascii=False, indent=2)
            return True
        except:
            return False

    def refresh_list(self):
        for i in reversed(range(self.list_layout.count())):
            item = self.list_layout.itemAt(i)
            if item.widget() and item.widget() != self.empty_widget:
                item.widget().deleteLater()

        has_scripts = bool(self.scripts_data)
        self.empty_widget.setVisible(not has_scripts)

        if has_scripts:
            for script in self.scripts_data:
                item_widget = CommandScriptItem(script)
                item_widget.itemClicked.connect(self.on_script_clicked)
                item_widget.itemEditRequested.connect(
                    self.show_edit_script_dialog)
                item_widget.itemDeleteRequested.connect(self.delete_script)
                item_widget.itemExecuteRequested.connect(
                    self.on_script_execute)
                self.list_layout.insertWidget(
                    self.list_layout.count() - 1, item_widget)

    def update_category_combo(self):
        self.category_combo.clear()
        self.category_combo.addItem(self.tr("All categories"))

        categories = set()
        for script in self.scripts_data:
            category = script.get('category', '')
            if category:
                categories.add(category)

        for category in sorted(categories):
            self.category_combo.addItem(category)

    def filter_scripts(self):
        search_text = self.search_edit.text().lower()
        selected_category = self.category_combo.currentText()

        visible_count = 0

        for i in range(self.list_layout.count()):
            item = self.list_layout.itemAt(i)
            widget = item.widget()
            if isinstance(widget, CommandScriptItem):
                script = widget.script_data
                name_match = search_text in script.get('name', '').lower()
                desc_match = search_text in script.get(
                    'description', '').lower()
                command_match = search_text in script.get(
                    'command', '').lower()

                category_match = True
                if selected_category and selected_category != self.tr("All categories"):
                    category_match = script.get(
                        'category', '') == selected_category

                visible = (
                    name_match or desc_match or command_match) and category_match
                widget.setVisible(visible)

                if visible:
                    visible_count += 1

        self.empty_widget.setVisible(visible_count == 0)

    def on_script_clicked(self, script_data):
        self.scriptSelected.emit(script_data['command'])

    def on_script_execute(self, script_data):
        if script_data.get('confirm', False):
            dialog = MessageBox(
                self.tr("Confirm Execution"),
                self.tr(f"Execute script '{script_data['name']}'?"),
                self
            )
            dialog.yesButton.setText(self.tr('Execute'))
            dialog.cancelButton.setText(self.tr('Cancel'))

            if dialog.exec():
                self.scriptExecuteRequested.emit(script_data['command'])
        else:
            self.scriptExecuteRequested.emit(script_data['command'])

    def delete_script(self, script_data):
        dialog = MessageBox(
            self.tr("Confirm Delete"),
            self.tr(
                f"Delete script '{script_data['name']}'? This action cannot be undone."),
            self
        )
        dialog.yesButton.setText(self.tr('Delete'))
        dialog.cancelButton.setText(self.tr('Cancel'))

        if dialog.exec():
            self.scripts_data = [
                s for s in self.scripts_data if s['name'] != script_data['name']]
            if self.save_scripts():
                self.refresh_list()
                self.update_category_combo()
                self.show_success(self.tr("Success"),
                                  self.tr("Script deleted"))
            else:
                self.show_error(self.tr("Error"), self.tr("Delete failed"))

    def get_all_categories(self):
        categories = set()
        for script in self.scripts_data:
            category = script.get('category', '')
            if category:
                categories.add(category)
        return sorted(categories)

    def show_success(self, title, content):
        InfoBar.success(title, content, duration=2000, parent=self)

    def show_error(self, title, content):
        InfoBar.error(title, content, duration=3000, parent=self)

    def show_info(self, title, content):
        InfoBar.info(title, content, duration=2000, parent=self)

    def _import_single_script(self, script_data):
        """导入单个脚本，处理重复名称"""
        original_name = script_data.get('name', '').strip()
        if not original_name:
            return False

        # 检查是否已存在同名脚本
        existing_names = {s['name'] for s in self.scripts_data}
        new_name = original_name

        # 如果名称重复，添加后缀
        counter = 1
        while new_name in existing_names:
            new_name = f"{original_name}-{counter}"
            counter += 1

        # 创建脚本副本并更新名称
        imported_script = script_data.copy()
        imported_script['name'] = new_name

        # 更新创建时间为导入时间
        imported_script['created_time'] = datetime.now().strftime(
            "%Y-%m-%d %H:%M")

        # 如果是重命名的脚本，添加原始名称备注
        if new_name != original_name:
            imported_script['original_imported_name'] = original_name
            imported_script['description'] = self._append_import_info(
                imported_script.get('description', ''),
                original_name
            )

        # 添加到数据列表
        self.scripts_data.append(imported_script)
        return True

    def _append_import_info(self, description, original_name):
        """在描述中添加导入信息"""
        import_info = self.tr("(Imported from '{}')").format(original_name)

        if description:
            return f"{description} {import_info}"
        else:
            return import_info
