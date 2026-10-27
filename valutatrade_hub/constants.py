from pathlib import Path

# Корень проекта
BASE_DIR = Path(__file__).resolve().parent.parent

# Папка с JSON-хранилищами
DATA_DIR = BASE_DIR / "data"

# Пути к файлам данных
USERS_FILE = DATA_DIR / "users.json"
PORTFOLIOS_FILE = DATA_DIR / "portfolios.json"
RATES_FILE = DATA_DIR / "rates.json"

# Базовая валюта по умолчанию (для конвертации и отчётов)
DEFAULT_BASE_CURRENCY = "USD"