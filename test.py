import sys
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget
from qfluentwidgets import setTheme, Theme
from widgets.file_load_window import FileWindow  # 替换为你的 FileWindow 文件路径


class DemoApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FileWindow Demo")
        self.resize(300, 200)

        layout = QVBoxLayout(self)
        self.show_window_btn = QPushButton("Show FileWindow", self)
        layout.addWidget(self.show_window_btn)

        self.add_card_btn = QPushButton("Add Card", self)
        layout.addWidget(self.add_card_btn)

        # 初始化 FileWindow，不设置 parent=None 是可以的，也可以不传
        self.files_window = FileWindow(parent=None)

        # 点击按钮显示 frameless 窗口
        self.show_window_btn.clicked.connect(self.show_file_window)

        # 点击按钮添加测试卡片
        self.add_card_btn.clicked.connect(self.add_card)

        self.counter = 1

    def show_file_window(self):
        self.files_window.show()
        self.files_window.raise_()
        self.files_window.activateWindow()

    def add_card(self):
        title = f"任务 {self.counter}"
        content = f"文件{self.counter}.zip"
        file_id = f"demo_{self.counter}"
        self.files_window.add_card(
            title, content, file_id, action_type="upload")
        self.counter += 1


if __name__ == "__main__":
    app = QApplication(sys.argv)
    setTheme(Theme.LIGHT)  # 设置主题
    demo = DemoApp()
    demo.show()
    sys.exit(app.exec_())
