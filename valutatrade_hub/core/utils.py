import hashlib
import json

from ..constants import (
    RATES_FILE,
    SMALL_RATE_THRESHOLD,
    SMALL_RATE_DECIMALS,
    LARGE_RATE_DECIMALS,
)


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

# Функции для работы с json

def load_json(path, fallback=None):
    """Возвращает содержимое из JSON-файла.
    Если файла нет, он пуст или содержит 
    битый JSON — вернет fallback, или []
    """

    if fallback is None:
        fallback = []
    if not path.exists():
        return fallback
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return fallback


def save_json(path, data):
    """Записывает данные в JSON-файл (создаёт папку при необходимости)"""

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_rates():
    """Возвращает словарь курсов из rates.json"""
    
    rates = load_json(RATES_FILE, {})
    if not isinstance(rates, dict):
        return {}
    data = rates.get("data", {})
    if not isinstance(data, dict):
        return {}
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