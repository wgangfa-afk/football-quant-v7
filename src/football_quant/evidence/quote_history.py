"""Earlier observations stay visible but cannot become current recommendations."""

from datetime import datetime

from football_quant.domain import Evidence, Quote


def quote_key(quote: Quote) -> tuple[object, ...]:
    return quote.market, quote.selection, quote.line, quote.bookmaker, quote.rules


def historical_quotes(
    quotes: tuple[Quote, ...], sources: tuple[Evidence, ...]
) -> tuple[frozenset[Quote], tuple[str, ...]]:
    by_id = {e.id: e for e in sources}
    observations: dict[tuple[object, ...], list[tuple[datetime, Quote]]] = {}
    for q in quotes:
        source = by_id[q.evidence_id]
        if source.observed_at_utc is not None:
            observations.setdefault(quote_key(q), []).append((source.observed_at_utc, q))
    old, notes = set(), []
    for records in observations.values():
        records.sort(key=lambda pair: pair[0])
        first, last = records[0], records[-1]
        if first[0] == last[0]:
            continue
        old.update(q for at, q in records if at < last[0])
        q = last[1]
        notes.append(
            f"{q.bookmaker} {q.market.value} {q.selection} {q.line}：最早可见欧赔"
            f"{first[1].decimal_odds}（{first[0].isoformat()}）至"
            f"{q.decimal_odds}（{last[0].isoformat()}）。最早可见值不等于已核验初盘。"
        )
    return frozenset(old), tuple(notes)
