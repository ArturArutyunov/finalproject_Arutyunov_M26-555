# ValutaTrade Hub

Консольная платформа для симуляции торговли фиатными и криптовалютами:
регистрация пользователей, виртуальные портфели, покупка/продажа валют
и просмотр актуальных курсов.

---

## Требования

- **Python 3.12+**

## Установка

```bash
# вариант с uv (рекомендуется)
uv sync
```

## Структура проекта
```
finalproject
├── data/
│ ├── users.json            # пользователи
│ ├── portfolios.json       # портфели и кошельки
│ ├── rates.json            # снимок курсов для Core
│ └── exchange_rates.json   # история замеров
├── valutatrade_hub/
│ ├── constants.py          # константы кода
│ ├── logging_config.py     # настройка логов
│ ├── decorators.py         # декораторы
│ ├── core/
│ │ ├── currencies.py       # Классы валют
│ │ ├── exceptions.py       # доменные исключения
│ │ ├── models.py           # User, Wallet, Portfolio
│ │ ├── usecases.py         # register/login/buy/sell/get_rate/...
│ │ └── utils.py            # курсы (TTL), хеш, валидаторы, формат
│ ├── infra/
│ │ ├── settings.py         # Singleton SettingsLoader
│ │ └── database.py         # Singleton DatabaseManager
│ ├── parser_service/
│ │ ├── config.py           # конфигурация API и параметров обновления
│ │ ├── api_clients.py      # работа с внешними API
│ │ ├── storage.py          # операции чтения/записи exchange_rates.json
│ │ ├── updater.py          # основной модуль обновления курсов
│ │ └── scheduler.py        # планировщик периодического обновления
│ └── cli/
│ └── interface.py          # CLI-команды
├── main.py
├── pyproject.toml
├── .env.example            # образец-пример с переменными окружения
├── README.md
└── .gitignore
```

## Запуск

```bash
python main.py
```

Появится приглашение:

`ValutaTrade Hub. Введите команду (exit/quit для выхода)`

Выход — `exit`, `quit` или Ctrl+C.

Перед первым запуском, если нет парсера, положите в `data/rates.json` пример курсов, иначе `buy`,
`sell` и `get-rate` будут сообщать «курс недоступен».

---
## Формат `rates.json`

Файл data/rates.json — объект с last_refresh (служебное) и pairs (курсы):

```json
{
  "pairs": {
    "BTC_USD": {"rate": 59337.21, "updated_at": "2026-10-31T00:00:00Z", "source": "CoinGecko"},
    "ETH_USD": {"rate": 3720.00, "updated_at": "2026-10-31T00:00:00Z", "source": "CoinGecko"},
    "SOL_USD": {"rate": 180.50, "updated_at": "2026-10-31T00:00:00Z", "source": "CoinGecko"},
    "EUR_USD": {"rate": 1.0786, "updated_at": "2026-10-31T00:00:00Z", "source": "ExchangeRate-API"},
    "GBP_USD": {"rate": 1.27, "updated_at": "2026-10-31T00:00:00Z", "source": "ExchangeRate-API"},
    "RUB_USD": {"rate": 0.01016, "updated_at": "2026-10-31T00:00:00Z", "source": "ExchangeRate-API"}
  },
  "last_refresh": "2026-10-31T00:00:00Z"
}
```

---
## Команды CLI

Общий формат аргументов: `--ключ значение` (через пробел).
Коды валют нормализуются (`usd` → `USD`).

**Требуют логина**: `logout`, `show-portfolio`, `buy`, `sell`, `get-rate`.

**Доступны без логина:** `register`, `login`, `update-rates`, `show-rates`, `help`.


### help
Вывести справку о доступных командах.


### register
Создать пользователя и пустой портфель.
```bash
register --username <имя> --password <пароль>
```
- `--username` — непустой, уникальный.
- `--password` — не короче 4 символов.

### login
Войти в систему.
```bash
login --username <имя> --password <пароль>
```

### logout
Выйти из системы.
```bash
logout
```

### show-portfolio
Показать все кошельки и итоговую стоимость.

```bash
show-portfolio [--base <код>]
```
- --`base` — базовая валюта конвертации (по умолчанию USD).

### buy
Купить валюту (зачислить на кошелёк). USD не списывается.

```bash
buy --currency <код> --amount <число>
```

- `--currency ` — код валюты
- `--amount` — количество, > 0
- Если кошелька нет — создаётся автоматически

### sell
Продать валюту (списать с кошелька). USD не начисляется.
```bash
sell --currency <код> --amount <число>
```
- `--currency ` — код валюты
- `--amount` — количество, > 0
- Кошелёк должен существовать

### get-rate
Курс одной валюты к другой (прямой и обратный).
```bash
get-rate --from <код> --to <код>
```

### show-rates

Показать актуальные курсы из локального кеша `data/rates.json`.

```bash
show-rates [--currency <код>] [--top <N>] [--base <код>]
```
- `--currency` — только указанная валюта.
- `--top` — N самых дорогих криптовалют (по курсу).
- `--base` — пересчёт всех курсов относительно указанной базы (через USD).

### update-rates

Запустить немедленное обновление курсов через Parser Service.

```bash
update-rates [--source <coingecko|exchangerate>]
```
Без `--source` — оба источника.

Требует `EXCHANGERATE_API_KEY` (в .env) для фиатных курсов.

Подробности шагов — в **logs/parser.log**.

## Логирование

Логи пишутся **только в файл** (консоль не используется), настраиваются
в `valutatrade_hub/logging_config.py` (`setup_logging()` вызывается в `main.py`).

- **Файлы:** `logs/actions.log` (Core, `log_file`) и `logs/parser.log` (Parser Service, `parser_log_file`).
- **Формат:** строковый, задаётся `log_format` (по умолчанию
  `%(asctime)s %(levelname)s %(name)s: %(message)s`).
- **Уровень:** `log_level` (`INFO` по умолчанию).
- **Ротация:** `log_rotation` = `time` (по дням, архивы
  `actions.log.YYYY-MM-DD`) или `size` (по размеру, `actions.log.1`, …).
  `log_backup_count` — сколько архивов хранить, `log_file_size` — размер
  файла для `size` (байт).

**Декоратор `@log_action`** (`valutatrade_hub/decorators.py`) оборачивает
`buy`, `sell`, `register_user`, `login`. Пишет:
- `INFO ... result=OK` — с полями `user_id`, `currency`, `amount`, `rate`,
  `base` (для buy/sell), `balance_before`/`balance_after` (`verbose=True`);
- `ERROR ... result=ERROR` — с `error_type`, `error_message`; исключение
  пробрасывается (пользователь видит ту же ошибку).


## Parser Service

Отдельный микросервис — собирает курсы с CoinGecko (крипта) и
ExchangeRate-API (фиат), пишет:
- `data/exchange_rates.json` — история всех замеров (дедуп по `id`);
- `data/rates.json` — снимок текущих курсов (Core читает его).

### API-ключ

ExchangeRate-API требует ключ. Создайте `.env` в корне проекта (по образцу `.env.example`):

```bash
EXCHANGERATE_API_KEY=your_key_here
```

### Запуск

```bash
# вручную, одноразово (из CLI Core)
> update-rates

# как микросервис (по таймеру)
python -m valutatrade_hub.parser_service.scheduler
```