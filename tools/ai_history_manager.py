from pathlib import Path
import json
import re
from typing import List, Dict, Any
from datetime import datetime

class AIHistoryManager:
    def __init__(self):
        self.history_dir = Path.home() / ".config" / "pyqt-ssh" / "ai_chat_history"
        self._ensure_history_dir()

    def _ensure_history_dir(self):
        self.history_dir.mkdir(parents=True, exist_ok=True)

    def _sanitize_filename(self, name: str) -> str:
        # Remove invalid characters for filenames
        name = re.sub(r'[\\/*?:"<>|]', "", name)
        # Limit length to avoid issues with long filenames
        return name[:100]

    def save_history(self, conversation: List[Dict[str, Any]], first_message: str):
        filename = self._sanitize_filename(first_message) + ".json"
        filepath = self.history_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(conversation, f, ensure_ascii=False, indent=2)

    def list_histories(self) -> List[Dict[str, str]]:
        histories = []
        for f in self.history_dir.glob("*.json"):
            try:
                stat = f.stat()
                created_at = datetime.fromtimestamp(stat.st_ctime).isoformat()
                modified_at = datetime.fromtimestamp(stat.st_mtime).isoformat()
                histories.append({
                    "filename": f.name,
                    "createdAt": created_at,
                    "modifiedAt": modified_at
                })
            except FileNotFoundError:
                # File might be deleted during iteration
                continue
        # Sort by creation date, newest first
        histories.sort(key=lambda x: x['createdAt'], reverse=True)
        return histories

    def load_history(self, filename: str) -> List[Dict[str, Any]]:
        filepath = self.history_dir / filename
        if not filepath.exists():
            return []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []

    def delete_history(self, filename: str) -> bool:
        filepath = self.history_dir / filename
        if filepath.exists():
            filepath.unlink()
            return True
        return False