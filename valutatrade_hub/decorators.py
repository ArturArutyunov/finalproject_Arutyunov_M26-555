import logging
from functools import wraps

from .constants import BALANCE_DECIMALS, MONEY_DECIMALS
from .core.utils import validate_currency_code

logger = logging.getLogger("valutatrade.actions")


def _build_info_fields(action, args, result, verbose, base):
    """Собрать поля INFO-записи по типу действия"""

    fields = {"action": action}

    if action in ("BUY", "SELL"):
        fields["user_id"] = args[0]
        fields["currency"] = f"{result['currency_code']!r}"
        fields["amount"] = f"{result['amount']:.{BALANCE_DECIMALS}f}"
        fields["rate"] = f"{result['rate']:.{MONEY_DECIMALS}f}"
        if base is not None:
            fields["base"] = f"{base!r}"
        if verbose:
            fields["balance_before"] = (
                f"{result['balance_before']:.{BALANCE_DECIMALS}f}"
            )
            fields["balance_after"] = (
                f"{result['balance_after']:.{BALANCE_DECIMALS}f}"
            )
    elif action == "REGISTER":
        fields["user_id"] = result.user_id
        fields["username"] = f"{args[0]!r}"
    elif action == "LOGIN":
        fields["user_id"] = result
        fields["username"] = f"{args[0]!r}"

    fields["result"] = "OK"
    return fields


def _format_line(fields):
    """Собрать строку key=value key=value ... для лога."""

    return " ".join(f"{key}={value}" for key, value in fields.items())


def log_action(action, verbose=False, base=None):
    """Декоратор логирования операции.
    action: строка — BUY / SELL / REGISTER / LOGIN.
    verbose: флаг - добавить balance_before/balance_after.
    base: базовая валюта (для buy/sell)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
            except Exception as e:
                error_fields = {
                    "action": action,
                    "user_id": args[0] if args else None,
                }
                if action in ("BUY", "SELL"):
                    try:
                        currency = validate_currency_code(args[1])
                    except ValueError:
                        currency = args[1]
                    error_fields["currency"] = f"{currency!r}"
                    error_fields["amount"] = (
                        f"{args[2]:.{BALANCE_DECIMALS}f}"
                    )
                elif action in ("REGISTER", "LOGIN"):
                    error_fields["username"] = f"{args[0]!r}"
                error_fields["result"] = "ERROR"
                error_fields["error_type"] = type(e).__name__
                error_fields["error"] = str(e)
                logger.error(_format_line(error_fields))
                raise

            info_fields = _build_info_fields(
                action, args, result, verbose, base
            )
            logger.info(_format_line(info_fields))
            return result
        return wrapper
    return decorator