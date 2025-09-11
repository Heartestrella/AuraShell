# session.py
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List


class Session:
    def __init__(self, session_data: Dict[str, Any] = None):
        self.id = session_data.get(
            'id', f"session_{datetime.now().timestamp()}") if session_data else f"session_{datetime.now().timestamp()}"
        self.name = session_data.get('name', '新会话') if session_data else '新会话'
        self.host = session_data.get(
            'host', 'localhost') if session_data else 'localhost'
        self.username = session_data.get(
            'username', 'user') if session_data else 'user'
        self.port = session_data.get('port', 22) if session_data else 22
        self.auth_type = session_data.get(
            'auth_type', 'password') if session_data else 'password'
        self.password = session_data.get(
            'password', '') if session_data else ''
        self.key_path = session_data.get(
            'key_path', '') if session_data else ''
        self.status = session_data.get(
            'status', 'disconnected') if session_data else 'disconnected'
        self.created_at = session_data.get('created_at', datetime.now(
        ).isoformat()) if session_data else datetime.now().isoformat()
        self.history = session_data.get('history', []) if session_data else []
        self.console_content = session_data.get(
            'console_content', '') if session_data else ''

    def to_dict(self) -> Dict[str, Any]:
        """将会话转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'host': self.host,
            'username': self.username,
            'port': self.port,
            'auth_type': self.auth_type,
            'password': self.password,
            'key_path': self.key_path,
            'status': self.status,
            'created_at': self.created_at,
            'history': self.history,
            'console_content': self.console_content
        }

    def add_command(self, command: str):
        """添加命令到历史记录"""
        if command.strip() and command not in self.history:
            self.history.append(command)
            if len(self.history) > 30:
                self.history.pop(0)

    def update_console(self, content: str):
        """更新控制台内容"""
        self.console_content = content


class SessionManager:
    def __init__(self):
        self.config_dir = Path.home() / ".config" / "pyqt-ssh"
        self.sessions_file = self.config_dir / "sessions.json"
        self._ensure_config_dir()
        self._init_sessions_file()
        self.sessions_cache = self.load_sessions()  # 添加内存缓存

    def load_sessions(self) -> List[Session]:
        """加载所有会话"""
        try:
            with open(self.sessions_file, 'r', encoding='utf-8') as f:
                sessions_data = json.load(f)
                return [Session(session_data) for session_data in sessions_data]
        except:
            return [Session()]

    def save_sessions(self, sessions: List[Session]):
        """保存会话列表"""
        sessions_data = [session.to_dict() for session in sessions]
        with open(self.sessions_file, 'w', encoding='utf-8') as f:
            json.dump(sessions_data, f, ensure_ascii=False, indent=2)
        self.sessions_cache = sessions  # 更新缓存

    def create_session(self, name: str, host: str, username: str, port: int,
                       auth_type: str, password: str = '', key_path: str = '') -> Session:
        """创建新会话"""
        # 检查内存缓存中的会话名称
        existing_names = [s.name for s in self.sessions_cache]
        if name in existing_names:
            raise ValueError(f"会话名称 '{name}' 已存在")

        new_session = Session({
            'name': name,
            'host': host,
            'username': username,
            'port': port,
            'auth_type': auth_type,
            'password': password,
            'key_path': key_path,
            'console_content': f'Welcome to SSH Session: {name}\n{username}@{host}:~$ '
        })

        sessions = self.sessions_cache.copy()
        sessions.append(new_session)
        self.save_sessions(sessions)

        return new_session

    def delete_session(self, session_id: str):
        """删除会话"""
        sessions = [s for s in self.sessions_cache if s.id != session_id]
        self.save_sessions(sessions)

    def get_session(self, session_id: str) -> Session:
        """获取指定会话"""
        for session in self.sessions_cache:
            if session.id == session_id:
                return session
        return None

    def session_name_exists(self, name: str) -> bool:
        """检查会话名称是否存在"""
        return any(s.name == name for s in self.sessions_cache)

    def _ensure_config_dir(self):
        """确保配置目录存在"""
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def _init_sessions_file(self):
        """初始化会话文件"""
        if not self.sessions_file.exists():
            default_session = Session({
                'name': '默认会话',
                'console_content': 'Welcome to SSH\nuser@host:~$ '
            })
            self.save_sessions([default_session])

    def get_session_by_name(self, name: str) -> Session:
        """根据会话名称获取会话"""
        for session in self.sessions_cache:
            if session.name == name:
                return session
        return None
