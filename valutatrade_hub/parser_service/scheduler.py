import logging
import time

import schedule

from ..constants import PARSER_UPDATE_INTERVAL_DEFAULT
from ..infra.settings import SettingsLoader
from ..logging_config import setup_logging, setup_parser_logging
from .api_clients import CoinGeckoClient, ExchangeRateApiClient
from .config import ParserConfig
from .storage import ParserStorage
from .updater import RatesUpdater

logger = logging.getLogger("valutatrade.parser")


def job():
    """Джоба для обновления"""

    try:
        config = ParserConfig()
        updater = RatesUpdater(
            clients=[CoinGeckoClient(config), ExchangeRateApiClient(config)],
            storage=ParserStorage(),
        )
        updater.run_update()
    except Exception as e:
        logger.error("Scheduled update failed: %s", e)


def run_scheduler():
    """Запустить периодическое обновление"""

    interval = SettingsLoader().get(
        "parser_update_interval_seconds", PARSER_UPDATE_INTERVAL_DEFAULT
    )

    schedule.every(interval).seconds.do(job)
    logger.info("Запущен планировщик парсера, интервал=%d секунд", interval)

    job()

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":

    setup_logging()
    setup_parser_logging()
    run_scheduler()