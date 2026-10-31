"""Конфигурация Parser Service.

Секреты (API-ключ) — из .env в корне проекта. Остальное — константы
или SettingsLoader (BASE_CURRENCY, чтобы совпадать с Core).
"""

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

from ..constants import PARSER_REQUEST_TIMEOUT_DEFAULT
from ..infra.settings import BASE_DIR, SettingsLoader

# .env в корне проекта (если есть)
load_dotenv(BASE_DIR / ".env")


@dataclass
class ParserConfig:
    """Параметры Parser Service."""

    EXCHANGERATE_API_KEY: str = field(
        default_factory=lambda: os.getenv("EXCHANGERATE_API_KEY", "")
    )

    SOURCE_ALIASES: dict = field(default_factory=lambda: {
        "coingecko": "CoinGecko",
        "exchangerate": "ExchangeRate-API",
    })

    COINGECKO_URL: str = "https://api.coingecko.com/api/v3/simple/price"
    EXCHANGERATE_API_URL: str = "https://v6.exchangerate-api.com/v6"

    BASE_CURRENCY: str = field(
        default_factory=lambda: SettingsLoader().get("default_base_currency")
    )

    FIAT_CURRENCIES: tuple = ("EUR", "GBP", "RUB")
    CRYPTO_CURRENCIES: tuple = ("BTC", "ETH", "SOL")
    CRYPTO_ID_MAP: dict = field(default_factory=lambda: {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "SOL": "solana",
    })

    REQUEST_TIMEOUT: int = PARSER_REQUEST_TIMEOUT_DEFAULT