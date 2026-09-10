"""Pure odds conversions. Decimal odds are the sole calculation format."""

from decimal import Decimal
from enum import StrEnum

from football_quant.domain import number


class OddsFormat(StrEnum):
    EU = "EU"
    HK = "HK"
    MY = "MY"
    ID = "ID"


def to_decimal(value: Decimal, format_: OddsFormat) -> Decimal:
    number(value, "odds")
    if format_ is OddsFormat.EU and value > 1:
        return value
    if format_ is OddsFormat.HK and value > 0:
        return 1 + value
    if format_ is OddsFormat.MY and 0 < abs(value) <= 1:
        return 1 + value if value > 0 else 1 + 1 / abs(value)
    if format_ is OddsFormat.ID and abs(value) >= 1:
        return 1 + value if value > 0 else 1 + 1 / abs(value)
    raise ValueError("invalid odds or odds format")


def to_hong_kong(value: Decimal) -> Decimal:
    return to_decimal(value, OddsFormat.EU) - 1


def devig(odds: tuple[Decimal, ...]) -> tuple[float, ...]:
    if len(odds) < 2:
        raise ValueError("complete market requires at least two outcomes")
    implied = tuple(1 / to_decimal(d, OddsFormat.EU) for d in odds)
    total = sum(implied)
    return tuple(float(p / total) for p in implied)
