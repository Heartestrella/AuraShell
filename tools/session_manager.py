# session.py
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List


class Session:
    def __init__(self, session_data: Dict[str, Any] = None):
        self.id = session_data.get(
            'id', f"session_{datetime.now().timestamp()}") if session_data else f"session_{datetime.now().timestamp()}"
        self.name = session_data.get(
            'name', 'New Session') if session_data else 'New Session'
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
        """Convert the session to a dictionary"""
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
        """Add command to history"""
        if command.strip() and command not in self.history:
            self.history.append(command)
            if len(self.history) > 30:
                self.history.pop(0)

    def update_console(self, content: str):
        """Update console content"""
        self.console_content = content


class SessionManager:
    def __init__(self):
        self.config_dir = Path.home() / ".config" / "pyqt-ssh"
        self.sessions_file = self.config_dir / "sessions.json"
        self._ensure_config_dir()
        self._init_sessions_file()
        self.sessions_cache = self.load_sessions()  # Adding memory cache

    def load_sessions(self) -> List[Session]:
        try:
            with open(self.sessions_file, 'r', encoding='utf-8') as f:
                sessions_data = json.load(f)
                return [Session(session_data) for session_data in sessions_data]
        except:
            return [Session()]

    def save_sessions(self, sessions: List[Session]):

        sessions_data = [session.to_dict() for session in sessions]
        with open(self.sessions_file, 'w', encoding='utf-8') as f:
            json.dump(sessions_data, f, ensure_ascii=False, indent=2)
        self.sessions_cache = sessions  # Updating cache

    def create_session(self, name: str, host: str, username: str, port: int,
                       auth_type: str, password: str = '', key_path: str = '') -> Session:

        existing_names = [s.name for s in self.sessions_cache]
        if name in existing_names:
            raise ValueError(
                f"A session with the name '{name}' already exists")

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

        sessions = [s for s in self.sessions_cache if s.id != session_id]
        self.save_sessions(sessions)

    def get_session(self, session_id: str) -> Session:

        for session in self.sessions_cache:
            if session.id == session_id:
                return session
        return None

    def session_name_exists(self, name: str) -> bool:

        return any(s.name == name for s in self.sessions_cache)

    def _ensure_config_dir(self):
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def _init_sessions_file(self):
        if not self.sessions_file.exists():
            default_session = Session({
                'name': 'Default Session',
                'console_content': 'Welcome to SSH\nuser@host:~$ '
            })
            self.save_sessions([default_session])

    def get_session_by_name(self, name: str) -> Session:
        for session in self.sessions_cache:
            if session.name == name:
                return session
        return None

    def add_command_to_session(self, name: str, command: str):
        session = self.get_session_by_name(name)
        if session:
            session.add_command(command)
            print(session.history)
            self.save_sessions(self.sessions_cache)

    def clear_history(self, name: str):
        """清空指定 session 的历史命令"""
        session = self.get_session_by_name(name)
        if session:
            session.history.clear()
            self.save_sessions(self.sessions_cache)
