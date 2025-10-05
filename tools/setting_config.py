from pathlib import Path
import json
import os
import time
import uuid
# Setting Config Manager

config_dir = Path.home() / ".config" / "pyqt-ssh"


class SCM:
    def __init__(self):
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)

        self.default_config = {
            "bg_color": "Dark",  # Dark or Light
            "bg_pic": None,  # Path or None
            "font_size": 12,  # 12-30
            "locked_ratio": True,  # Bool
            "ssh_widget_text_color": "#FFFFFF",  # color code
            "background_opacity": 100,  # int 0-100
            "window_last_width": 720,  # int
            "window_last_height": 680,  # int
            "follow_cd": False,  # bool
            "language": "system",  # system, EN, CN, JP, RU
            "default_view": "icon",  # icon or details
            "max_concurrent_transfers": 10,  # int 1-10
            "compress_upload": False,  # bool compress_upload
            "splitter_lr_ratio": [0.2, 0.8],  # proportion
            "splitter_tb_ratio": [0.6, 0.4],  # proportion
            "maximized": False,  # bool Restore the last maximized state
            "aigc_api_key": "",  # str Your API key for the AI model
            "aigc_open": False,  # bool Whether to enable the AI model feature
            "aigc_model": "DeepSeek",  # str The AI model to use
            "aigc_history_max_length": 10,  # int The max length of history messages
            "splitter_left_components": [0.18, 0.47, 0.35],
            "open_mode": False,  # bool  true:external editor, false: internal viewer
            "external_editor": "",
            # bool Auto-save editor files when focus is lost
            "editor_auto_save_on_focus_lost": False,
            "splitter_sizes": [500, 500],
            "splitter_lr_left_width": 300,
            "bg_theme_color": None
        }
        self.config_path = config_dir / "setting-config.json"
        if not os.path.exists(self.config_path):
            self.init_config()
            print("Config file created at:", self.config_path)
        else:
            self._check_and_repair_config(self.read_config())

    def write_config(self, config_data):
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Failed to write config file: {e}")

    def _check_and_repair_config(self, config: dict) -> dict:

        repaired = False
        for key in self.default_config:
            if key not in config:
                config[key] = self.default_config[key]
                repaired = True
        if repaired:
            self.write_config(config)
        return config

    def init_config(self):
        self.write_config(self.default_config)

    def revise_config(self, key, value):
        config = self.read_config()
        config[key] = value
        # print(config)
        self.write_config(config)

    def read_config(self) -> dict:
        with open(self.config_path, mode="r", encoding="utf-8") as f:
            config_dict = json.load(f)
        return config_dict


class ChatSession:
    def __init__(self, session_data=None):
        self.id = session_data.get("id") if session_data else str(uuid.uuid4())
        now = int(time.time())
        self.created_at = session_data.get(
            "created_at", now) if session_data else now
        self.updated_at = session_data.get(
            "updated_at", now) if session_data else now
        self.messages = session_data.get(
            "messages", []) if session_data else []
        self.model = session_data.get("model", "") if session_data else ""
        self.title = session_data.get("title", "") if session_data else ""

    def to_dict(self):
        return {
            "id": self.id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "messages": self.messages,
            "model": self.model,
            "title": self.title,
        }

    def add_message(self, sender, text):
        self.messages.append({
            "sender": sender,
            "text": text,
            "time": int(time.time())
        })
        self.updated_at = int(time.time())


class ChatSessionManager:
    def __init__(self, config_dir=None):
        self.config_dir = Path(
            config_dir) if config_dir else Path.home() / ".config" / "pyqt-ssh"
        self.sessions_file = self.config_dir / "sessions.json"
        os.makedirs(self.config_dir, exist_ok=True)
        self.sessions = self.load_sessions()

    def load_sessions(self):
        if self.sessions_file.exists():
            with open(self.sessions_file, "r", encoding="utf-8") as f:
                raw = json.load(f)
                return {s["id"]: ChatSession(s) for s in raw}
        return {}

    def save_sessions(self):
        with open(self.sessions_file, "w", encoding="utf-8") as f:
            json.dump([s.to_dict() for s in self.sessions.values()],
                      f, ensure_ascii=False, indent=2)

    def new_session(self, title="", model=""):
        session = ChatSession({"title": title, "model": model})
        self.sessions[session.id] = session
        self.save_sessions()
        return session

    def get_session(self, session_id):
        return self.sessions.get(session_id)

    def add_message(self, session_id, sender, text):
        sess = self.get_session(session_id)
        if sess:
            sess.add_message(sender, text)
            self.save_sessions()
