from pathlib import Path
import json
from typing import Dict, Any

class AIModelManager:
    def __init__(self):
        self.config_dir = Path.home() / ".config" / "pyqt-ssh"
        self.models_file = self.config_dir / "ai_models.json"
        self._ensure_config_dir()
        self.models_cache = self.load_models()

    def _ensure_config_dir(self):
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def _get_default_models(self) -> Dict[str, Dict[str, Any]]:
        return { "AuraShellVip": { "api_url": "https://aurashell-aichatapi.beefuny.shop/v1", "model_name": "AuraShellVip", "key":"68*w&t7457#h8S*LS@*W1q8I%DMXMq!MT8#!" } }

    def _init_models_file(self):
        if not self.models_file.exists():
            self.save_models(self._get_default_models())

    def load_models(self) -> Dict[str, Dict[str, Any]]:
        default_models = self._get_default_models()
        if not self.models_file.exists():
            self.save_models(default_models)
            return default_models
        loaded_models = {}
        try:
            with open(self.models_file, 'r', encoding='utf-8') as f:
                loaded_models = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error loading AI models file: {e}. Reinitializing with defaults.")
            loaded_models = {}
        loaded_models.update(default_models)
        self.save_models(loaded_models)
        return loaded_models

    def save_models(self, models: Dict[str, Dict[str, Any]]):
        with open(self.models_file, 'w', encoding='utf-8') as f:
            json.dump(models, f, ensure_ascii=False, indent=2)
        self.models_cache = models

    def get_model_names(self) -> list[str]:
        return list(self.models_cache.keys())

    def get_model_by_id(self, model_id: str) -> Dict[str, Any]:
        return self.models_cache.get(model_id)
