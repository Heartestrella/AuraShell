from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
import os
from PyQt5.QtCore import QUrl, Qt, QObject, pyqtSlot, QEventLoop, QTimer, QVariant
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtGui import QKeyEvent, QDesktopServices
from tools.setting_config import SCM
from tools.ai_model_manager import AIModelManager
from tools.ai_mcp_manager import AIMCPManager
from tools.ai_history_manager import AIHistoryManager
import json
import typing

if typing.TYPE_CHECKING:
    from main_window import Window
    from widgets.ssh_widget import SSHWidget

CONFIGER = SCM()

class AIBridge(QObject):
    def __init__(self, parent=None, main_window: 'Window' = None):
        super().__init__(parent)
        self.main_window = main_window
        self.model_manager = AIModelManager()
        self.mcp_manager = AIMCPManager()
        self.history_manager = AIHistoryManager()
        self._register_tool_handlers()

    def _register_tool_handlers(self):
        def Linux终端():
            def exe_shell(shell: str = '', cwd: str = '.'):
                command = "cd " + cwd + ";" + shell
                if not command:
                    return json.dumps({"status": "error", "content": "No command provided."})
                if not self.main_window:
                    return json.dumps({"status": "error", "content": "Main window not available."})
                active_widget = self.main_window.get_active_ssh_widget()
                if not active_widget:
                    return json.dumps({"status": "error", "content": "No active SSH session found."})
                worker = None
                if hasattr(active_widget, 'ssh_widget') and hasattr(active_widget.ssh_widget, 'bridge'):
                    worker = active_widget.ssh_widget.bridge.worker
                if not worker:
                    return json.dumps({"status": "error", "content": "Could not find the SSH worker for the active session."})
                output = []
                exit_code = [-1]
                loop = QEventLoop()
                def on_output_ready(result_str, code):
                    output.append(result_str)
                    exit_code[0] = code
                    if loop.isRunning():
                        loop.quit()
                timeout_timer = QTimer()
                timeout_timer.setSingleShot(True)
                timeout_timer.timeout.connect(loop.quit)
                def reset_timeout(chunk_bytes):
                    timeout_timer.start(30000)
                worker.result_ready.connect(reset_timeout)
                worker.command_output_ready.connect(on_output_ready)
                active_widget.execute_command_and_capture(command)
                timeout_timer.start(30000)
                loop.exec_()
                timeout_timer.stop()
                try:
                    worker.result_ready.disconnect(reset_timeout)
                    worker.command_output_ready.disconnect(on_output_ready)
                except TypeError:
                    pass
                if not output:
                    return json.dumps({"status": "error", "content": "Command timed out or produced no output."})
                output_str = "".join(output)
                return output_str
            def read_file(file_path: str = None):
                if not file_path:
                    return json.dumps({"status": "error", "content": "No file path provided."})
                try:
                    return exe_shell(f"cat {file_path}")
                except Exception as e:
                    return json.dumps({"status": "error", "content": f"Failed to read file: {e}"})
                pass
            self.mcp_manager.register_tool_handler(
                server_name="Linux终端",
                tool_name="exe_shell",
                handler=exe_shell,
                description="在当前终端执行shell命令",
                auto_approve=False
            )
            self.mcp_manager.register_tool_handler(
                server_name="Linux终端",
                tool_name="read_file",
                handler=read_file,
                description="读取服务器文件内容",
                auto_approve=True
            )
        Linux终端()

    @pyqtSlot(str, result=str)
    def processMessage(self, message):
        mcp_tool_call = self.mcp_manager.parse_mcp_tool_use(message)
        if mcp_tool_call:
            return json.dumps(mcp_tool_call)
        return ""

    @pyqtSlot(str, str, str, result=str)
    def executeMcpTool(self, server_name, tool_name, arguments_json):
        try:
            arguments = json.loads(arguments_json)
            result = self.mcp_manager.execute_tool(server_name, tool_name, arguments)
            return str(result)
        except json.JSONDecodeError as e:
            return json.dumps({"status": "error", "content": f"Invalid arguments format: {e}"})

    @pyqtSlot(result=str)
    def getModels(self):
        return json.dumps(self.model_manager.load_models())

    @pyqtSlot(str)
    def saveModels(self, models_json):
        try:
            models_data = json.loads(models_json)
            self.model_manager.save_models(models_data)
        except Exception as e:
            print(f"Error saving AI models: {e}")

    @pyqtSlot(str, result=str)
    def getSetting(self, key):
        config = CONFIGER.read_config()
        return config.get(key, "")

    @pyqtSlot(str, str)
    def saveSetting(self, key, value):
        CONFIGER.revise_config(key, value)

    @pyqtSlot(result=str)
    def getSystemPrompt(self):
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            prompt_path = os.path.join(current_dir, '..', 'resource', 'widget', 'ai_chat', 'system.md')
            with open(prompt_path, 'r', encoding='utf-8') as f:
                prompt = f.read()

            prompt += "\n\n# 已连接的MCP服务器\n"
            prompt += "当服务器已连接时,你可以通过`use_mcp_tool`工具使用该服务器的工具.\n"

            for server_name, tools in self.mcp_manager.tools.items():
                prompt += f"\n## {server_name}\n"
                prompt += "### 可用工具\n"
                for tool_name, tool_info in tools.items():
                    prompt += f"- {tool_name}\n"
                    prompt += f"      {tool_info['description']}\n\n"
                    prompt += "      输入模式:\n"
                    schema_str = json.dumps(tool_info['schema'], indent=2, ensure_ascii=False)
                    prompt += f"```json\n{schema_str}\n```\n"
            return prompt
        except Exception as e:
            print(f"Error generating system prompt: {e}")
            return ""

    @pyqtSlot(str, 'QVariant')
    def saveHistory(self, first_message, conversation):
        try:
            return self.history_manager.save_history(first_message, conversation)
        except Exception as e:
            print(f"Error saving chat history: {e}")

    @pyqtSlot(result=str)
    def listHistories(self):
        try:
            histories = self.history_manager.list_histories()
            return json.dumps(histories)
        except Exception as e:
            print(f"Error listing chat histories: {e}")
            return "[]"

    @pyqtSlot(str, result=str)
    def loadHistory(self, filename):
        try:
            history = self.history_manager.load_history(filename)
            return json.dumps(history)
        except Exception as e:
            print(f"Error loading chat history: {e}")
            return "[]"

    @pyqtSlot(str, result=bool)
    def deleteHistory(self, filename):
        try:
            return self.history_manager.delete_history(filename)
        except Exception as e:
            print(f"Error deleting chat history: {e}")
            return False


class AiChatWidget(QWidget):
    def __init__(self, parent=None, main_window: 'Window' = None):
        super().__init__(parent)
        self.tab_id = None
        self._side_panel = None
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

        self.channel = QWebChannel()
        self.bridge = AIBridge(self, main_window=main_window)
        self.channel.registerObject('backend', self.bridge)

        self.browser = QWebEngineView()
        self.browser.page().setWebChannel(self.channel)
        self.browser.settings().setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        self.browser.settings().setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
        self.browser.setContextMenuPolicy(Qt.NoContextMenu)
        self.layout.addWidget(self.browser)

        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        index_html_path = os.path.join(project_root, 'resource', 'widget', 'ai_chat', 'index.html')
        self.browser.setUrl(QUrl.fromLocalFile(index_html_path))

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_F5:
            self.browser.reload()
        elif event.key() == Qt.Key_F12:
            if os.environ.get('QTWEBENGINE_REMOTE_DEBUGGING'):
                QDesktopServices.openUrl(QUrl("http://localhost:" + str(os.environ['QTWEBENGINE_REMOTE_DEBUGGING'])))
        else:
            super().keyPressEvent(event)
            
    def set_tab_id(self, tab_id):
        self.tab_id = tab_id

    def _find_side_panel(self):
        if self._side_panel:
            return self._side_panel
        parent = self.parent()
        while parent is not None:
            if parent.metaObject().className() == "SidePanelWidget":
                self._side_panel = parent
                return self._side_panel
            parent = parent.parent()
        return None

    def get_tab_data(self):
        side_panel = self._find_side_panel()
        if side_panel:
            tab_data = side_panel.get_tab_data_by_uuid(self.tab_id)
            return tab_data
        return None