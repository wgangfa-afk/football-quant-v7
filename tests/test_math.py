from dataclasses import FrozenInstanceError
from datetime import datetime
from decimal import Decimal as D

import pytest

from football_quant.application import demo
from football_quant.domain import aware, number
from football_quant.markets.odds import OddsFormat, devig, to_decimal, to_hong_kong
from football_quant.markets.settlement import Settlement as S
from football_quant.markets.settlement import profit, settle, split_line
from football_quant.models.goals import score_matrix


@pytest.mark.parametrize("value", [True, float("nan"), float("inf"), "2"])
def test_reject_non_numeric(value: object) -> None:
    with pytest.raises(ValueError):
        number(value, "test")


@pytest.mark.parametrize(
    "format_,raw,expected",
    [
        (OddsFormat.EU, "1.8", "1.8"),
        (OddsFormat.HK, ".8", "1.8"),
        (OddsFormat.MY, "-.8", "2.25"),
        (OddsFormat.MY, ".8", "1.8"),
        (OddsFormat.ID, "-2", "1.5"),
        (OddsFormat.ID, "2", "3"),
    ],
)
def test_odds_conversion(format_: OddsFormat, raw: str, expected: str) -> None:
    assert to_decimal(D(raw), format_) == D(expected)
    assert to_hong_kong(D(expected)) == D(expected) - 1


def test_devig_complete() -> None:
    assert devig((D(2), D(2))) == (0.5, 0.5)
    assert sum(devig((D("2.1"), D("3.4"), D("3.6")))) == pytest.approx(1)


@pytest.mark.parametrize(
    "value,line,expected",
    [
        (1, "-1", S.PUSH),
        (0, "-.25", S.HALF_LOSS),
        (0, ".25", S.HALF_WIN),
        (1, "-.75", S.HALF_WIN),
        (1, "-1.25", S.HALF_LOSS),
        (0, "-.5", S.LOSS),
        (1, "-.5", S.WIN),
    ],
)
def test_asian_settlement(value: int, line: str, expected: S) -> None:
    assert settle(value, D(line)) is expected
    assert profit(expected, D(2)) == D(int(expected)) / 2


def test_invalid_quarter_line() -> None:
    with pytest.raises(ValueError):
        split_line(D(".1"))


@pytest.mark.parametrize("mean", [0, -1, True, float("nan"), float("inf")])
def test_lambda_validation(mean: float) -> None:
    with pytest.raises(ValueError):
        score_matrix(mean, 1)


def test_dc_probabilities_and_boundary() -> None:
    independent, dc = score_matrix(1.6, 1.1), score_matrix(1.6, 1.1, -0.08)
    assert sum(map(sum, dc.matrix)) == pytest.approx(1)
    assert sum(dc.result()) == pytest.approx(1)
    assert dc.omitted_mass < 2e-12
    assert dc.matrix[0][0] > independent.matrix[0][0]
    assert independent.btts() == pytest.approx(
        (1 - __import__("math").exp(-1.6)) * (1 - __import__("math").exp(-1.1))
    )
    with pytest.raises(ValueError, match="negative mass"):
        score_matrix(2, 2, 0.3)


def test_frozen_deterministic_report_and_negative_ev() -> None:
    report = demo()
    assert report == demo()
    with pytest.raises(FrozenInstanceError):
        report.mode = "live"
    negative = [c for c in report.matches[0].candidates if c.price.ev < 0]
    assert negative
    assert all(c.price.risk_ev < c.price.ev < 0 for c in negative)
    assert all(c.grade.value == "C" for c in negative)
    with pytest.raises(ValueError):
        aware(datetime(2030, 1, 1))
