import secrets
from datetime import datetime

from ..constants import (
    MIN_PASSWORD_LENGTH,
    PORTFOLIOS_FILE,
    SALT_BYTES,
    USERS_FILE,
)
from ..decorators import log_action
from ..infra.database import DatabaseManager
from ..infra.settings import SettingsLoader
from .currencies import get_currency
from .models import Portfolio, User, Wallet
from .utils import (
    get_rates,
    hash_password,
    validate_amount,
    validate_currency_code,
)

_BASE_CURRENCY = SettingsLoader().get("default_base_currency")

def _next_user_id():
    """Возвращает следующий id для нового пользователя"""

    users = DatabaseManager().read(USERS_FILE)
    if not isinstance(users, list) or not users:
        return 1
    return max(u.get("user_id", 0) for u in users) + 1


@log_action("REGISTER")
def register_user(username, password):
    """Регистрирует нового пользователя в системе"""

    if not isinstance(username, str) or not username.strip():
        raise ValueError("Имя пользователя не может быть пустым")
    username = username.strip()
    if not isinstance(password, str) or len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Пароль должен быть не короче {MIN_PASSWORD_LENGTH} символов")

    db = DatabaseManager()
    users = db.read(USERS_FILE)
    if not isinstance(users, list):
        users = []
    for record in users:
        if record.get("username") == username:
            raise ValueError(f"Имя пользователя '{username}' уже занято")

    user_id = _next_user_id()
    salt = secrets.token_hex(SALT_BYTES)
    hashed = hash_password(password, salt)
    registration_date = datetime.now()

    user = User(user_id, username, hashed, salt, registration_date)

    users.append({
        "user_id": user_id,
        "username": username,
        "hashed_password": hashed,
        "salt": salt,
        "registration_date": registration_date.isoformat(),
    })
    db.write(USERS_FILE, users)


    portfolios = db.read(PORTFOLIOS_FILE)
    if not isinstance(portfolios, list):
        portfolios = []
    portfolios.append({"user_id": user_id, "wallets": {}})
    db.write(PORTFOLIOS_FILE, portfolios)

    return user


def load_user_by_id(user_id):
    """Возвращает объект User из users.json по id (или None)"""

    users = DatabaseManager().read(USERS_FILE)
    if not isinstance(users, list):
        return None
    for record in users:
        if record.get("user_id") == user_id:
            return User(
                record["user_id"],
                record["username"],
                record["hashed_password"],
                record["salt"],
                datetime.fromisoformat(record["registration_date"]),
            )
    return None


@log_action("LOGIN")
def login(username, password):
    """Провреяет имя/пароль. При успешной валидации возвращает user_id"""
    
    if not isinstance(username, str) or not isinstance(password, str):
        raise ValueError("Пользователь не найден")

    users = DatabaseManager().read(USERS_FILE)
    if not isinstance(users, list):
        users = []

    for record in users:
        if record.get("username") == username:
            user = User(
                record["user_id"],
                record["username"],
                record["hashed_password"],
                record["salt"],
                datetime.fromisoformat(record["registration_date"]),
            )
            if user.verify_password(password):
                return user.user_id
            raise ValueError("Неверный пароль")

    raise ValueError(f"Пользователь '{username}' не найден")


def get_rate_value(from_code, to_code, rates):
    """Возвращает курс from_code → to_code по словарю rates"""

    from_code = validate_currency_code(from_code)
    to_code = validate_currency_code(to_code)

    if from_code == to_code:
        return 1.0

    # Прямой
    direct = f"{from_code}_{to_code}"
    if direct in rates:
        return rates[direct]["rate"]

    # Обратный
    inverse = f"{to_code}_{from_code}"
    if inverse in rates:
        return 1.0 / rates[inverse]["rate"]

    # кросс через USD
    from_usd = 1.0 if from_code == _BASE_CURRENCY else None
    to_usd = 1.0 if to_code == _BASE_CURRENCY else None
    if from_usd is None:
        key = f"{from_code}_{_BASE_CURRENCY}"
        if key not in rates:
            raise ValueError(f"Курс {from_code}→{to_code} недоступен")
        from_usd = rates[key]["rate"]
    if to_usd is None:
        key = f"{to_code}_{_BASE_CURRENCY}"
        if key not in rates:
            raise ValueError(f"Курс {from_code}→{to_code} недоступен")
        to_usd = rates[key]["rate"]

    return from_usd / to_usd


def convert(amount, from_code, to_code, rates=None):
    """Сконвертировать amount из from_code в to_code"""

    if rates is None:
        rates = get_rates()
    rate = get_rate_value(from_code, to_code, rates)
    return amount * rate


def load_portfolio(user_id):
    """Возвращает портфель пользователя из portfolios.json"""

    portfolios = DatabaseManager().read(PORTFOLIOS_FILE)
    if not isinstance(portfolios, list):
        portfolios = []

    for record in portfolios:
        if record.get("user_id") == user_id:
            wallets = {}
            for code, w in record.get("wallets", {}).items():
                wallets[code] = Wallet(code, w.get("balance", 0.0))
            return Portfolio(user_id, wallets, user_loader=load_user_by_id)

    return Portfolio(user_id, user_loader=load_user_by_id)


def save_portfolio(portfolio):
    """Сохраняет портфель в portfolios.json"""

    wallets_data = {
        code: {"balance": wallet.balance}
        for code, wallet in portfolio.wallets.items()
    }
    record = {"user_id": portfolio.user_id, "wallets": wallets_data}
    DatabaseManager().update(PORTFOLIOS_FILE, record, key="user_id")


def get_portfolio_info(user_id, base_currency=_BASE_CURRENCY):
    """Возвращает данные портфеля для отображения"""

    base_currency_obj = get_currency(base_currency)
    base = base_currency_obj.code
    rates = get_rates()

    if (base != _BASE_CURRENCY
            and f"{base}_{_BASE_CURRENCY}" not in rates
            and f"{_BASE_CURRENCY}_{base}" not in rates):
        raise ValueError(f"Неизвестная базовая валюта '{base}'")

    portfolio = load_portfolio(user_id)

    rows = []
    for code, wallet in portfolio.wallets.items():
        try:
            value = convert(wallet.balance, code, base, rates)
        except ValueError:
            print(f"Курс для {code}→{base} неизвестен, кошелёк пропущен")
            continue
        rows.append({
            "currency_code": code,
            "balance": wallet.balance,
            "value": value,
        })

    total = portfolio.get_total_value(base, rates)

    return {
        "user": portfolio.user,
        "base": base,
        "wallets": rows,
        "total": total,
    }


@log_action("BUY", verbose=True, base=_BASE_CURRENCY)
def buy(user_id, currency_code, amount):
    """Купить amount валюты currency_code (зачисление на кошелёк).
    USD не списывается. Если кошелька currency_code нет — создаёт.
    Для отчёта считает оценочную стоимость amount * rate в USD
    """

    validate_amount(amount)
    currency = get_currency(currency_code)
    code = currency.code
    if code == _BASE_CURRENCY:
        raise ValueError(f"Нельзя купить {_BASE_CURRENCY} за {_BASE_CURRENCY}")

    rates = get_rates()
    try:
        rate = get_rate_value(code, _BASE_CURRENCY, rates)
    except ValueError:
        raise ValueError(f"Не удалось получить курс для {code}→{_BASE_CURRENCY}")

    portfolio = load_portfolio(user_id)

    target = portfolio.get_wallet(code)
    if target is None:
        portfolio.add_currency(code)
        target = portfolio.get_wallet(code)

    balance_before = target.balance
    target.deposit(amount)
    save_portfolio(portfolio)

    return {
        "currency_code": code,
        "amount": amount,
        "rate": rate,
        "cost_usd": amount * rate,
        "balance_before": balance_before,
        "balance_after": target.balance,
    }


@log_action("SELL", verbose=True, base=_BASE_CURRENCY)
def sell(user_id, currency_code, amount):
    """Продать amount валюты currency_code (списание с кошелька).
    USD не начисляется. Для отчёта считает 
    оценочную выручку amount * rate в USD"""

    validate_amount(amount)
    currency = get_currency(currency_code)
    code = currency.code
    if code == _BASE_CURRENCY:
        raise ValueError(f"Нельзя продать {_BASE_CURRENCY} за {_BASE_CURRENCY}")

    rates = get_rates()
    try:
        rate = get_rate_value(code, _BASE_CURRENCY, rates)
    except ValueError:
        raise ValueError(f"Не удалось получить курс для {code}→{_BASE_CURRENCY}")

    portfolio = load_portfolio(user_id)

    wallet = portfolio.get_wallet(code)
    if wallet is None:
        raise ValueError(
            f"У вас нет кошелька '{code}'. Добавьте валюту: "
            f"она создаётся автоматически при первой покупке"
        )

    balance_before = wallet.balance
    wallet.withdraw(amount)
    save_portfolio(portfolio)

    return {
        "currency_code": code,
        "amount": amount,
        "rate": rate,
        "income_usd": amount * rate,
        "balance_before": balance_before,
        "balance_after": wallet.balance,
    }

def get_rate_info(code_from, code_to):
    """Возвращает курс from_code → to_code и метку времени обновления.
    Поддерживает прямой ключ, обратный и кросс через USD"""

    from_currency = get_currency(code_from)
    to_currency = get_currency(code_to)

    from_code = from_currency.code
    to_code = to_currency.code
    rates = get_rates()

    direct_key = f"{from_code}_{to_code}"
    inverse_key = f"{to_code}_{from_code}"

    rate = None
    updated_at = None

    if direct_key in rates:
        rate = rates[direct_key]["rate"]
        updated_at = rates[direct_key].get("updated_at")
    elif inverse_key in rates:
        rate = 1.0 / rates[inverse_key]["rate"]
        updated_at = rates[inverse_key].get("updated_at")
    else:
        try:
            from_usd = (1.0 if from_code == _BASE_CURRENCY
                else rates[f"{from_code}_{_BASE_CURRENCY}"]["rate"])
            to_usd = (1.0 if to_code == _BASE_CURRENCY
                    else rates[f"{to_code}_{_BASE_CURRENCY}"]["rate"])

            rate = from_usd / to_usd

            stamps = []
            if from_code != _BASE_CURRENCY:
                stamps.append(rates[f"{from_code}_{_BASE_CURRENCY}"].get("updated_at"))
            if to_code != _BASE_CURRENCY:
                stamps.append(rates[f"{to_code}_{_BASE_CURRENCY}"].get("updated_at"))
            stamps = [s for s in stamps if s]
            updated_at = max(stamps) if stamps else None
        except KeyError:
            raise ValueError(
                f"Курс {from_code}→{to_code} недоступен. "
                f"Повторите попытку позже."
            )

    reverse = None
    reverse_updated_at = None
    if rate:
        reverse = 1.0 / rate
        reverse_updated_at = updated_at

    return {
        "from": from_code,
        "to": to_code,
        "rate": rate,
        "updated_at": updated_at,
        "reverse": reverse,
        "reverse_updated_at": reverse_updated_at,
    }

