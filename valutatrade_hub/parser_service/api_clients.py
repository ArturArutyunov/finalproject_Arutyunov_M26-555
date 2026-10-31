import logging
from abc import ABC, abstractmethod

import requests

from ..core.exceptions import ApiRequestError
from .config import ParserConfig

logger = logging.getLogger("valutatrade.parser")

_HTTP_OK = 200


class BaseApiClient(ABC):
    """Абстрактный клиент API курсов"""

    SOURCE_NAME = "unknown"

    def __init__(self, config: ParserConfig):
        self.config = config

    @abstractmethod
    def fetch_rates(self):
        """Наследники реализуют fetch_rates(), возвращая словарь
        {f"{CODE}_{BASE_CURRENCY}": rate}"""
        pass


class CoinGeckoClient(BaseApiClient):
    """CoinGecko: криптовалюты к BASE_CURRENCY"""

    SOURCE_NAME = "CoinGecko"

    def fetch_rates(self):
        """Вернуть {CODE_BASE: rate} для криптовалют"""

        ids = ",".join(
            self.config.CRYPTO_ID_MAP[c]
            for c in self.config.CRYPTO_CURRENCIES
            if c in self.config.CRYPTO_ID_MAP
        )
        vs = self.config.BASE_CURRENCY.lower()

        try:
            response = requests.get(
                self.config.COINGECKO_URL,
                params={"ids": ids, "vs_currencies": vs},
                timeout=self.config.REQUEST_TIMEOUT,
            )
        except requests.exceptions.RequestException as e:
            raise ApiRequestError(f"CoinGecko: сетевая ошибка — {e}")

        if response.status_code != _HTTP_OK:
            raise ApiRequestError(
                f"CoinGecko: HTTP {response.status_code} — {response.text}"
            )

        try:
            data = response.json()
        except ValueError as e:
            raise ApiRequestError(f"CoinGecko: неверный JSON — {e}")

        if not isinstance(data, dict):
            raise ApiRequestError("CoinGecko: ожидался объект в ответе")

        result = {}
        for code in self.config.CRYPTO_CURRENCIES:
            cg_id = self.config.CRYPTO_ID_MAP.get(code)
            if not cg_id:
                continue
            entry = data.get(cg_id)
            if not isinstance(entry, dict):
                logger.warning("CoinGecko: нет данных для %s (%s)", code, cg_id)
                continue
            rate = entry.get(vs)
            if not isinstance(rate, (int, float)) or rate <= 0:
                logger.warning("CoinGecko: некорректный rate для %s", code)
                continue
            result[f"{code}_{self.config.BASE_CURRENCY}"] = float(rate)
        return result


class ExchangeRateApiClient(BaseApiClient):
    """ExchangeRate-API (v6): фиат к BASE_CURRENCY"""

    SOURCE_NAME = "ExchangeRate-API"

    def fetch_rates(self):
        """Вернуть {CODE_BASE: rate} для фиатных валют"""

        if not self.config.EXCHANGERATE_API_KEY:
            raise ApiRequestError("EXCHANGERATE_API_KEY не задан")

        url = (
            f"{self.config.EXCHANGERATE_API_URL}/"
            f"{self.config.EXCHANGERATE_API_KEY}/latest/"
            f"{self.config.BASE_CURRENCY}"
        )

        try:
            response = requests.get(
                url, timeout=self.config.REQUEST_TIMEOUT
            )
        except requests.exceptions.RequestException as e:
            raise ApiRequestError(f"ExchangeRate-API: сетевая ошибка — {e}")

        if response.status_code != _HTTP_OK:
            raise ApiRequestError(
                f"ExchangeRate-API: HTTP {response.status_code} — "
                f"{response.text}"
            )

        try:
            data = response.json()
        except ValueError as e:
            raise ApiRequestError(f"ExchangeRate-API: неверный JSON — {e}")

        if not isinstance(data, dict):
            raise ApiRequestError("ExchangeRate-API: ожидался объект в ответе")

        if data.get("result") == "error":
            reason = data.get("error-type", "unknown")
            raise ApiRequestError(f"ExchangeRate-API: {reason}")

        conversion = data.get("conversion_rates")
        if not isinstance(conversion, dict):
            raise ApiRequestError(
                "ExchangeRate-API: нет conversion_rates в ответе"
            )

        result = {}
        for code in self.config.FIAT_CURRENCIES:
            if code == self.config.BASE_CURRENCY:
                continue
            rate = conversion.get(code)
            if not isinstance(rate, (int, float)) or rate <= 0:
                logger.warning(
                    "ExchangeRate-API: некорректный rate для %s", code
                )
                continue
            result[f"{code}_{self.config.BASE_CURRENCY}"] = 1.0 / rate
        return result