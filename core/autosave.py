import json
from PyQt6.QtCore import QObject, QTimer

class AutoSaver(QObject):
    def __init__(self, model, get_path_func, get_config_func=None, parent=None):
        super().__init__(parent)
        self.model = model
        self.get_path_func = get_path_func  # Callable that returns the current save path
        self.get_config_func = get_config_func # Callable that returns the current style config
        
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(1000)  # 1 second debounce
        self.timer.timeout.connect(self._perform_save)
        
        # Listen to model changes
        self.model.data_changed_signal.connect(self.request_save)

    def request_save(self):
        """Called when data changes. Resets the debounce timer."""
        self.timer.start()

    def _perform_save(self):
        """Actually writes the data to disk."""
        path = self.get_path_func()
        if not path:
            return
            
        entries = self.model.get_entries()
        data = {"entries": entries}
        if self.get_config_func:
            data["config"] = self.get_config_func()
            
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Auto-save failed: {e}")

    def load_from_file(self, path):
        """Loads entries from the specified JSON-formatted txt file."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            config = None
            if isinstance(data, dict):
                entries = data.get("entries", [])
                config = data.get("config", None)
            else:
                entries = data # Legacy list format
                
            # Clear old model and insert new ones
            self.model.beginResetModel()
            self.model.entries = entries
            self.model._max_authors = self.model._calculate_max_authors()
            self.model._headers = self.model._build_headers()
            self.model.endResetModel()
            return config
        except Exception as e:
            print(f"Failed to load from {path}: {e}")
            return False
