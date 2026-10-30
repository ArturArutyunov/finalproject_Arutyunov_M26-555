import hashlib
from datetime import datetime

from ..constants import (
    RATES_FILE,
    RATES_TTL_DEFAULT,
    SMALL_RATE_THRESHOLD,
    SMALL_RATE_DECIMALS,
    LARGE_RATE_DECIMALS,
)
from ..infra.database import DatabaseManager
from ..infra.settings import BASE_DIR, SettingsLoader
from .exceptions import ApiRequestError


def hash_password(password, salt):
    """Хеширует строку sha256(password + salt)"""
    
    return hashlib.sha256((password + salt).encode("utf-8")).hexdigest()

def format_rate(value):
    """Форматирует курс: < 1 → 8 знаков, иначе 2 знака"""

    if abs(value) < SMALL_RATE_THRESHOLD:
        return f"{value:.{SMALL_RATE_DECIMALS}f}".rstrip("0").rstrip(".")
    return f"{value:.{LARGE_RATE_DECIMALS}f}"


def format_timestamp(iso_str):
    """Форматирует время в формат
    ISO '2025-10-09T00:03:22' → '2025-10-09 00:03:22'
    если пусто - вернет (или 'нет данных')"""

    if not iso_str:
        return "нет данных"
    return str(iso_str).replace("T", " ").split(".")[0]


def refresh_rates():
    """Обновить курсы через Parser Service"""

    raise ApiRequestError("Курсы устарели, Parser Service недоступен")


def _extract_rates(raw):
    """Достать (data, meta) из прочитанного rates.json"""

    if not isinstance(raw, dict):
        raw = {}
    meta = raw.get("meta", {})
    if not isinstance(meta, dict):
        meta = {}
    data = raw.get("data", {})
    if not isinstance(data, dict):
        data = {}
    return data, meta


def _is_rates_fresh(meta):
    """Проверяет свежий ли кеш курсов"""

    last_refresh = meta.get("last_refresh")
    if not last_refresh:
        return False
    try:
        refreshed_at = datetime.fromisoformat(last_refresh)
    except (TypeError, ValueError):
        return False

    if refreshed_at.tzinfo is not None:
        now = datetime.now(refreshed_at.tzinfo)
    else:
        now = datetime.now()

    ttl = SettingsLoader().get("rates_ttl_seconds", RATES_TTL_DEFAULT)
    age_seconds = (now - refreshed_at).total_seconds()
    return age_seconds < ttl


def get_rates(with_meta=False):
    """Возвращает словарь курсов из rates.json
    Если кеш устарел — вызывает refresh_rates(). Если refresh_rates()
    бросает ApiRequestError — пробрасывает дальше"""

    db = DatabaseManager()
    data, meta = _extract_rates(db.read(RATES_FILE, {}))

    if not _is_rates_fresh(meta):
        refresh_rates()
        data, meta = _extract_rates(db.read(RATES_FILE, {}))

    if with_meta:
        return data, meta
    return data


# валидаторы

def validate_amount(amount):
    """Проверяет, что сумма — положительное число"""

    if type(amount) not in (int, float):
        raise ValueError("'amount' должен быть положительным числом")
    if amount <= 0:
        raise ValueError("'amount' должен быть положительным числом")


def validate_currency_code(currency_code):
    """Возвращает код в верхнем регистре без пробелов по краям"""

    if not isinstance(currency_code, str) or not currency_code.strip():
        raise ValueError("Код валюты не может быть пустым")
    return currency_code.strip().upper()