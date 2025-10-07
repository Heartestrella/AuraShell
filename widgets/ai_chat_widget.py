from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
import os
from PyQt5.QtCore import QUrl, Qt, QObject, pyqtSlot, QEventLoop, QTimer, QVariant, pyqtSignal
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtGui import QKeyEvent, QDesktopServices
from tools.setting_config import SCM
from tools.ai_model_manager import AIModelManager
from tools.ai_mcp_manager import AIMCPManager
from tools.ai_history_manager import AIHistoryManager
import json
import base64
import re
import typing
import time
import requests
import threading

if typing.TYPE_CHECKING:
    from main_window import Window
    from widgets.ssh_widget import SSHWidget

CONFIGER = SCM()

class AIBridge(QObject):
    toolResultReady = pyqtSignal(str, str)
    streamChunkReceived = pyqtSignal(str, str)
    streamFinished = pyqtSignal(str, int, str, str)
    streamFailed = pyqtSignal(str, str)
    
    def __init__(self, parent=None, main_window: 'Window' = None):
        super().__init__(parent)
        self.main_window = main_window
        self.model_manager = AIModelManager()
        self.mcp_manager = AIMCPManager()
        self.history_manager = AIHistoryManager()
        self.pending_tool_calls = {}
        self.active_requests = {}
        self._register_tool_handlers()

    def _register_tool_handlers(self):

        def Linux终端():
            def exe_shell(shell: str = '', cwd: str = '.'):
                command = "cd " + cwd + ";" + shell
                if not command:
                    return json.dumps({"status": "error", "content": "No command provided."}, ensure_ascii=False)
                if not self.main_window:
                    return json.dumps({"status": "error", "content": "Main window not available."}, ensure_ascii=False)
                active_widget = self.main_window.get_active_ssh_widget()
                if not active_widget:
                    return json.dumps({"status": "error", "content": "No active SSH session found."}, ensure_ascii=False)
                worker = None
                if hasattr(active_widget, 'ssh_widget') and hasattr(active_widget.ssh_widget, 'bridge'):
                    worker = active_widget.ssh_widget.bridge.worker
                if not worker:
                    return json.dumps({"status": "error", "content": "Could not find the SSH worker for the active session."}, ensure_ascii=False)
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
                output_str = "".join(output)
                return output_str
            def read_file(file_path: str = None, show_line: bool = False):
                if not file_path:
                    return json.dumps({"status": "error", "content": "No file path provided."}, ensure_ascii=False)
                try:
                    command = f"cat {file_path}"
                    if show_line:
                        command = f"awk '{{print NR\"|\" $0}}' {file_path}"
                    return exe_shell(command)
                except Exception as e:
                    return json.dumps({"status": "error", "content": f"Failed to read file: {e}"}, ensure_ascii=False)
                pass
            def write_file(args:str = None):
                """
                <write_to_file><path>{文件绝对路径}</path><content>{文件内容}</content></write_to_file>
                """
                if not args:
                    return json.dumps({"status": "error", "content": "No arguments provided."}, ensure_ascii=False)
                try:
                    path_match = re.search(r'<path>(.*?)</path>', args, re.DOTALL)
                    if not path_match:
                        return json.dumps({"status": "error", "content": "Missing or invalid <path> tag."}, ensure_ascii=False)
                    file_path = path_match.group(1).strip()
                    if not file_path:
                        return json.dumps({"status": "error", "content": "File path cannot be empty."}, ensure_ascii=False)
                    content_start_tag = '<content>'
                    content_end_tag = '</content>'
                    start_index = args.find(content_start_tag)
                    end_index = args.rfind(content_end_tag)
                    if start_index == -1 or end_index == -1 or start_index >= end_index:
                        return json.dumps({"status": "error", "content": "Missing or invalid <content> tag."}, ensure_ascii=False)
                    content = args[start_index + len(content_start_tag):end_index]
                    if content.startswith('\n'):
                        content = content[1:]
                    if content.endswith('\n'):
                        content = content[:-1]
                    encoded_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')
                    command = f"echo '{encoded_content}' | base64 --decode > {file_path}"
                    r = exe_shell(command)
                    if r == '':
                        active_widget = self.main_window.get_active_ssh_widget()
                        if active_widget:
                            widget_key = active_widget.objectName()
                            self.main_window._refresh_paths(widget_key)
                        return json.dumps({"status": "success", "content": f"File '{file_path}' was written successfully."}, ensure_ascii=False)
                    else:
                        try:
                            error_data = json.loads(r)
                            return json.dumps(error_data, ensure_ascii=False)
                        except json.JSONDecodeError:
                            return json.dumps({"status": "error", "content": r}, ensure_ascii=False)
                except Exception as e:
                    return json.dumps({"status": "error", "content": f"An unexpected error occurred during file creation: {e}"}, ensure_ascii=False)
            def edit_file(args:str = None):
                """
                <edit_file><path>{文件绝对路径}</path><start_line>{开始行号}</start_line><end_line>{结束行号}</end_line><search>{要查找的原始内容}</search><replace>{替换成的新内容}</replace></edit_file>
                """
                if not args:
                    return json.dumps({"status": "error", "content": "No arguments provided for edit_file."}, ensure_ascii=False)
                try:
                    path_match = re.search(r'<path>(.*?)</path>', args, re.DOTALL)
                    start_line_match = re.search(r'<start_line>(\d+)</start_line>', args)
                    end_line_match = re.search(r'<end_line>(\d+)</end_line>', args)
                    if not (path_match and start_line_match and end_line_match):
                        return json.dumps({"status": "error", "content": "Missing or invalid path/start_line/end_line tags."}, ensure_ascii=False)
                    file_path = path_match.group(1).strip()
                    start_line = int(start_line_match.group(1))
                    end_line = int(end_line_match.group(1))
                    search_content = re.search(r'<search>(.*?)</search>', args, re.DOTALL)
                    if search_content is None:
                         return json.dumps({"status": "error", "content": "Missing <search> tag."}, ensure_ascii=False)
                    search_block = search_content.group(1)
                    replace_content = re.search(r'<replace>(.*?)</replace>', args, re.DOTALL)
                    if replace_content is None:
                        return json.dumps({"status": "error", "content": "Missing <replace> tag."}, ensure_ascii=False)
                    replace_block = replace_content.group(1)
                    remote_content_json = read_file(file_path)
                    try:
                        remote_data = json.loads(remote_content_json)
                        if remote_data.get("status") == "error":
                            return remote_content_json
                        remote_content = remote_data.get("content", "")
                    except (json.JSONDecodeError, AttributeError):
                        remote_content = remote_content_json
                    remote_content = remote_content.replace('\r', '')
                    lines = remote_content.splitlines(True)
                    if not (1 <= start_line <= end_line <= len(lines)):
                        return json.dumps({"status": "error", "content": f"Line numbers out of bounds. File has {len(lines)} lines."}, ensure_ascii=False)
                    actual_block = "".join(lines[start_line - 1:end_line])
                    search_block_stripped = search_block.strip()
                    actual_block_stripped = actual_block.strip()
                    if actual_block_stripped != search_block_stripped:
                        return json.dumps({
                            "status": "error",
                            "content": "Content verification failed. The content on the server does not match the 'search' block.",
                            "expected": search_block_stripped,
                            "actual": actual_block_stripped
                        }, ensure_ascii=False)
                    original_last_line = lines[end_line - 1]
                    line_ending = '\n'
                    if original_last_line.endswith('\r\n'):
                        line_ending = '\r\n'
                    replace_block_stripped = replace_block.strip()
                    new_content_parts = []
                    if replace_block_stripped:
                        replace_lines = replace_block_stripped.splitlines()
                        new_content_parts = [line + line_ending for line in replace_lines]
                    new_lines = lines[:start_line - 1] + new_content_parts + lines[end_line:]
                    new_full_content = "".join(new_lines)
                    encoded_content = base64.b64encode(new_full_content.encode('utf-8')).decode('utf-8')
                    command = f"echo '{encoded_content}' | base64 --decode > {file_path}"
                    r = exe_shell(command)
                    if r == '':
                        active_widget = self.main_window.get_active_ssh_widget()
                        if active_widget:
                            widget_key = active_widget.objectName()
                            self.main_window._refresh_paths(widget_key)
                        return json.dumps({"status": "success", "content": f"{file_path} {start_line}-{end_line} {search_block} -> {replace_block}"}, ensure_ascii=False)
                    else:
                        return json.dumps({"status": "error", "content": r}, ensure_ascii=False)
                except Exception as e:
                    return json.dumps({"status": "error", "content": f"An unexpected error occurred during file edit: {e}"}, ensure_ascii=False)

            def get_terminal_output(count: int = 1):
                if not self.main_window:
                    return json.dumps({"status": "error", "content": "Main window not available."}, ensure_ascii=False)
                active_widget = self.main_window.get_active_ssh_widget()
                if not active_widget:
                    return json.dumps({"status": "error", "content": "No active SSH session found."}, ensure_ascii=False)
                if hasattr(active_widget, 'ssh_widget') and hasattr(active_widget.ssh_widget, 'get_latest_output'):
                    return active_widget.ssh_widget.get_latest_output(count)
                else:
                    return json.dumps({"status": "error", "content": "Could not find the terminal output function."}, ensure_ascii=False)

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
            self.mcp_manager.register_tool_handler(
                server_name="Linux终端",
                tool_name="write_file",
                handler=write_file,
                description="覆盖服务器文件",
                auto_approve=False
            )
            self.mcp_manager.register_tool_handler(
                server_name="Linux终端",
                tool_name="edit_file",
                handler=edit_file,
                description="编辑文件",
                auto_approve=False
            )
            self.mcp_manager.register_tool_handler(
                server_name="Linux终端",
                tool_name="get_terminal_output",
                handler=get_terminal_output,
                description="获取最新几条的所执行命令的终端输出",
                auto_approve=True
            )
        Linux终端()
        # print(self.getSystemPrompt())

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
                    schema_str = tool_info['schema']
                    prompt += f"{schema_str}\n\n"
            return prompt
        except Exception as e:
            print(f"Error generating system prompt: {e}")
            return ""

    @pyqtSlot(str, result=str)
    def processMessage(self, message):
        mcp_tool_call = self.mcp_manager.parse_mcp_tool_use(message)
        if mcp_tool_call:
            return json.dumps(mcp_tool_call, ensure_ascii=False)
        return ""

    def _execute_tool_async(self, server_name, tool_name, arguments, request_id):
        try:
            result = self.mcp_manager.execute_tool(server_name, tool_name, arguments)
            result_str = str(result)
        except json.JSONDecodeError as e:
            result_str = json.dumps({"status": "error", "content": f"Invalid arguments format: {e}"}, ensure_ascii=False)
        except Exception as e:
            result_str = json.dumps({"status": "error", "content": f"Tool execution error: {e}"}, ensure_ascii=False)
        self.toolResultReady.emit(request_id, result_str)
        if request_id in self.pending_tool_calls:
            del self.pending_tool_calls[request_id]
    
    @pyqtSlot(str, str, str, result=str)
    @pyqtSlot(str, str, str, str, result=str)
    def executeMcpTool(self, server_name, tool_name, arguments:str, request_id=None):
        if request_id:
            self.pending_tool_calls[request_id] = {
                'server_name': server_name,
                'tool_name': tool_name,
                'start_time': time.time()
            }
            QTimer.singleShot(0, lambda: self._execute_tool_async(
                server_name, tool_name, arguments, request_id
            ))
            return ""
        else:
            try:
                result = self.mcp_manager.execute_tool(server_name, tool_name, arguments)
                return str(result)
            except json.JSONDecodeError as e:
                return json.dumps({"status": "error", "content": f"Invalid arguments format: {e}"}, ensure_ascii=False)

    @pyqtSlot(result=str)
    def getModels(self):
        return json.dumps(self.model_manager.load_models(), ensure_ascii=False)

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
            return json.dumps(histories, ensure_ascii=False)
        except Exception as e:
            print(f"Error listing chat histories: {e}")
            return "[]"

    @pyqtSlot(str, result=str)
    def loadHistory(self, filename):
        try:
            history = self.history_manager.load_history(filename)
            return json.dumps(history, ensure_ascii=False)
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

    @pyqtSlot(result=str)
    def get_current_cwd(self):
        if not self.main_window:
            return json.dumps({"status": "error", "content": "Main window not available."}, ensure_ascii=False)
        active_widget = self.main_window.get_active_ssh_widget()
        if not active_widget:
            return json.dumps({"status": "error", "content": "No active SSH session found."}, ensure_ascii=False)
        if hasattr(active_widget, 'ssh_widget') and hasattr(active_widget.ssh_widget, 'bridge'):
            cwd = active_widget.ssh_widget.bridge.current_directory
            return json.dumps({"status": "success", "cwd": cwd}, ensure_ascii=False)
        else:
            return json.dumps({"status": "error", "content": "Could not find the terminal bridge."}, ensure_ascii=False)

    @pyqtSlot(result=str)
    def get_file_manager_cwd(self):
        if not self.main_window:
            return json.dumps({"status": "error", "content": "Main window not available."}, ensure_ascii=False)
        active_widget = self.main_window.get_active_ssh_widget()
        if not active_widget:
            return json.dumps({"status": "error", "content": "No active SSH session found."}, ensure_ascii=False)
        if hasattr(active_widget, 'file_explorer'):
            cwd = active_widget.file_explorer.path
            return json.dumps({"status": "success", "cwd": cwd}, ensure_ascii=False)
        else:
            return json.dumps({"status": "error", "content": "Could not find the file explorer."}, ensure_ascii=False)


    @pyqtSlot(str)
    def cancelProxiedFetch(self, request_id):
        if request_id in self.active_requests:
            self.active_requests[request_id]['cancelled'] = True

    @pyqtSlot(str, str, str)
    def proxiedFetch(self, request_id, url, options_json):
        self.active_requests[request_id] = {'cancelled': False}

        def run():
            try:
                options = json.loads(options_json)
                proxy_config_str = self.getSetting("ai_chat_proxy")
                proxies = {}
                if proxy_config_str:
                    proxy_config = json.loads(proxy_config_str)
                    protocol = proxy_config.get("protocol")
                    host = proxy_config.get("host")
                    port = proxy_config.get("port")
                    username = proxy_config.get("username")
                    password = proxy_config.get("password")
                    if protocol and host and port:
                        auth = ""
                        if username and password:
                            auth = f"{username}:{password}@"
                        proxy_url = f"{protocol}://{auth}{host}:{port}"
                        if protocol.startswith('socks'):
                            proxy_scheme = 'socks5h' if protocol == 'socks5' else protocol
                            proxy_url = f"{proxy_scheme}://{auth}{host}:{port}"
                            proxies = {"http": proxy_url, "https": proxy_url}
                        else:
                            proxies = {"http": proxy_url, "https": proxy_url}
                headers = options.get('headers', {})
                body = options.get('body', None)
                method = options.get('method', 'GET')
                with requests.request(method, url, headers=headers, data=body, stream=True, proxies=proxies, timeout=300) as r:
                    for chunk in r.iter_content(chunk_size=8192):
                        if self.active_requests.get(request_id, {}).get('cancelled'):
                            break
                        if chunk:
                            self.streamChunkReceived.emit(request_id, chunk.decode('utf-8', errors='ignore'))
                    if not self.active_requests.get(request_id, {}).get('cancelled'):
                        response_headers = dict(r.headers)
                        self.streamFinished.emit(request_id, r.status_code, r.reason, json.dumps(response_headers))
            except Exception as e:
                if not self.active_requests.get(request_id, {}).get('cancelled'):
                    self.streamFailed.emit(request_id, str(e))
            finally:
                if request_id in self.active_requests:
                    del self.active_requests[request_id]
        thread = threading.Thread(target=run)
        thread.start()

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