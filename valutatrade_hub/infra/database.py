import json
import os
import tempfile

from ..constants import JSON_INDENT
from .settings import BASE_DIR, SettingsLoader


class DatabaseManager:
    """Единственный экземпляр менеджера JSON-хранилища
    Способ Singleton: __new__. Выбран за минимализм и читаемость
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _path(self, filename):
        """Полный путь к файлу данных: BASE_DIR / data_dir / filename."""

        data_dir = SettingsLoader().get("data_dir")
        return BASE_DIR / data_dir / filename

    def read(self, filename, fallback=None):
        """Возвращает содержимое из JSON-файла.
        Если файла нет, он пуст или содержит 
        битый JSON — вернет fallback, или []
        """

        if fallback is None:
            fallback = []
        path = self._path(filename)
        if not path.exists():
            return fallback
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return fallback

    def write(self, filename, data):
        """Записывает данные в JSON-файл (создаёт папку при необходимости)"""

        path = self._path(filename)
        path.parent.mkdir(parents=True, exist_ok=True)

        fd, tmp_name = tempfile.mkstemp(
            dir=path.parent, prefix=path.name, suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=JSON_INDENT)
            os.replace(tmp_name, path)
        except Exception:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise

    def update(self, filename, record, key):
        """Обновляет данные. Возвращает новое состояние"""

        key_value = record[key]
        items = self.read(filename)
        if not isinstance(items, list):
            items = []

        for i, existing in enumerate(items):
            if existing.get(key) == key_value:
                items[i] = record
                break
        else:
            items.append(record)

        self.write(filename, items)
        return items