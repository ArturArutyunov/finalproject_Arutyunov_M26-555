from pathlib import Path

# Корень проекта
BASE_DIR = Path(__file__).resolve().parent.parent

# Папка с JSON-хранилищами
DATA_DIR = BASE_DIR / "data"

# Пути к файлам данных
USERS_FILE = DATA_DIR / "users.json"
PORTFOLIOS_FILE = DATA_DIR / "portfolios.json"
RATES_FILE = DATA_DIR / "rates.json"

# Базовая валюта
BASE_CURRENCY = "USD"

# Константы для регистрации
MIN_PASSWORD_LENGTH = 4
SALT_BYTES = 8

# Форматирование вывода
BALANCE_DECIMALS = 4
MONEY_DECIMALS = 2
SEPARATOR_LENGTH = 33

# Форматирование курса
SMALL_RATE_THRESHOLD = 1
SMALL_RATE_DECIMALS = 8
LARGE_RATE_DECIMALS = 2