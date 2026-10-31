import shlex
from functools import wraps

from valutatrade_hub.constants import (
    BALANCE_DECIMALS,
    MONEY_DECIMALS,
    RATES_FILE,
    SEPARATOR_LENGTH,
)
from valutatrade_hub.core import usecases
from valutatrade_hub.core.currencies import supported_codes
from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
)
from valutatrade_hub.core.utils import format_rate, format_timestamp
from valutatrade_hub.infra.database import DatabaseManager
from valutatrade_hub.infra.settings import SettingsLoader
from valutatrade_hub.parser_service.api_clients import (
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from valutatrade_hub.parser_service.config import ParserConfig
from valutatrade_hub.parser_service.storage import ParserStorage
from valutatrade_hub.parser_service.updater import RatesUpdater

_BASE_CURRENCY = SettingsLoader().get("default_base_currency")

def login_required(func):
    """Декоратор: выполнить команду только для залогиненного пользователя"""

    @wraps(func)
    def wrapper(self, args):
        if self._current_user_id is None:
            print("Сначала авторизуйтесь")
            return
        return func(self, args)
    return wrapper


class CLI:
    """Класс для описания консольного интерфейса"""

    def __init__(self):
        """Конструктор класса"""

        self._current_user_id = None
        self._current_username = None
        self._commands = {
            "register": self.cmd_register,
            "login": self.cmd_login,
            "logout": self.cmd_logout,
            "show-portfolio": self.cmd_show_portfolio,
            "buy": self.cmd_buy,
            "sell": self.cmd_sell,
            "get-rate": self.cmd_get_rate,
            "show-rates": self.cmd_show_rates,
            "update-rates": self.cmd_update_rates,
            "help": self.cmd_help,
        }

    # хелперы

    def _parse_args(self, args):
        """Разбирает аргументы вида --key value.
        Возвращает словарь {key: value} или None при ошибке формата.
        """

        result = {}
        i = 0
        while i < len(args):
            token = args[i]
            if not token.startswith("--"):
                return None
            key = token[2:]
            if i + 1 >= len(args):
                return None
            result[key] = args[i + 1]
            i += 2
        return result

    # команды

    def cmd_register(self, args):
        """Регистрация пользователя.
        Обработчик команды register --username X --password Y"""

        parsed = self._parse_args(args)
        if parsed is None:
            print("Ошибка: неверный формат аргументов")
            return
        if "username" not in parsed or "password" not in parsed:
            print("Ошибка: нужны --username и --password")
            return

        try:
            user = usecases.register_user(parsed["username"], parsed["password"])
        except ValueError as e:
            print(e)
            return

        print(f"Пользователь '{user.username}' зарегистрирован "
              f"(id={user.user_id}). Войдите: "
              f"login --username {user.username} --password ****")

    def cmd_login(self, args):
        """Авторизация в приложении.
        Обработчик команды login --username X --password Y"""

        if self._current_user_id is not None:
            print(f"Вы уже вошли как '{self._current_username}'. "
                  f"Сначала завершите текущую сессию")
            return

        parsed = self._parse_args(args)
        if parsed is None:
            print("Ошибка: неверный формат аргументов")
            return
        if "username" not in parsed or "password" not in parsed:
            print("Ошибка: нужны --username и --password")
            return

        try:
            user_id = usecases.login(parsed["username"], parsed["password"])
        except ValueError as e:
            print(e)
            return

        self._current_user_id = user_id
        self._current_username = parsed["username"]
        print(f"Вы вошли как '{parsed['username']}'")


    @login_required
    def cmd_logout(self, args):
        """Обработчик команды logout"""

        self._current_user_id = None
        self._current_username = None
        print("Вы вышли из системы")


    @login_required
    def cmd_show_portfolio(self, args):
        """Обработчик команды show-portfolio [--base X]
        Можно указывать в какой валюте выводить. По умолчанию USD
        """

        parsed = self._parse_args(args)
        if parsed is None:
            print("Ошибка: неверный формат аргументов")
            return

        base = parsed.get("base", _BASE_CURRENCY)

        try:
            info = usecases.get_portfolio_info(self._current_user_id, base)
        except CurrencyNotFoundError as e:
            print(e)
            print(f"Поддерживаемые валюты: {', '.join(supported_codes())}")
            return
        except ApiRequestError as e:
            print(e)
            print("Повторите попытку позже")
            return
        except ValueError as e:
            print(e)
            return

        user = info["user"]
        username = user.username if user else "?"
        print(f"Портфель пользователя '{username}' (база: {info['base']}):")

        if not info["wallets"]:
            print("Портфель пуст. Добавьте валюту через buy")
            return

        for row in info["wallets"]:
            print(f"- {row['currency_code']}: {row['balance']:.{BALANCE_DECIMALS}f}  "
                  f"→ {row['value']:.{MONEY_DECIMALS}f} {info['base']}")
        print("-" * SEPARATOR_LENGTH)
        print(f"ИТОГО: {info['total']:,.{MONEY_DECIMALS}f} {info['base']}")

    @login_required
    def cmd_buy(self, args):
        """Покупка валюты. 
        Обрабочик команды buy --currency X --amount Y"""

        parsed = self._parse_args(args)
        if parsed is None:
            print("Ошибка: неверный формат аргументов")
            return
        if "currency" not in parsed or "amount" not in parsed:
            print("Ошибка: нужны --currency и --amount")
            return

        try:
            amount = float(parsed["amount"])
        except ValueError:
            print("'amount' должен быть положительным числом")
            return

        try:
            result = usecases.buy(
                self._current_user_id, parsed["currency"], amount
            )
        except InsufficientFundsError as e:
            print(e)
            return
        except CurrencyNotFoundError as e:
            print(e)
            print(f"Поддерживаемые валюты: {', '.join(supported_codes())}")
            return
        except ApiRequestError as e:
            print(e)
            print("Повторите попытку позже")
            return
        except (ValueError, RuntimeError) as e:
            print(e)
            return

        code = result["currency_code"]
        print(f"Покупка выполнена: {result['amount']:.{BALANCE_DECIMALS}f} {code} "
              f"по курсу {format_rate(result['rate'])} {_BASE_CURRENCY}/{code}")
        print("Изменения в портфеле:")
        print(f"- {code}: было {result['balance_before']:.{BALANCE_DECIMALS}f} "
              f"→ стало {result['balance_after']:.{BALANCE_DECIMALS}f}")
        print(f"Оценочная стоимость покупки: "
              f"{result['cost_usd']:,.{MONEY_DECIMALS}f} {_BASE_CURRENCY}")

    @login_required
    def cmd_sell(self, args):
        """Продажа валюты. 
        Обрабочик команды sell --currency X --amount Y"""

        parsed = self._parse_args(args)
        if parsed is None:
            print("Ошибка: неверный формат аргументов")
            return
        if "currency" not in parsed or "amount" not in parsed:
            print("Ошибка: нужны --currency и --amount")
            return

        try:
            amount = float(parsed["amount"])
        except ValueError:
            print("'amount' должен быть положительным числом")
            return

        try:
            result = usecases.sell(
                self._current_user_id, parsed["currency"], amount
            )
        except InsufficientFundsError as e:
            print(e)
            return
        except CurrencyNotFoundError as e:
            print(e)
            print(f"Поддерживаемые валюты: {', '.join(supported_codes())}")
            return
        except ApiRequestError as e:
            print(e)
            print("Повторите попытку позже")
            return
        except (ValueError, RuntimeError) as e:
            print(e)
            return

        code = result["currency_code"]
        print(f"Продажа выполнена: {result['amount']:.{BALANCE_DECIMALS}f} {code} "
              f"по курсу {format_rate(result['rate'])} {_BASE_CURRENCY}/{code}")
        print("Изменения в портфеле:")
        print(f"- {code}: было {result['balance_before']:.{BALANCE_DECIMALS}f} "
              f"→ стало {result['balance_after']:.{BALANCE_DECIMALS}f}")
        print(f"Оценочная стоимость продажи: "
              f"{result['income_usd']:,.{MONEY_DECIMALS}f} {_BASE_CURRENCY}")

    @login_required
    def cmd_get_rate(self, args):
        """Вывод курса валют.
        Обработчик команды get-rate --from X --to Y"""

        parsed = self._parse_args(args)
        if parsed is None:
            print("Ошибка: неверный формат аргументов")
            return
        if "from" not in parsed or "to" not in parsed:
            print("Ошибка: нужны --from и --to")
            return

        try:
            info = usecases.get_rate_info(parsed["from"], parsed["to"])
        except CurrencyNotFoundError as e:
            print(e)
            print(f"Поддерживаемые валюты: {', '.join(supported_codes())}")
            return
        except ApiRequestError as e:
            print(e)
            print("Повторите попытку позже")
            return
        except ValueError as e:
            print(e)
            return

        rate_str = format_rate(info["rate"])
        updated_str = format_timestamp(info["updated_at"])
        print(f"Курс {info['from']}→{info['to']}: {rate_str} "
              f"(обновлено: {updated_str})")

        if info["reverse"] is not None:
            rev_str = format_rate(info["reverse"])
            rev_updated = format_timestamp(info["reverse_updated_at"])
            print(f"Обратный курс {info['to']}→{info['from']}: "
                  f"{rev_str} (обновлено: {rev_updated})")


    def cmd_update_rates(self, args):
        """Обработчик команды update-rates.
        Обновить курсы через Parser Service"""

        parsed = self._parse_args(args)
        if parsed is None:
            print("Ошибка: неверный формат аргументов")
            return

        config = ParserConfig()
        all_clients = [
            CoinGeckoClient(config),
            ExchangeRateApiClient(config),
        ]

        source_arg = parsed.get("source")
        if source_arg is not None:
            normalized = source_arg.strip().lower()
            aliases = {k.lower(): v for k, v in config.SOURCE_ALIASES.items()}
            if normalized not in aliases:
                print(f"Неизвестный источник: '{source_arg}'")
                print(f"Доступные: {', '.join(config.SOURCE_ALIASES.keys())}")
                return
            target = aliases[normalized]
            clients = [c for c in all_clients if c.SOURCE_NAME == target]
        else:
            clients = all_clients

        print("Начало обновления...")
        updater = RatesUpdater(clients=clients, storage=ParserStorage())

        try:
            result = updater.run_update()
        except ApiRequestError as e:
            print(e)
            return

        for source_name, count in result["per_source"].items():
            print(f"{source_name}: OK ({count})")
        for err in result["errors"]:
            print(f"Ошибка: {err}")

        if result["errors"]:
            print("Обновление завершено с ошибками. "
                  "Подробности в logs/parser.log")
        else:
            total = len(result["pairs"])
            ts = format_timestamp(result["last_refresh"])
            print(f"Записано {total} пар. Последнее обновление: {ts}")


    def cmd_show_rates(self, args):
        """Обработчик show-rates
        Синтаксис: [--currency X] [--top N] [--base X]"""

        parsed = self._parse_args(args)
        if parsed is None:
            print("Ошибка: неверный формат аргументов")
            return

        db = DatabaseManager()
        raw = db.read(RATES_FILE, {})
        if not isinstance(raw, dict):
            raw = {}
        pairs_raw = raw.get("pairs", {})
        if not isinstance(pairs_raw, dict):
            pairs_raw = {}
        last_refresh = raw.get("last_refresh")

        if not pairs_raw:
            print("Локальный кеш курсов пуст. "
                  "Выполните 'update-rates', чтобы загрузить данные.")
            return

        base = parsed.get("base", _BASE_CURRENCY).strip().upper()

        if base == _BASE_CURRENCY:
            base_rate = 1.0
        else:
            base_key = f"{base}_{_BASE_CURRENCY}"
            entry = pairs_raw.get(base_key)
            if not isinstance(entry, dict):
                print(f"Неизвестная базовая валюта '{base}'.")
                return
            base_rate = entry.get("rate")
            if not isinstance(base_rate, (int, float)) or base_rate <= 0:
                print(f"Неизвестная базовая валюта '{base}'.")
                return

        result = {}
        result[f"{_BASE_CURRENCY}_{base}"] = (
            1.0 if base == _BASE_CURRENCY else 1.0 / base_rate
        )
        for pair_key, entry in pairs_raw.items():
            if not isinstance(entry, dict):
                continue
            rate = entry.get("rate")
            if not isinstance(rate, (int, float)) or rate <= 0:
                continue
            parts = pair_key.split("_", 1)
            if len(parts) != 2:
                continue
            from_code = parts[0]
            if from_code == base:
                result[f"{from_code}_{base}"] = 1.0
            else:
                result[f"{from_code}_{base}"] = rate / base_rate

        currency = parsed.get("currency")
        if currency is not None:
            currency = currency.strip().upper()
            key = f"{currency}_{base}"
            if key not in result:
                print(f"Курс для '{currency}' не найден в кеше.")
                return
            result = {key: result[key]}

        top = None
        if "top" in parsed:
            try:
                top = int(parsed["top"])
            except (TypeError, ValueError):
                print("'--top' должен быть целым числом")
                return
            if top <= 0:
                print("'--top' должен быть положительным")
                return

        if top is not None:
            crypto_codes = set(ParserConfig().CRYPTO_CURRENCIES)
            crypto_items = [
                (k, v) for k, v in result.items()
                if k.split("_", 1)[0] in crypto_codes
            ]
            sorted_items = sorted(
                crypto_items, key=lambda kv: kv[1], reverse=True
            )[:top]
        else:
            sorted_items = sorted(result.items())

        if not sorted_items:
            print("Нет подходящих курсов.")
            return

        ts = format_timestamp(last_refresh)
        print(f"Курсы из кеша (обновлено: {ts}):")
        for pair, value in sorted_items:
            print(f"- {pair}: {format_rate(value)}")


    def cmd_help(self, args):
        """Обработать help."""
        print("Доступные команды:")
        print("  register --username <имя> --password <пароль>     — регистрация")
        print("  login --username <имя> --password <пароль>        — вход")
        print("  logout                                            — выход из системы")
        print("  show-portfolio [--base <код>]                     — портфель и итог")
        print("  buy --currency <код> --amount <число>             — покупка")
        print("  sell --currency <код> --amount <число>            — продажа")
        print("  get-rate --from <код> --to <код>                  — курс")
        print("  update-rates [--source <coingecko|exchangerate>]  — обновить курсы")
        print("  show-rates [--currency X] [--top N] [--base X]    — курсы из кеша")
        print("  help                                              — эта справка")
        print("  exit / quit                                       — выход из REPL")
            
    # диспетчеризация и repl

    def dispatch(self, args):
        """Выбрать обработчик по имени команды и вызвать его"""

        if not args:
            print("Нет команды")
            return
        command = args[0]
        rest = args[1:]
        handler = self._commands.get(command)
        if handler is None:
            print(f"Неизвестная команда: {command}")
            return
        handler(rest)

    def run(self):
        """Интерактивный режим: читает команды из консоли до ввода exit/quit"""

        print("ValutaTrade Hub. Введите команду "
        "(help - для получения списка доступных команд. exit/quit для выхода)")
        while True:
            try:
                line = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not line:
                continue
            if line in ("exit", "quit"):
                break
            try:
                parts = shlex.split(line)
            except ValueError:
                print("Ошибка: неверный формат аргументов")
                continue
            self.dispatch(parts)
