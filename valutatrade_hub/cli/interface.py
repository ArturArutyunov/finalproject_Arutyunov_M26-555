from functools import wraps

from valutatrade_hub.constants import DEFAULT_BASE_CURRENCY
from valutatrade_hub.core import usecases
from valutatrade_hub.core.utils import format_rate, format_timestamp


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
        self._commands = {
            "register": self.cmd_register,
            "login": self.cmd_login,
            "show-portfolio": self.cmd_show_portfolio,
            "buy": self.cmd_buy,
            "sell": self.cmd_sell,
            "get-rate": self.cmd_get_rate,
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
        print(f"Вы вошли как '{parsed['username']}'")

    @login_required
    def cmd_show_portfolio(self, args):
        """Обработчик команды show-portfolio [--base X]
        Можно указывать в какой валюте выводить. По умолчанию USD
        """

        parsed = self._parse_args(args)
        if parsed is None:
            print("Ошибка: неверный формат аргументов")
            return

        base = parsed.get("base", DEFAULT_BASE_CURRENCY)

        try:
            info = usecases.get_portfolio_info(self._current_user_id, base)
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
            print(f"- {row['currency_code']}: {row['balance']:.4f}  "
                  f"→ {row['value']:.2f} {info['base']}")
        print("--------------------------------------------------------")
        print(f"ИТОГО: {info['total']:,.2f} {info['base']}")

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
        except (ValueError, RuntimeError) as e:
            print(e)
            return

        code = result["currency_code"]
        print(f"Покупка выполнена: {result['amount']:.4f} {code} "
              f"по курсу {format_rate(result['rate'])} USD/{code}")
        print("Изменения в портфеле:")
        print(f"- {code}: было {result['balance_before']:.4f} "
              f"→ стало {result['balance_after']:.4f}")
        print(f"Оценочная стоимость покупки: "
              f"{result['cost_usd']:,.2f} USD")

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
        except (ValueError, RuntimeError) as e:
            print(e)
            return

        code = result["currency_code"]
        print(f"Продажа выполнена: {result['amount']:.4f} {code} "
              f"по курсу {format_rate(result['rate'])} USD/{code}")
        print("Изменения в портфеле:")
        print(f"- {code}: было {result['balance_before']:.4f} "
              f"→ стало {result['balance_after']:.4f}")
        print(f"Оценочная стоимость продажи: {result['income_usd']:,.2f} USD")

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

        print("ValutaTrade Hub. Введите команду (exit/quit для выхода)")
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
            parts = line.split()
            self.dispatch(parts)
