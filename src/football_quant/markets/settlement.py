"""Full/half win, push, half/full loss from individual outcomes."""

from decimal import Decimal
from enum import IntEnum

from football_quant.domain import number


class Settlement(IntEnum):
    LOSS = -2
    HALF_LOSS = -1
    PUSH = 0
    HALF_WIN = 1
    WIN = 2


def split_line(line: Decimal) -> tuple[Decimal, Decimal]:
    number(line, "line")
    if line * 4 != (line * 4).to_integral_value():
        raise ValueError("line must be an exact quarter increment")
    if line * 2 == (line * 2).to_integral_value():
        return line, line
    return line - Decimal("0.25"), line + Decimal("0.25")


def settle(value: int, line: Decimal) -> Settlement:
    number(value, "count")
    if not isinstance(value, int):
        raise ValueError("integer count required")
    legs = split_line(line)
    result = sum((value + leg > 0) - (value + leg < 0) for leg in legs)
    return Settlement(result)


def profit(state: Settlement, odds: Decimal) -> Decimal:
    if number(odds, "odds") <= 1:
        raise ValueError("decimal odds must exceed 1")
    if state > 0:
        return (odds - 1) * Decimal(int(state)) / 2
    return Decimal(int(state)) / 2
