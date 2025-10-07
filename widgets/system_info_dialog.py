from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTextBrowser, QApplication, QFrame, QLabel
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QFont
from qfluentwidgets import PrimaryPushButton, TransparentPushButton, TransparentToolButton, FluentIcon as FIF, isDarkTheme

class SystemInfoDialog(QDialog):
    def __init__(self, title: str, system_info: str, parent=None):
        super().__init__(parent)
        self.system_info = system_info
        self.m_drag = False
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(700, 500)
        self.resize(800, 600)
        self._init_ui(title)
        self._apply_styles()
        self._format_and_display_info()

    def _init_ui(self, title: str):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.container = QFrame(self)
        self.container.setObjectName("container")
        main_layout.addWidget(self.container)
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(1, 1, 1, 1)
        container_layout.setSpacing(0)
        self.title_bar = QFrame(self)
        self.title_bar.setObjectName("titleBar")
        self.title_bar.setFixedHeight(44)
        title_bar_layout = QHBoxLayout(self.title_bar)
        title_bar_layout.setContentsMargins(15, 0, 5, 0)
        self.title_label = QLabel(title, self)
        self.title_label.setObjectName("titleLabel")
        self.close_btn_title = TransparentToolButton(FIF.CLOSE, self)
        self.close_btn_title.setObjectName("closeBtnTitle")
        self.close_btn_title.clicked.connect(self.accept)
        title_bar_layout.addWidget(self.title_label)
        title_bar_layout.addStretch()
        title_bar_layout.addWidget(self.close_btn_title)
        content_frame = QFrame(self)
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(20, 10, 20, 20)
        content_layout.setSpacing(15)
        self.text_browser = QTextBrowser(self)
        self.text_browser.setObjectName("systemInfoBrowser")
        self.text_browser.setOpenExternalLinks(False)
        self.text_browser.setReadOnly(True)
        self.text_browser.setContextMenuPolicy(Qt.NoContextMenu)
        font = QFont("Consolas", 10)
        if not font.exactMatch():
            font = QFont("Courier New", 10)
        self.text_browser.setFont(font)
        content_layout.addWidget(self.text_browser, 1)
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        self.copy_all_btn = PrimaryPushButton(FIF.COPY, self.tr("Copy All"))
        self.copy_all_btn.setFixedHeight(36)
        self.copy_all_btn.clicked.connect(self._copy_all)
        self.close_btn = TransparentPushButton(FIF.CLOSE, self.tr("Close"))
        self.close_btn.setFixedHeight(36)
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.copy_all_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.close_btn)
        content_layout.addLayout(button_layout)
        container_layout.addWidget(self.title_bar)
        container_layout.addWidget(content_frame, 1)

    def _apply_styles(self):
        is_dark = isDarkTheme()
        if is_dark:
            bg_color, text_color, border_color, header_color, key_color, value_color, title_bar_bg = "#1e1e1e", "#d4d4d4", "#3c3c3c", "#569cd6", "#9cdcfe", "#ce9178", "#2d2d2d"
        else:
            bg_color, text_color, border_color, header_color, key_color, value_color, title_bar_bg = "#f8f8f8", "#333333", "#e0e0e0", "#0078d4", "#0451a5", "#a31515", "#f0f0f0"
        self.setStyleSheet(f"""
            QFrame#container {{ background-color: {bg_color}; border-radius: 8px; }}
            QFrame#titleBar {{ background-color: {title_bar_bg}; border-top-left-radius: 8px; border-top-right-radius: 8px; border-bottom: 1px solid {border_color}; }}
            QLabel#titleLabel {{ color: {text_color}; font-size: 14px; font-weight: bold; }}
            QTextBrowser#systemInfoBrowser {{ background-color: transparent; color: {text_color}; border: none; selection-background-color: #264f78; selection-color: white; }}
            QScrollBar:vertical {{ background: transparent; width: 12px; margin: 0; }}
            QScrollBar::handle:vertical {{ background: {'#555555' if is_dark else '#c0c0c0'}; border-radius: 6px; min-height: 30px; }}
            QScrollBar::handle:vertical:hover {{ background: {'#666666' if is_dark else '#a0a0a0'}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
        """)
        self.colors = {'header': header_color, 'key': key_color, 'value': value_color, 'text': text_color}

    def _format_and_display_info(self):
        if not self.system_info:
            self.text_browser.setHtml(f"""<div style='color: {self.colors['text']}; text-align: center; padding: 50px;'><h3>📊 {self.tr("No System Information Available")}</h3><p>{self.tr("System information has not been retrieved yet.")}</p></div>""")
            return
        self.text_browser.setHtml(self._parse_info_to_html(self.system_info))

    def _parse_info_to_html(self, info: str) -> str:
        lines = info.strip().split('\n')
        html_parts = [f"""<html><head><style>
                body {{ font-family: 'Consolas', 'Courier New', monospace; line-height: 1.6; color: {self.colors['text']}; }}
                .section-header {{ color: {self.colors['header']}; font-size: 14px; font-weight: bold; margin-top: 15px; margin-bottom: 8px; padding-bottom: 5px; border-bottom: 2px solid {self.colors['header']}; }}
                .info-line {{ margin: 4px 0; padding-left: 10px; }}
                .key {{ color: {self.colors['key']}; font-weight: 600; }}
                .value {{ color: {self.colors['value']}; }}
                .icon {{ margin-right: 8px; }}
            </style></head><body>"""]
        for line in lines:
            line = line.strip()
            if not line:
                html_parts.append("<br>")
                continue
            if self._is_section_header(line):
                html_parts.append(f"<div class='section-header'><span class='icon'>{self._get_section_icon(line)}</span>{line}</div>")
            elif ':' in line or '=' in line:
                parts = line.split(':', 1) if ':' in line else line.split('=', 1)
                if len(parts) == 2:
                    html_parts.append(f"<div class='info-line'><span class='key'>{parts[0].strip()}:</span><span class='value'> {parts[1].strip()}</span></div>")
                else:
                    html_parts.append(f"<div class='info-line'>{line}</div>")
            else:
                html_parts.append(f"<div class='info-line'>{line}</div>")
        html_parts.append("</body></html>")
        return ''.join(html_parts)

    def _is_section_header(self, line: str) -> bool:
        if not line: return False
        if any(char * 3 in line for char in ['=', '-', '#', '*']): return True
        if line.isupper() and len(line) < 50: return True
        if any(keyword in line.upper() for keyword in ['SYSTEM', 'CPU', 'MEMORY', 'DISK', 'NETWORK', 'INFO']): return True
        return False

    def _get_section_icon(self, header: str) -> str:
        header_upper = header.upper()
        if 'CPU' in header_upper or 'PROCESSOR' in header_upper: return '🖥️'
        if 'MEMORY' in header_upper or 'RAM' in header_upper: return '💾'
        if 'DISK' in header_upper or 'STORAGE' in header_upper: return '💿'
        if 'NETWORK' in header_upper or 'NET' in header_upper: return '🌐'
        if 'SYSTEM' in header_upper or 'OS' in header_upper: return '⚙️'
        if 'USER' in header_upper: return '👤'
        if 'TIME' in header_upper or 'DATE' in header_upper: return '🕒'
        return '📊'

    def _copy_all(self):
        QApplication.clipboard().setText(self.system_info)
        self.copy_all_btn.setText(self.tr("✓ Copied!"))
        self.copy_all_btn.setEnabled(False)
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(1500, self._reset_copy_button)

    def _reset_copy_button(self):
        self.copy_all_btn.setText(self.tr("Copy All"))
        self.copy_all_btn.setEnabled(True)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.title_bar.underMouse():
            self.m_drag = True
            self.m_DragPosition = event.globalPos() - self.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.m_drag:
            self.move(event.globalPos() - self.m_DragPosition)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.m_drag = False

    def tr(self, text: str) -> str:
        translations = {
            "Copy All": "复制全部", "Close": "关闭",
            "✓ Copied!": "✓ 已复制！",
            "No System Information Available": "暂无系统信息",
            "System information has not been retrieved yet.": "系统信息尚未获取。",
        }
        return translations.get(text, text)