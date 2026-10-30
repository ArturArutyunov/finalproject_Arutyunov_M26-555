# ValutaTrade Hub

Консольная платформа для симуляции торговли фиатными и криптовалютами:
регистрация пользователей, виртуальные портфели, покупка/продажа валют
и просмотр актуальных курсов.

---

## Требования

- **Python 3.12+**

---

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

Файл data/rates.json — объект с meta (служебное) и data (курсы):

```json
{
  "meta": {
    "source": "ParserService",
    "last_refresh": "2026-10-25T10:35:00"
  },
  "data": {
    "BTC_USD": {
      "rate": 80607.61,
      "updated_at": "2026-10-25T10:29:42"
    },
    "ETH_USD": {
      "rate": 2336.00,
      "updated_at": "2026-10-25T10:35:00"
    },
    "EUR_USD": {
      "rate": 1.1203,
      "updated_at": "2026-10-25T10:30:00"
    },
    "RUB_USD": {
      "rate": 0.0124,
      "updated_at": "2026-10-25T10:31:12"
    }
  }
}
```

---
## Команды CLI

Общий формат аргументов: `--ключ значение` (через пробел).
Коды валют нормализуются (`usd` → `USD`).
Все команды, кроме `register` и `login`, требуют активного сеанса —
иначе выводится `Сначала выполните login`.


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
Показать все кошельки и итоговую стоимость
```bash
show-portfolio
```

### buy
Купить валюту (зачислить на кошелёк). USD не списывается.
```bash
buy --currency <код> --amount <число>
```
- `--currency ` — код валюты
- `--password` — количество, > 0
- Если кошелька нет — создаётся автоматически

### sell
Продать валюту (списать с кошелька). USD не начисляется.
```bash
sell --currency <код> --amount <число>
```
- `--currency ` — код валюты
- `--password` — количество, > 0
- Кошелёк должен существовать

### get-rate
Курс одной валюты к другой (прямой и обратный).
```bash
get-rate --from <код> --to <код>
```

## Логирование

Логи пишутся **только в файл** (консоль не используется), настраиваются
в `valutatrade_hub/logging_config.py` (`setup_logging()` вызывается в `main.py`).

- **Файл:** `logs/actions.log` (ключ `log_file`).
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