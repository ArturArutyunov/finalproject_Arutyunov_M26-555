import json
import os
import tempfile

from ..constants import (
    EXCHANGE_RATES_FILENAME,
    JSON_INDENT,
    RATES_FILE,
)
from ..infra.settings import BASE_DIR, SettingsLoader


class ParserStorage:
    """Чтение/запись файлов Parser Service"""

    def _path(self, filename):
        data_dir = SettingsLoader().get("data_dir")
        return BASE_DIR / data_dir / filename

    def _read(self, filename, fallback):
        path = self._path(filename)
        if not path.exists():
            return fallback
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return fallback

    def _write(self, filename, data):
        path = self._path(filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(
            dir=path.parent, prefix=path.name, suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=JSON_INDENT)
            os.replace(tmp, path)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    def append_history(self, entry):
        """Добавляет запись в историю"""

        history = self._read(EXCHANGE_RATES_FILENAME, [])
        if not isinstance(history, list):
            history = []
        entry_id = entry.get("id")
        for existing in history:
            if existing.get("id") == entry_id:
                return False
        history.append(entry)
        self._write(EXCHANGE_RATES_FILENAME, history)
        return True

    def update_snapshot(self, new_pairs, last_refresh):
        """Обновиляет rates.json"""

        snapshot = self._read(RATES_FILE, {"pairs": {}, "last_refresh": None})
        if not isinstance(snapshot, dict):
            snapshot = {"pairs": {}, "last_refresh": None}

        pairs = snapshot.get("pairs", {})
        if not isinstance(pairs, dict):
            pairs = {}

        for pair, data in new_pairs.items():
            current = pairs.get(pair)
            if current is None:
                pairs[pair] = data
            elif data.get("updated_at", "") > current.get("updated_at", ""):
                pairs[pair] = data

        snapshot["pairs"] = pairs
        if last_refresh:
            snapshot["last_refresh"] = last_refresh
        self._write(RATES_FILE, snapshot)