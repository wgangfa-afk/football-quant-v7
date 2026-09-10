"""Market pricing consumes probability distributions, never web content."""

from decimal import Decimal

from football_quant.domain import Market, Price, Quote, probability
from football_quant.markets.settlement import Settlement, profit, settle
from football_quant.models.goals import Scores


def outcome(quote: Quote, home: int, away: int) -> Settlement:
    if quote.market is Market.RESULT:
        actual = "home" if home > away else "away" if home < away else "draw"
        return Settlement.WIN if quote.selection == actual else Settlement.LOSS
    if quote.line is None:
        raise ValueError("Asian market requires line")
    if quote.market is Market.HANDICAP:
        if quote.selection not in ("home", "away"):
            raise ValueError("handicap selection must be home or away")
        difference = home - away if quote.selection == "home" else away - home
        return settle(difference, quote.line)
    raise ValueError("unsupported market")


def price(
    quote: Quote,
    scores: Scores,
    market_probability: float | None,
    penalty: Decimal = Decimal("0.03"),
) -> Price:
    probability(penalty, "risk penalty")
    if market_probability is not None:
        probability(market_probability)
    masses = {state: 0.0 for state in Settlement}
    for i, row in enumerate(scores.matrix):
        for j, p in enumerate(row):
            masses[outcome(quote, i, j)] += p
    win = masses[Settlement.WIN] + masses[Settlement.HALF_WIN] / 2
    loss = masses[Settlement.LOSS] + masses[Settlement.HALF_LOSS] / 2
    effective = win / (win + loss) if win + loss else 0
    ev = sum(
        (Decimal(str(p)) * profit(s, quote.decimal_odds) for s, p in masses.items()), Decimal(0)
    )
    fair = 1 + Decimal(str(loss)) / Decimal(str(win)) if win else None
    return Price(
        effective,
        float(1 / quote.decimal_odds),
        market_probability,
        fair,
        quote.decimal_odds,
        ev,
        ev - penalty,
        tuple(masses[s] for s in reversed(Settlement)),
    )
