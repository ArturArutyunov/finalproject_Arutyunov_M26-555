import hmac

from ..constants import BASE_CURRENCY, MIN_PASSWORD_LENGTH
from .exceptions import InsufficientFundsError
from .utils import get_rates, hash_password, validate_currency_code


class User:
    """Модель, описывающий пользователя системы"""

    def __init__(self, user_id, username, hashed_password, salt, registration_date):
        """Конструктор принимает все поля явно. Регистрация (генерация
        user_id, salt, hashed_password, registration_date) — в usecases"""

        self._user_id = user_id
        self.username = username
        self._hashed_password = hashed_password
        self._salt = salt
        self._registration_date = registration_date

    # геттеры

    @property
    def user_id(self):
        """Уникальный идентификатор пользователя"""

        return self._user_id

    @property
    def username(self) -> str:
        """Имя пользователя"""

        return self._username

    @property
    def registration_date(self):
        """Дата и время регистрации пользователя"""

        return self._registration_date

    # сеттеры 

    @username.setter
    def username(self, value: str) -> None:
        """Устанавливает имя пользователя с валидацией"""

        if not isinstance(value, str) or not value.strip():
            raise ValueError("Имя пользователя не может быть пустым")
        self._username = value.strip()

    # методы

    def get_user_info(self) -> None:
        """Возвращает информацию о пользователе"""

        return {
            "user_id": self._user_id,
            "username": self._username,
            "registration_date": self._registration_date.isoformat(),
        }

    def change_password(self, new_password: str) -> None:
        """Меняет пароль пользователя. (Длина - не менее 4 символов)"""

        if (not isinstance(new_password, str)
                or len(new_password) < MIN_PASSWORD_LENGTH):
            raise ValueError(
                f"Пароль должен быть не короче {MIN_PASSWORD_LENGTH} символов"
            )
        self._hashed_password = hash_password(new_password, self._salt)

    def verify_password(self, password: str) -> bool:
        """Проверяет, соответствует ли введённый пароль сохранённому хешу"""

        if not isinstance(password, str):
            return False
        
        return hmac.compare_digest(
            hash_password(password, self._salt),
            self._hashed_password
        )
    

class Wallet:
    """Кошелёк пользователя для одной конкретной валюты"""

    def __init__(self, currency_code, balance=0.0):
        """Конструктор. Создает кошелек в валюте currency_code"""

        self._currency_code = validate_currency_code(currency_code)
        self._balance = 0.0
        self.balance = balance

    # геттеры

    @property
    def currency_code(self):
        """Код валюты кошелька"""

        return self._currency_code

    @property
    def balance(self):
        """Текущий баланс кошелька"""

        return self._balance

    # сеттеры

    @balance.setter
    def balance(self, value):
        """Устанавливает баланс"""

        if type(value) not in (int, float):
            raise ValueError("Баланс должен быть числом")
        if value < 0:
            raise ValueError("Баланс не может быть отрицательным")
        self._balance = float(value)

    # методы

    def deposit(self, amount):
        """Пополнить баланс на {amount}"""

        if type(amount) not in (int, float):
            raise ValueError("Сумма пополнения должна быть числом")
        if amount <= 0:
            raise ValueError("Сумма пополнения должна быть положительной")
        self.balance = self._balance + amount

    def withdraw(self, amount):
        """Снять {amount} с баланса"""

        if type(amount) not in (int, float):
            raise ValueError("Сумма снятия должна быть числом")
        if amount <= 0:
            raise ValueError("Сумма снятия должна быть положительной")
        if amount > self._balance:
            raise InsufficientFundsError(
                self._balance, amount, self._currency_code
            )
        self.balance = self._balance - amount

    def get_balance_info(self):
        """Возвращает информацию о текущем балансе кошелька"""

        return {
            "currency_code": self._currency_code,
            "balance": self._balance,
        }


class Portfolio:
    """Портфель пользователя — набор кошельков по валютам"""

    def __init__(self, user_id, wallets=None, user_loader=None):
        """Создает портфель"""

        self._user_id = user_id
        self._wallets = {}
        self._user_loader = user_loader
        self._user_cache = None
        if wallets:
            for code, wallet in wallets.items():
                self._wallets[code] = wallet

    # геттеры

    @property
    def user_id(self):
        """ID владельца портфеля"""

        return self._user_id

    @property
    def user(self):
        """Владелец портфеля (объект User). Только чтение, без сеттера"""

        if self._user_cache is None and self._user_loader is not None:
            self._user_cache = self._user_loader(self._user_id)
        return self._user_cache


    @property
    def wallets(self):
        """Копия словаря кошельков"""
        
        return dict(self._wallets)

    # методы

    def add_currency(self, currency_code):
        """Добавляет новый кошелёк с нулевым балансом"""

        code = validate_currency_code(currency_code)
        if code in self._wallets:
            raise ValueError(f"Кошелёк {code} уже существует в портфеле")
        self._wallets[code] = Wallet(code)

    def get_wallet(self, currency_code):
        """Возвращает кошелёк по коду валюты"""

        if not isinstance(currency_code, str):
            return None
        return self._wallets.get(currency_code.strip().upper())

    def get_total_value(self, base_currency=BASE_CURRENCY, rates=None):
        """Считает суммарную стоимость всех кошельков в основной валюте"""
        
        base = base_currency.strip().upper()
        if rates is None:
            rates = get_rates()

        if base == BASE_CURRENCY:
            base_rate = 1.0
        else:
            key = f"{base}_{BASE_CURRENCY}"
            if key not in rates:
                raise ValueError(f"Курс для валюты {base} неизвестен")
            base_rate = rates[key]["rate"]

        total = 0.0
        for code, wallet in self._wallets.items():
            if code == BASE_CURRENCY:
                rate = 1.0
            else:
                key = f"{code}_{BASE_CURRENCY}"
                if key not in rates:
                    continue
                rate = rates[key]["rate"]
            total += wallet.balance * rate / base_rate
        return total