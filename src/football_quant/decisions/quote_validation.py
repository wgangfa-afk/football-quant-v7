"""Per-quote safety gates; unrelated markets never share these blockers."""

from decimal import Decimal, InvalidOperation
from typing import Any

from football_quant.domain import Market, Quote, Status
from football_quant.evidence.research import Research
from football_quant.evidence.verification import freshness
from football_quant.markets.odds import OddsFormat, to_decimal
from football_quant.markets.pricing import outcome


def check_model_evidence(data: Any, research: Research) -> None:
    if isinstance(data, dict):
        if "evidence_id" in data:
            sources = {e.id: e for e in research.evidence}
            source = sources.get(data["evidence_id"])
            if source is None or source.validation_status is not Status.VERIFIED:
                raise ValueError("模型输入来源未核验：" + str(data["evidence_id"]))
        for value in data.values():
            check_model_evidence(value, research)
    elif isinstance(data, list):
        for value in data:
            check_model_evidence(value, research)


def quote_key(q: Quote, research: Research) -> tuple[object, ...]:
    source = next(e for e in research.evidence if e.id == q.evidence_id)
    return q.bookmaker, q.market, q.selection, q.line, q.rules, source.observed_at_utc


def quote_blockers(q: Quote, all_quotes: tuple[Quote, ...], research: Research) -> tuple[str, ...]:
    source = next(e for e in research.evidence if e.id == q.evidence_id)
    reasons = []
    stale = freshness(source, research.generated)
    if stale:
        reasons.append(stale)
    if source.validation_status is not Status.VERIFIED:
        reasons.append("盘口来源未核验")
    rule = "regular_time"
    if q.market in (Market.CORNER_TOTAL, Market.CORNER_HANDICAP):
        rule = "regular_time_corners"
    elif q.market in (Market.CARD_TOTAL, Market.CARD_HANDICAP):
        rule = "regular_time_yellow_cards"
    if q.rules != rule:
        reasons.append("全场常规时间结算规则不明确")
    try:
        converted = to_decimal(Decimal(q.original_value), OddsFormat(q.original_format))
        if converted != q.decimal_odds:
            reasons.append("原始赔率与标准化赔率不一致")
        outcome(q, 0, 0)
    except (ValueError, InvalidOperation) as exc:
        reasons.append(f"赔率格式、盘口或结算不支持：{exc}")
    values = {
        p.decimal_odds for p in all_quotes if quote_key(p, research) == quote_key(q, research)
    }
    if len(values) > 1:
        reasons.append("同一盘口观察时间报价冲突：" + " / ".join(map(str, sorted(values))))
    return tuple(reasons)
