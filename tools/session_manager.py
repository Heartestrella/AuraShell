import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List


class Session:
    def __init__(self, session_data: Dict[str, Any] = None):
        default_values = {
            'id': f"session_{datetime.now().timestamp()}",
            'name': 'New Session',
            'host': 'localhost',
            'username': 'user',
            'port': 22,
            'auth_type': 'password',
            'password': '',
            'key_path': '',
            'status': 'disconnected',
            'created_at': datetime.now().isoformat(),
            'history': [],
            'console_content': '',
            'host_key': '',
            'processes_md5': '',
            'proxy_type': 'None',
            'proxy_host': '',
            'proxy_port': 0,
            'proxy_username': '',
            'proxy_password': '',
            "ssh_default_path": "",
            "file_manager_default_path": ""
        }
        if session_data:
            for key, default_value in default_values.items():
                setattr(self, key, session_data.get(key, default_value))
        else:
            for key, value in default_values.items():
                setattr(self, key, value)

    def to_dict(self) -> Dict[str, Any]:
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
            'console_content': self.console_content,
            'host_key': self.host_key,
            'processes_md5': self.processes_md5,
            'proxy_type': self.proxy_type,
            'proxy_host': self.proxy_host,
            'proxy_port': self.proxy_port,
            'proxy_username': self.proxy_username,
            'proxy_password': self.proxy_password,
            "ssh_default_path": self.ssh_default_path,
            "file_manager_default_path": self.file_manager_default_path
        }

    def add_command(self, command: str):
        if command.strip() and command not in self.history:
            self.history.append(command)
            if len(self.history) > 30:
                self.history.pop(0)

    def update_console(self, content: str):
        self.console_content = content

    def set_host_key(self, host_key: str, session_manager):
        self.host_key = host_key

    def set_processes_md5(self, md5: str, session_manager):
        self.processes_md5 = md5
        session_manager.save_sessions(session_manager.sessions_cache)


class SessionManager:
    def __init__(self):
        self.config_dir = Path.home() / ".config" / "pyqt-ssh"
        self.sessions_file = self.config_dir / "sessions.json"
        self._ensure_config_dir()
        self._init_sessions_file()
        self.sessions_cache = self.load_sessions()

    def load_sessions(self) -> List[Session]:
        try:
            with open(self.sessions_file, 'r', encoding='utf-8') as f:
                sessions_data = json.load(f)
                migrated_sessions = []
                for session_data in sessions_data:
                    migrated_session_data = self._migrate_session_data(
                        session_data)
                    migrated_sessions.append(Session(migrated_session_data))
                return migrated_sessions
        except Exception as e:
            print(f"加载会话文件时出错: {e}")
            return [Session()]

    def _migrate_session_data(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        current_fields = {
            'id': f"session_{datetime.now().timestamp()}",
            'name': 'Migrated Session',
            'host': 'localhost',
            'username': 'user',
            'port': 22,
            'auth_type': 'password',
            'password': '',
            'key_path': '',
            'status': 'disconnected',
            'created_at': datetime.now().isoformat(),
            'history': [],
            'console_content': '',
            'host_key': '',
            'processes_md5': '',
            'proxy_type': 'None',
            'proxy_host': '',
            'proxy_port': 0,
            'proxy_username': '',
            'proxy_password': '',
            "ssh_default_path": "",
            "file_manager_default_path": ""
        }
        migrated_data = session_data.copy()
        for field, default_value in current_fields.items():
            if field not in migrated_data:
                migrated_data[field] = default_value
        return migrated_data

    def save_sessions(self, sessions: List[Session]):
        sessions_data = [session.to_dict() for session in sessions]
        with open(self.sessions_file, 'w', encoding='utf-8') as f:
            json.dump(sessions_data, f, ensure_ascii=False, indent=2)
        self.sessions_cache = sessions

    def create_session(self, name: str, host: str, username: str, port: int,
                       auth_type: str, password: str = '', key_path: str = '',
                       host_key: str = '', processes_md5: str = '',
                       proxy_type: str = 'None', proxy_host: str = '', proxy_port: int = 0,
                       proxy_username: str = '', proxy_password: str = '', ssh_default_path: str = '', file_manager_default_path: str = '') -> Session:
        existing_names = [s.name for s in self.sessions_cache]
        if name in existing_names:
            raise ValueError(
                f"A session with the name '{name}' already exists")
        new_session = Session({
            'id': f"session_{datetime.now().timestamp()}",
            'name': name,
            'host': host,
            'username': username,
            'port': port,
            'auth_type': auth_type,
            'password': password,
            'key_path': key_path,
            'status': 'disconnected',
            'created_at': datetime.now().isoformat(),
            'history': [],
            'console_content': f'Welcome to SSH Session: {name}\n{username}@{host}:~$ ',
            'host_key': host_key,
            'processes_md5': processes_md5,
            'proxy_type': proxy_type,
            'proxy_host': proxy_host,
            'proxy_port': proxy_port,
            'proxy_username': proxy_username,
            'proxy_password': proxy_password,
            "ssh_default_path": ssh_default_path,
            "file_manager_default_path": file_manager_default_path
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

        self.sessions_cache = self.load_sessions()

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
        else:
            try:
                sessions = self.load_sessions()
                self.save_sessions(sessions)
            except Exception as e:
                print(f"迁移会话数据时出错: {e}")

    def get_session_by_name(self, name: str) -> Session:
        for session in self.sessions_cache:
            if session.name == name:
                return session

        self.sessions_cache = self.load_sessions()

        for session in self.sessions_cache:
            if session.name == name:
                return session

        return None

    def add_command_to_session(self, name: str, command: str):
        session = self.get_session_by_name(name)
        if session:
            session.add_command(command)
            self.save_sessions(self.sessions_cache)

    def clear_history(self, name: str):
        session = self.get_session_by_name(name)
        if session:
            session.history.clear()
            self.save_sessions(self.sessions_cache)

    def update_session_host_key(self, session_name: str, host_key: str):
        session = self.get_session_by_name(session_name)
        if session:
            session.host_key = host_key
            self.save_sessions(self.sessions_cache)

    def update_session_processes_md5(self, session_name: str, md5: str):
        session = self.get_session_by_name(session_name)
        if session:
            session.processes_md5 = md5
            self.save_sessions(self.sessions_cache)

    def check_and_migrate_all_sessions(self):
        sessions = self.load_sessions()
        self.save_sessions(sessions)
