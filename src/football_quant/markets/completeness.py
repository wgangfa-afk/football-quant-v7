"""A de-vig group must be the same book, observation, rules and market line."""

from decimal import Decimal

from football_quant.domain import Market, Quote
from football_quant.markets.odds import devig


def expected_selections(quotes: tuple[Quote, ...]) -> set[str]:
    market = quotes[0].market
    if market is Market.RESULT:
        return {"home", "draw", "away"}
    if market is Market.BTTS:
        return {"yes", "no"}
    if market in (Market.HANDICAP, Market.CORNER_HANDICAP, Market.CARD_HANDICAP):
        return {"home", "away"}
    if market in (Market.TOTAL, Market.CORNER_TOTAL, Market.CARD_TOTAL):
        return {"over", "under"}
    tails = [q.selection for q in quotes if q.selection.endswith("+")]
    if len(tails) != 1 or not tails[0][:-1].isdigit():
        raise ValueError("exact-goal market needs one exhaustive tail bin")
    cutoff = int(tails[0][:-1])
    if not 1 <= cutoff <= 20:
        raise ValueError("invalid exact-goal tail")
    return {str(n) for n in range(cutoff)} | {tails[0]}


def line_key(quote: Quote) -> Decimal | None:
    if quote.market in (Market.HANDICAP, Market.CORNER_HANDICAP, Market.CARD_HANDICAP):
        return -quote.line if quote.selection == "away" and quote.line is not None else quote.line
    return quote.line


def complete_probabilities(quotes: tuple[Quote, ...]) -> tuple[float, ...] | None:
    if not quotes:
        return None
    keys = {(q.market, q.bookmaker, q.rules, q.evidence_id, line_key(q)) for q in quotes}
    if len(keys) != 1:
        return None
    # Missing exhaustive bins affect de-vig only, not an individual exact-goal EV.
    try:
        expected = expected_selections(quotes)
    except ValueError:
        return None
    if {q.selection for q in quotes} != expected or len(quotes) != len(expected):
        return None
    return devig(tuple(q.decimal_odds for q in quotes))
