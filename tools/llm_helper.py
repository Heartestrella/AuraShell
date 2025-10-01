
from openai import OpenAI
from tools.setting_config import SCM
from PyQt5.QtCore import QThread, pyqtSignal
import json

configer = SCM()
config = configer.read_config()

API_KEY = config.get("aigc_api_key", "")
MODEL = config.get("aigc_model", "DeepSeek")
MODEL_URL = {
    "DeepSeek": "https://api.deepseek.com",
    "ChatGPT": "https://api.openai.com",
    "Local ollama": "http://127.0.0.1"
}
MODEL_NAME = {
    "DeepSeek": "deepseek-chat"
}


class LLMHelper(QThread):
    error_signal = pyqtSignal(str)
    result_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.client = None
        self.is_running = False
        self.current_messages = []

        self.system_prompt = self.tr('''
You are a professional SSH assistant. Generate corresponding SSH commands based on terminal output and user requirements.

Please return in strict JSON format:
{
    "command": ["generated SSH command, can be multi-line script", "is multi-line command: true/false"],
    "explanation": "explanation of the generated SSH command (explanation language should match user input language)"
}

If unable to generate command, return:
{
    "command": ["", false],
    "explanation": "reason why command cannot be generated"
}

Input format:
{
    "terminal": "terminal output content",
    "user_input": "user natural language requirement"
}

Please note that there may be multi-turn Q&A information. Pay attention to whether the context is related. Only answer the content of the latest text. The previous text may contain helpful auxiliary information. The assistant field corresponds to your previous answer.
''')

        self.history_messages_max_length = config.get(
            "aigc_history_max_length", 10)
        self.recent_commands = []

        if self.init_client():
            print("LLM client initialized successfully")
        else:
            print("LLM client initialization failed")

    def run(self):
        if not self.client or not self.current_messages:
            self.error_signal.emit(
                self.tr("Client not initialized or no message content"))
            return

        try:
            buffer = ""
            buffer_size = 0
            max_buffer_size = 50

            messages = self._build_messages()
            print(messages)
            # print("Model Name:", MODEL_NAME.get(MODEL))
            response = self.client.chat.completions.create(
                model=MODEL_NAME.get(MODEL),
                messages=messages,
                stream=True
            )

            full_content = ""
            for chunk in response:
                if not self.is_running:
                    break

                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    full_content += content
                    buffer += content
                    buffer_size += len(content)

                    if (buffer_size >= max_buffer_size or
                            content in ['\n', '。', '!', '?', '；', '.']):
                        self.result_signal.emit(buffer)
                        buffer = ""
                        buffer_size = 0

            if buffer and self.is_running:
                self.result_signal.emit(buffer)

            if self.is_running and full_content:
                self._add_to_history("assistant", full_content)
                self.finished_signal.emit()

        except Exception as e:
            self.error_signal.emit(self.tr(f"API request failed: {str(e)}"))
        finally:
            self.is_running = False

    def send_request(self, terminal_output, user_input, use_compact_history=True):
        """
        发送请求：
          - use_compact_history=True 时，调用 _compact_history_for_send 来节省 tokens
          - 注意：recent_commands 保持原样（用于本地保存或后续展示）
        """
        if self.is_running:
            self.error_signal.emit(
                self.tr("Previous request is still processing"))
            return False

        # 记录历史（保留原始内容以便之后复用）
        user_message = json.dumps(
            {"terminal": terminal_output, "user_input": user_input}, ensure_ascii=False)
        self._add_to_history("user", user_message)

        # 生成 current_messages（但不要把 oversized terminal 带到历史里）
        if use_compact_history:
            self.current_messages = self._compact_history_for_send(
                terminal_output, user_input)
        else:
            # 不压缩，直接 system + recent_commands + current user
            msgs = [{"role": "system", "content": self.system_prompt}]
            for msg in self.recent_commands:
                if msg.get("role") != "system":
                    msgs.append(msg)
            msgs.append({"role": "user", "content": user_message})
            self.current_messages = msgs

        self.is_running = True
        self.start()
        return True

    def _build_messages(self):
        messages = [{"role": "system", "content": self.system_prompt}]

        for msg in self.recent_commands:
            if msg["role"] != "system":
                messages.append(msg)

        return messages

    def _add_to_history(self, role, content):
        self.recent_commands.append({"role": role, "content": content})

        if len(self.recent_commands) > self.history_messages_max_length:
            self.recent_commands = [self.recent_commands[0]] + \
                self.recent_commands[-(self.history_messages_max_length-1):]

    def init_client(self, model=MODEL, api_key=API_KEY):
        try:
            if not api_key:
                self.error_signal.emit(self.tr("API key is empty"))
                return False

            self.client = OpenAI(
                api_key=api_key,
                base_url=MODEL_URL.get(model, None)
            )
            print("Model : ", MODEL_URL.get(model, None))
            return True

        except Exception as e:
            self.error_signal.emit(
                self.tr(f"Client initialization failed: {str(e)}"))
            return False

    def stop(self):
        self.is_running = False
        self.wait()

    def _safe_load_json(self, s):
        """尝试把字符串解析为 JSON，失败则返回 None"""
        try:
            return json.loads(s)
        except Exception:
            return None

    def _compact_history_for_send(self, latest_terminal: str, latest_user_input: str):
        """
        构建 compact 的 messages 列表以发送给模型，策略：
         - 保留 system prompt（始终）
         - 对于历史 user 条目：保留 user_input 文本，但把 terminal 字段清空或置为简短占位
         - 对于历史 assistant 条目：如果能解析为 JSON，则只保留 explanation 字段（或少量元信息）
           否则保留原文本（但可考虑截断）
         - 最后追加当前 user（带上 latest_terminal 与 latest_user_input）
        这样可以显著减少 tokens 用量而保留上下文要点。
        """
        messages = [{"role": "system", "content": self.system_prompt}]

        # 遍历 recent_commands（它是按时间顺序追加的：user/assistant/...）
        for msg in self.recent_commands:
            role = msg.get("role")
            content = msg.get("content", "")

            if role == "user":
                parsed = self._safe_load_json(content)
                if isinstance(parsed, dict):
                    # 保留 user_input，删除/缩短 terminal
                    ui = parsed.get("user_input", "")
                    # 用空字符串或占位符替代历史 terminal（节省 tokens）
                    compact_user = {"terminal": "", "user_input": ui}
                    messages.append({"role": "user", "content": json.dumps(
                        compact_user, ensure_ascii=False)})
                else:
                    # content 不是 json（回退），只保留原文的前 N 字（防止过大）
                    short = content if len(content) <= 200 else content[-200:]
                    messages.append({"role": "user", "content": short})

            elif role == "assistant":
                parsed = self._safe_load_json(content)
                if isinstance(parsed, dict):
                    # 只保留 explanation 字段（通常较短且有意义）
                    expl = parsed.get("explanation", "")
                    if expl:
                        compact_assistant = {"command": [
                            "", False], "explanation": expl}
                        messages.append({"role": "assistant", "content": json.dumps(
                            compact_assistant, ensure_ascii=False)})
                    else:
                        # 若没有 explanation，则保留少量文本
                        messages.append({"role": "assistant", "content": ""})
                else:
                    # 非 JSON：截断保留最后一段（若太长）
                    short = content if len(content) <= 200 else content[-200:]
                    messages.append({"role": "assistant", "content": short})

            else:
                # 其他 role（如 system），直接附上（但 system 一般只有第一个）
                messages.append({"role": role, "content": content})

        # 最后追加当前 user（带上最新的 terminal 内容）
        current_user_obj = {"terminal": latest_terminal or "",
                            "user_input": latest_user_input or ""}
        messages.append({"role": "user", "content": json.dumps(
            current_user_obj, ensure_ascii=False)})

        return messages
