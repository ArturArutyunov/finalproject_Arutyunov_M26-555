# Имена файлов данных
USERS_FILE = "users.json"
PORTFOLIOS_FILE = "portfolios.json"
RATES_FILE = "rates.json"

# Базовая валюта
BASE_CURRENCY = "USD"

# Константы для ограничений
MIN_PASSWORD_LENGTH = 4
SALT_BYTES = 8
CURRENCY_CODE_MIN_LENGTH = 2
CURRENCY_CODE_MAX_LENGTH = 5

# Форматирование вывода
BALANCE_DECIMALS = 4
MONEY_DECIMALS = 2
SEPARATOR_LENGTH = 33
MARKET_CAP_DECIMALS = 2

# Форматирование курса
SMALL_RATE_THRESHOLD = 1
SMALL_RATE_DECIMALS = 8
LARGE_RATE_DECIMALS = 2

# Константы логирования по умолчанию
LOG_FILE_DEFAULT = "logs/actions.log"
LOG_ROTATION_DEFAULT = "time"
LOG_BACKUP_COUNT_DEFAULT = 7
LOG_FILE_SIZE_DEFAULT = 1048576

# остальное
RATES_TTL_DEFAULT = 300
JSON_INDENT = 2