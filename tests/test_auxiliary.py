from dataclasses import replace
from decimal import Decimal as D

import pytest

from football_quant.application import demo
from football_quant.domain import Market
from football_quant.markets.pricing import price
from football_quant.models.counts import CountInputs, CountKind, count_model, negative_binomial
from football_quant.models.goals import score_matrix


@pytest.mark.parametrize(
    "kind,units,market",
    [
        (CountKind.CORNERS, "corners", Market.CORNER_TOTAL),
        (CountKind.CARDS, "yellow_cards", Market.CARD_TOTAL),
    ],
)
def test_independent_count_probability_ev(kind: CountKind, units: str, market: Market) -> None:
    rows = (1, 2, 2, 3, 4, 8, 9, 1)
    model = count_model(CountInputs(kind, rows, rows, rows, rows, units))
    assert sum(map(sum, model.scores.matrix)) == pytest.approx(1)
    assert model.home == pytest.approx(3.75)
    q = replace(
        demo().matches[0].candidates[0].quote, market=market, selection="over", line=D("7.25")
    )
    p = price(q, model.scores, 0.5)
    assert sum(p.states) == pytest.approx(1)
    assert float(p.ev) == pytest.approx(
        (p.states[0] + p.states[1] / 2) * 1.1 - p.states[3] / 2 - p.states[4]
    )
    with pytest.raises(ValueError, match="family mismatch"):
        price(q, score_matrix(1.6, 1.1), 0.5)


def test_nb_moments() -> None:
    dist = negative_binomial(5, 2)
    mu = sum(n * p for n, p in enumerate(dist))
    var = sum((n - mu) ** 2 * p for n, p in enumerate(dist))
    assert sum(dist) == pytest.approx(1)
    assert mu == pytest.approx(5, abs=1e-8)
    assert var == pytest.approx(17.5, abs=1e-6)


def test_count_missing_and_units_rejected() -> None:
    with pytest.raises(ValueError, match="至少8场"):
        CountInputs(CountKind.CORNERS, (1,), (1,), (1,), (1,), "corners")
    with pytest.raises(ValueError, match="口径"):
        CountInputs(CountKind.CARDS, (1,) * 8, (1,) * 8, (1,) * 8, (1,) * 8, "booking_points")
