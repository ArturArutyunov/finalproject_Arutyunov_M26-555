import hashlib
import math
from datetime import datetime

from ..constants import (
    LARGE_RATE_DECIMALS,
    RATES_FILE,
    RATES_TTL_DEFAULT,
    SMALL_RATE_DECIMALS,
    SMALL_RATE_THRESHOLD,
)
from ..infra.database import DatabaseManager
from ..infra.settings import SettingsLoader
from ..parser_service.api_clients import (
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from ..parser_service.config import ParserConfig
from ..parser_service.storage import ParserStorage
from ..parser_service.updater import RatesUpdater


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

    config = ParserConfig()
    updater = RatesUpdater(
        clients=[CoinGeckoClient(config), ExchangeRateApiClient(config)],
        storage=ParserStorage(),
    )
    updater.run_update()

def _extract_rates(raw):
    """Достать (pairs, last_refresh) из прочитанного rates.json"""

    if not isinstance(raw, dict):
        raw = {}
    pairs = raw.get("pairs", {})
    if not isinstance(pairs, dict):
        pairs = {}
    return pairs, raw.get("last_refresh")


def _is_rates_fresh(last_refresh):
    """Проверяет свежий ли кеш курсов"""

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
    return (now - refreshed_at).total_seconds() < ttl


def get_rates(with_meta=False):
    """Возвращает словарь курсов из rates.json
    Если кеш устарел — вызывает refresh_rates()"""

    db = DatabaseManager()
    pairs, last_refresh = _extract_rates(db.read(RATES_FILE, {}))

    if not _is_rates_fresh(last_refresh):
        refresh_rates()
        pairs, last_refresh = _extract_rates(db.read(RATES_FILE, {}))

    if with_meta:
        return pairs, {"last_refresh": last_refresh}
    return pairs


# валидаторы

def validate_amount(amount):
    """Проверяет, что сумма — положительное число
    Дополнительная проверка на nan, inf
    """

    if (type(amount) not in (int, float)
            or not math.isfinite(amount)
            or amount <= 0):
        raise ValueError("'amount' должен быть положительным числом")


def validate_currency_code(currency_code):
    """Возвращает код в верхнем регистре без пробелов по краям"""

    if not isinstance(currency_code, str) or not currency_code.strip():
        raise ValueError("Код валюты не может быть пустым")
    return currency_code.strip().upper()