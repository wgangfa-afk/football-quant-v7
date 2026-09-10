from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D

import pytest

from football_quant.application import demo
from football_quant.domain import Market
from football_quant.markets.completeness import complete_probabilities
from football_quant.markets.pricing import outcome, price
from football_quant.markets.settlement import Settlement as S
from football_quant.models.goals import score_matrix
from football_quant.models.strength import History, estimate


@pytest.mark.parametrize(
    "market,selection,line,home,away,expected",
    [
        (Market.TOTAL, "over", "2", 1, 1, S.PUSH),
        (Market.TOTAL, "under", "2.25", 1, 1, S.HALF_WIN),
        (Market.TOTAL, "over", "2.25", 1, 1, S.HALF_LOSS),
        (Market.TOTAL, "under", "2.75", 2, 1, S.HALF_LOSS),
        (Market.BTTS, "yes", None, 1, 1, S.WIN),
        (Market.BTTS, "no", None, 1, 0, S.WIN),
        (Market.GOALS, "7+", None, 5, 3, S.WIN),
        (Market.GOALS, "2", None, 1, 1, S.WIN),
    ],
)
def test_all_main_settlements(
    market: Market, selection: str, line: str | None, home: int, away: int, expected: S
) -> None:
    q = replace(
        demo().matches[0].candidates[0].quote,
        market=market,
        selection=selection,
        line=D(line) if line else None,
    )
    assert outcome(q, home, away) is expected


def test_asian_ev_matches_enumerated_half_loss_draw() -> None:
    q = demo().matches[0].candidates[-1].quote
    scores = score_matrix(1.6, 1.1)
    p = price(q, scores, 0.5)
    h, d, a = scores.result()
    expected = h * 0.92 - d * 0.5 - a
    assert float(p.ev) == pytest.approx(expected)
    assert float(p.fair_odds) == pytest.approx(1 + (a + d / 2) / h)


def test_incomplete_and_mismatched_market() -> None:
    quotes = tuple(c.quote for c in demo().matches[0].candidates[:3])
    assert sum(complete_probabilities(quotes)) == pytest.approx(1)
    assert complete_probabilities(quotes[:2]) is None
    assert (
        complete_probabilities((quotes[0], quotes[1], replace(quotes[2], bookmaker="other")))
        is None
    )


def test_strength_no_fabricated_lambda_and_time_decay() -> None:
    at = demo().started
    rows = tuple(
        History(at - timedelta(days=7 * i), 2, 1, 1, 1, None, None, "e") for i in range(1, 9)
    )
    with pytest.raises(ValueError, match="至少8场"):
        estimate(rows[:3], rows, at, 1.5, 1.2, True)
    with pytest.raises(ValueError, match="跨联赛"):
        estimate(rows, rows, at, 1.5, 1.2, False)
    result = estimate(rows, rows, at, 1.5, 1.2, True)
    assert result.home == pytest.approx(2 / 1.5)
    assert result.away == pytest.approx(2 / 1.2)
    assert result.stability == pytest.approx(1)
