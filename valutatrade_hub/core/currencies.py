from abc import ABC, abstractmethod

from .exceptions import CurrencyNotFoundError
from ..constants import (
    CURRENCY_CODE_MIN_LENGTH,
    CURRENCY_CODE_MAX_LENGTH,
    MARKET_CAP_DECIMALS,
)

class Currency(ABC):
    """Класс для абстрактной валюты"""

    def __init__(self, name, code):
        """Конструктор. Проверяет name на заполненность и длину code"""

        if not isinstance(name, str) or not name.strip():
            raise ValueError("Имя валюты не может быть пустым")
        if not isinstance(code, str):
            raise ValueError("Код валюты должен быть строкой")

        code = code.strip()
        code_len = len(code)
        if (code_len < CURRENCY_CODE_MIN_LENGTH
                or code_len > CURRENCY_CODE_MAX_LENGTH
                or " " in code):
            raise ValueError(
                f"Код валюты: {CURRENCY_CODE_MIN_LENGTH}–{CURRENCY_CODE_MAX_LENGTH} "
                f"символов, без пробелов"
            )
        code = code.upper()
        if not code.isalnum():
            raise ValueError("Код валюты: только буквы и цифры")

        self.name = name.strip()
        self.code = code

    @abstractmethod
    def get_display_info(self):
        """Строковое представление"""


class FiatCurrency(Currency):
    """Класс фиатной валюты"""

    def __init__(self, name, code, issuing_country):
        """Конструктор. Создает фиатную валюту"""

        super().__init__(name, code)
        if not isinstance(issuing_country, str) or not issuing_country.strip():
            raise ValueError("Страна эмиссии не может быть пустой")
        self.issuing_country = issuing_country.strip()

    def get_display_info(self):
        """Возвращает строка вида: 
        [FIAT] USD — US Dollar (Issuing: United States)"""

        return (f"[FIAT] {self.code} — {self.name} "
                f"(Issuing: {self.issuing_country})")


class CryptoCurrency(Currency):
    """Класс криптовалюты"""

    def __init__(self, name, code, algorithm, market_cap):
        """Конструктор. Создает криптовалюту"""

        super().__init__(name, code)
        if not isinstance(algorithm, str) or not algorithm.strip():
            raise ValueError("Алгоритм не может быть пустым")
        if type(market_cap) not in (int, float):
            raise ValueError("Капитализация должна быть числом")
        if market_cap < 0:
            raise ValueError("Капитализация не может быть отрицательной")
        self.algorithm = algorithm.strip()
        self.market_cap = float(market_cap)

    def get_display_info(self):
        """Возвращает строка вида: 
        [CRYPTO] BTC — Bitcoin (Algo: SHA-256, MCAP: 1.12e12)"""

        mcap = f"{self.market_cap:.{MARKET_CAP_DECIMALS}e}".replace("e+", "e")
        return (f"[CRYPTO] {self.code} — {self.name} "
                f"(Algo: {self.algorithm}, MCAP: {mcap})")


# реестр

_CURRENCIES = {
    "USD": FiatCurrency("US Dollar", "USD", "United States"),
    "EUR": FiatCurrency("Euro", "EUR", "Eurozone"),
    "RUB": FiatCurrency("Russian Ruble", "RUB", "Russia"),
    "BTC": CryptoCurrency("Bitcoin", "BTC", "SHA-256", 1.12e12),
    "ETH": CryptoCurrency("Ethereum", "ETH", "Ethash", 4.0e11),
}


def get_currency(code):
    """Возвращает валюту по коду"""

    if not isinstance(code, str):
        raise CurrencyNotFoundError(code)
    key = code.strip().upper()
    if key not in _CURRENCIES:
        raise CurrencyNotFoundError(code)
    return _CURRENCIES[key]

def supported_codes():
    """Вернуть список кодов валют из реестра"""

    return list(_CURRENCIES.keys())