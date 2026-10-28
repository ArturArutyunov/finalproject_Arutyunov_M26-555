import secrets
from datetime import datetime

from .models import Portfolio, User, Wallet
from ..constants import (
    BASE_CURRENCY,
    BALANCE_DECIMALS,
    MIN_PASSWORD_LENGTH,
    SALT_BYTES,
    PORTFOLIOS_FILE,
    USERS_FILE,
)
from .utils import (
    get_rates,
    hash_password,
    load_json,
    save_json,
    validate_amount,
    validate_currency_code,
)


def _next_user_id():
    """Возвращает следующий id для нового пользователя"""

    users = load_json(USERS_FILE)
    if not isinstance(users, list) or not users:
        return 1
    return max(u.get("user_id", 0) for u in users) + 1

def register_user(username, password):
    """Регистрирует нового пользователя в системе"""

    if not isinstance(username, str) or not username.strip():
        raise ValueError("Имя пользователя не может быть пустым")
    username = username.strip()
    if not isinstance(password, str) or len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Пароль должен быть не короче {MIN_PASSWORD_LENGTH} символов")

    users = load_json(USERS_FILE)
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
    save_json(USERS_FILE, users)

    portfolios = load_json(PORTFOLIOS_FILE)
    if not isinstance(portfolios, list):
        portfolios = []
    portfolios.append({"user_id": user_id, "wallets": {}})
    save_json(PORTFOLIOS_FILE, portfolios)

    return user

def load_user_by_id(user_id):
    """Возвращает объект User из users.json по id (или None)"""

    users = load_json(USERS_FILE)
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

def login(username, password):
    """Провреяет имя/пароль. При успешной валидации возвращает user_id"""
    
    if not isinstance(username, str) or not isinstance(password, str):
        raise ValueError("Пользователь не найден")

    users = load_json(USERS_FILE)
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
    from_usd = 1.0 if from_code == BASE_CURRENCY else None
    to_usd = 1.0 if to_code == BASE_CURRENCY else None
    if from_usd is None:
        key = f"{from_code}_{BASE_CURRENCY}"
        if key not in rates:
            raise ValueError(f"Курс {from_code}→{to_code} недоступен")
        from_usd = rates[key]["rate"]
    if to_usd is None:
        key = f"{to_code}_{BASE_CURRENCY}"
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

    portfolios = load_json(PORTFOLIOS_FILE)
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

    portfolios = load_json(PORTFOLIOS_FILE)
    if not isinstance(portfolios, list):
        portfolios = []

    wallets_data = {}
    for code, wallet in portfolio.wallets.items():
        wallets_data[code] = {"balance": wallet.balance}

    record = {"user_id": portfolio.user_id, "wallets": wallets_data}

    for i, existing in enumerate(portfolios):
        if existing.get("user_id") == portfolio.user_id:
            portfolios[i] = record
            break
    else:
        portfolios.append(record)

    save_json(PORTFOLIOS_FILE, portfolios)


def get_portfolio_info(user_id, base_currency=BASE_CURRENCY):
    """Возвращает данные портфеля для отображения"""

    base = validate_currency_code(base_currency)
    rates = get_rates()

    if base != {BASE_CURRENCY} and f"{base}_{BASE_CURRENCY}" not in rates and f"{BASE_CURRENCY}_{base}" not in rates:
        raise ValueError(f"Неизвестная базовая валюта '{base}'")

    portfolio = load_portfolio(user_id)

    rows = []
    total = 0.0
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
        total += value

    return {
        "user": portfolio.user,
        "base": base,
        "wallets": rows,
        "total": total,
    }


def buy(user_id, currency_code, amount):
    """Купить amount валюты currency_code (зачисление на кошелёк).
    USD не списывается. Если кошелька currency_code нет — создаёт.
    Для отчёта считает оценочную стоимость amount * rate в USD
    """

    validate_amount(amount)
    code = validate_currency_code(currency_code)
    if code == BASE_CURRENCY:
        raise ValueError(f"Нельзя купить {BASE_CURRENCY} за {BASE_CURRENCY}")

    rates = get_rates()
    try:
        rate = get_rate_value(code, BASE_CURRENCY, rates)
    except ValueError:
        raise ValueError(f"Не удалось получить курс для {code}→{BASE_CURRENCY}")

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


def sell(user_id, currency_code, amount):
    """Продать amount валюты currency_code (списание с кошелька).
    USD не начисляется. Для отчёта считает 
    оценочную выручку amount * rate в USD"""

    validate_amount(amount)
    code = validate_currency_code(currency_code)
    if code == BASE_CURRENCY:
        raise ValueError(f"Нельзя продать {BASE_CURRENCY} за {BASE_CURRENCY}")

    rates = get_rates()
    try:
        rate = get_rate_value(code, BASE_CURRENCY, rates)
    except ValueError:
        raise ValueError(f"Не удалось получить курс для {code}→{BASE_CURRENCY}")

    portfolio = load_portfolio(user_id)

    wallet = portfolio.get_wallet(code)
    if wallet is None:
        raise ValueError(
            f"У вас нет кошелька '{code}'. Добавьте валюту: "
            f"она создаётся автоматически при первой покупке."
        )

    if amount > wallet.balance:
        raise ValueError(
            f"Недостаточно средств: доступно {wallet.balance:.{BALANCE_DECIMALS}f} {code}, "
            f"требуется {amount:.{BALANCE_DECIMALS}f} {code}"
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

def get_rate_info(from_code, to_code):
    """Возвращает курс from_code → to_code и метку времени обновления.
    Поддерживает прямой ключ, обратный и кросс через USD"""

    from_code = validate_currency_code(from_code)
    to_code = validate_currency_code(to_code)
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
            from_usd = 1.0 if from_code == BASE_CURRENCY else rates[f"{from_code}_{BASE_CURRENCY}"]["rate"]
            to_usd = 1.0 if to_code == BASE_CURRENCY else rates[f"{to_code}_{BASE_CURRENCY}"]["rate"]
            rate = from_usd / to_usd

            stamps = []
            if from_code != BASE_CURRENCY:
                stamps.append(rates[f"{from_code}_{BASE_CURRENCY}"].get("updated_at"))
            if to_code != BASE_CURRENCY:
                stamps.append(rates[f"{to_code}_{BASE_CURRENCY}"].get("updated_at"))
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

