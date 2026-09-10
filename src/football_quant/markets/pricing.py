"""Market pricing consumes probability distributions, never web content."""

from decimal import Decimal

from football_quant.domain import Market, Price, Quote, probability
from football_quant.markets.settlement import Settlement, profit, settle
from football_quant.models.goals import Scores


def outcome(quote: Quote, home: int, away: int) -> Settlement:
    if quote.market is Market.RESULT:
        if quote.selection not in ("home", "draw", "away"):
            raise ValueError("invalid 1X2 selection")
        actual = "home" if home > away else "away" if home < away else "draw"
        return Settlement.WIN if quote.selection == actual else Settlement.LOSS
    if quote.market is Market.BTTS:
        if quote.selection not in ("yes", "no"):
            raise ValueError("BTTS selection must be yes or no")
        won = (home > 0 and away > 0) == (quote.selection == "yes")
        return Settlement.WIN if won else Settlement.LOSS
    if quote.market is Market.GOALS:
        tail = quote.selection.endswith("+")
        raw = quote.selection[:-1] if tail else quote.selection
        if not raw.isdigit():
            raise ValueError("exact goals requires integer or tail bin")
        won = home + away >= int(raw) if tail else home + away == int(raw)
        return Settlement.WIN if won else Settlement.LOSS
    if quote.line is None:
        raise ValueError("Asian market requires line")
    if quote.market in (Market.HANDICAP, Market.CORNER_HANDICAP, Market.CARD_HANDICAP):
        if quote.selection not in ("home", "away"):
            raise ValueError("handicap selection must be home or away")
        difference = home - away if quote.selection == "home" else away - home
        return settle(difference, quote.line)
    if quote.market in (Market.TOTAL, Market.CORNER_TOTAL, Market.CARD_TOTAL):
        if quote.selection not in ("over", "under"):
            raise ValueError("total selection must be over or under")
        return (
            settle(home + away, -quote.line)
            if quote.selection == "over"
            else settle(-(home + away), quote.line)
        )
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
