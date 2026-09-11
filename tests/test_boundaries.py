from dataclasses import replace
from decimal import Decimal as D

import pytest

from football_quant.application import demo
from football_quant.decisions.rating import Assessment, recommend
from football_quant.domain import Grade, Market
from football_quant.markets.odds import OddsFormat, to_decimal
from football_quant.markets.pricing import outcome
from football_quant.markets.settlement import Settlement as S
from football_quant.models.goals import Scores, score_matrix


@pytest.mark.parametrize(
    "format_,value",
    [
        (OddsFormat.EU, "1"),
        (OddsFormat.HK, "0"),
        (OddsFormat.MY, "1.2"),
        (OddsFormat.MY, "0"),
        (OddsFormat.ID, ".5"),
        (OddsFormat.ID, "0"),
        (OddsFormat.EU, "NaN"),
        (OddsFormat.HK, "Infinity"),
    ],
)
def test_invalid_odds_boundaries(format_: OddsFormat, value: str) -> None:
    with pytest.raises(ValueError):
        to_decimal(D(value), format_)


@pytest.mark.parametrize(
    "quality,grade",
    [(1, Grade.S), (0.9, Grade.A), (0.75, Grade.B), (0.6, Grade.C), (0.1, Grade.PASS)],
)
def test_grade_thresholds_with_negative_ev(quality: float, grade: Grade) -> None:
    candidate = demo().matches[0].candidates[1]
    p = replace(candidate.price, ev=D("-.01"), risk_ev=D("-.04"))
    assessment = Assessment((quality,) * 10, True, False, (), (), (), ())
    result = recommend("test-match", candidate.quote, p, assessment)
    assert result.grade is grade
    assert result.price.ev == D("-.01")
    assert result.price.risk_ev == D("-.04")


@pytest.mark.parametrize("market", [Market.CORNER_HANDICAP, Market.CARD_HANDICAP])
def test_auxiliary_handicap_quarters(market: Market) -> None:
    quote = replace(demo().matches[0].candidates[-1].quote, market=market, line=D("-1.25"))
    assert outcome(quote, 5, 4) is S.HALF_LOSS
    assert outcome(replace(quote, line=D("-1")), 5, 4) is S.PUSH


def test_distribution_validation_and_dc_extreme_boundary() -> None:
    with pytest.raises(ValueError):
        Scores(((float("nan"),),), 0)
    with pytest.raises(ValueError):
        Scores(((0.5,),), 0)
    edge = score_matrix(1, 1, 1)
    assert edge.matrix[0][0] == 0
    assert edge.matrix[1][1] == 0
    assert sum(map(sum, edge.matrix)) == pytest.approx(1)
