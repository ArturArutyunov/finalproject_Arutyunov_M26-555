
import tomllib
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
PYPROJECT_FILE = ROOT_DIR / "pyproject.toml"
SECTION = "valutatrade"

_MISSING = object()

class SettingsLoader:
    """Единственный экземпляр конфигурации.
    Способ Singleton: __new__. Выбран за минимализм и читаемость
    Хранит значения из [tool.valutatrade] или default
ъ   Для обновления конифгурации необходимо вызвать reload()
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self):
        """Получает [tool.valutatrade] из pyproject.toml"""

        if not PYPROJECT_FILE.exists():
            self._config = {}
            return
        with open(PYPROJECT_FILE, "rb") as f:
            data = tomllib.load(f)
        tool = data.get("tool", {})
        self._config = tool.get(SECTION, {}) or {}

    def get(self, key, default=_MISSING):
        """Возвращает значение по ключу.
        Если ключа нет и default не передан — KeyError.
        """

        if key in self._config:
            return self._config[key]
        if default is _MISSING:
            raise KeyError(key)
        return default

    def reload(self):
        """Обновляет конфигурацию из pyproject.toml"""

        self._load()