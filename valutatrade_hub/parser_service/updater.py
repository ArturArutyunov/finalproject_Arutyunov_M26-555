import logging
from datetime import datetime, timezone

from ..core.exceptions import ApiRequestError

logger = logging.getLogger("valutatrade.parser")

def _now_iso():
    """Текущее UTC-время в формате ISO с таймзоной"""

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _make_id(from_code, to_code, timestamp):
    """ID записи истории: FROM_TO_ISO"""

    return f"{from_code}_{to_code}_{timestamp}"


class RatesUpdater:
    """Класс для обновления курсов"""

    def __init__(self, clients, storage):
        self.clients = clients
        self.storage = storage

    def run_update(self):
        """Опросить клиентов, сохранить историю и snapshot"""

        now = _now_iso()
        all_pairs = {}
        sources = {}
        per_source = {}
        errors = []

        logger.info("Update started at %s", now)

        for client in self.clients:
            source_name = getattr(client, "SOURCE_NAME", type(client).__name__)
            try:
                rates = client.fetch_rates()
            except Exception as e:
                errors.append(f"{source_name}: {e}")
                logger.error(f"{source_name} failed: {e}")
                continue

            if not rates:
                logger.warning("%s: пустой ответ", source_name)
                continue

            all_pairs.update(rates)
            for pair in rates:
                sources[pair] = source_name
            logger.info("%s OK: %d pairs", source_name, len(rates))
            per_source[source_name] = len(rates)

        if not all_pairs:
            reason = "; ".join(errors) or "пустой ответ от всех клиентов"
            raise ApiRequestError(f"Не удалось получить курсы: {reason}")

        for pair, rate in all_pairs.items():
            from_code, to_code = pair.split("_", 1)
            entry = {
                "id": _make_id(from_code, to_code, now),
                "from_currency": from_code,
                "to_currency": to_code,
                "rate": rate,
                "timestamp": now,
                "source": sources[pair],
            }
            self.storage.append_history(entry)

        snapshot_pairs = {
            pair: {"rate": rate, "updated_at": now, "source": sources[pair]}
            for pair, rate in all_pairs.items()
        }
        self.storage.update_snapshot(snapshot_pairs, now)

        logger.info(
            "Update finished: %d pairs, last_refresh=%s",
            len(all_pairs), now,
        )
        return {
            "pairs": all_pairs,
            "per_source": per_source,
            "errors": errors,
            "last_refresh": now,
        }