from ..constants import BALANCE_DECIMALS


class InsufficientFundsError(Exception):
    """Недостаточно средств на кошельке"""

    def __init__(self, available, required, code):
        super().__init__(
            f"Недостаточно средств: доступно "
            f"{available:.{BALANCE_DECIMALS}f} {code}, "
            f"требуется {required:.{BALANCE_DECIMALS}f} {code}"
        )


class CurrencyNotFoundError(Exception):
    """Валюта не найдена в реестре"""

    def __init__(self, code):
        super().__init__(f"Неизвестная валюта '{code}'")


class ApiRequestError(Exception):
    """Сбой внешнего API"""

    def __init__(self, reason):
        super().__init__(f"Ошибка при обращении к внешнему API: {reason}")