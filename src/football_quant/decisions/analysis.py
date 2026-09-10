"""Per-match analysis joins verified evidence with pure football calculations."""

import json
from collections import defaultdict
from dataclasses import replace
from decimal import Decimal

from football_quant.decisions.rating import Assessment, recommend
from football_quant.domain import Candidate, Grade, MatchAnalysis, Quote, Status
from football_quant.evidence.research import Research, ResearchMatch
from football_quant.evidence.verification import freshness, reconcile, window_reason
from football_quant.markets.completeness import complete_probabilities, line_key
from football_quant.markets.pricing import price
from football_quant.models.goals import Scores, score_matrix
from football_quant.models.inputs import goal_inputs


def context(match: ResearchMatch, research: Research) -> tuple[tuple[str, ...], tuple[str, ...]]:
    conflicts, blockers = [], []
    for key in sorted({c.key for c in match.claims}):
        finding = reconcile(key, match.claims, research.evidence)
        if finding.status is Status.CONFLICT:
            message = f"{key}冲突：" + " / ".join(
                f"{c.value} [{c.evidence_id}]" for c in finding.assertions
            )
            conflicts.append(message)
            blockers.append(f"{key}关键证据冲突待解决")
    major = [c for c in match.claims if c.key == "major_change" and c.value != "none"]
    if major:
        blockers.append("已确认核心缺阵或大规模轮换，但缺少可核验影响模型；保留情景分析")
    outside = window_reason(match.fixture, research.started, research.deadline, research.generated)
    if outside:
        blockers.append(outside)
    return tuple(conflicts), tuple(blockers)


def groups(quotes: tuple[Quote, ...]) -> tuple[tuple[Quote, ...], ...]:
    result = defaultdict(list)
    for q in quotes:
        result[(q.market, q.bookmaker, q.rules, q.evidence_id, line_key(q))].append(q)
    return tuple(tuple(v) for v in result.values())


def rate_group(
    quotes: tuple[Quote, ...],
    scores: Scores | None,
    stability: float,
    match: ResearchMatch,
    research: Research,
    blockers: tuple[str, ...],
) -> tuple[Candidate, ...]:
    sources = {e.id: e for e in research.evidence}
    market_probabilities = complete_probabilities(quotes)
    candidates = []
    keys = {c.key for c in match.claims}
    quality = len(keys & {"personnel", "tactics", "schedule", "motivation"}) / 4
    source_count = len({sources[e].source_name for e in match.fixture.evidence_ids})
    for index, q in enumerate(quotes):
        missing = list(blockers)
        stale = freshness(sources[q.evidence_id], research.generated)
        if stale:
            missing.append(stale)
        if sources[q.evidence_id].validation_status is not Status.VERIFIED:
            missing.append("盘口来源未核验")
        if q.rules != "regular_time":
            missing.append("全场常规时间结算规则不明确")
        p = None
        if scores:
            mp = market_probabilities[index] if market_probabilities else None
            p = price(q, scores, mp, Decimal("0.03"))
        assessment = Assessment(
            (
                stability,
                0.5 + 0.5 * quality,
                min(1, source_count / 2),
                quality,
                0.5,
                float("personnel" in keys),
                float("tactics" in keys),
                float("schedule" in keys),
                0.5,
                0,
            ),
            False,
            False,
            tuple(missing),
            tuple(f"{c.key}：{c.value} [{c.evidence_id}]" for c in match.claims),
            ("V1参数未经实战校准，情景与价格可能不一致",),
            ("风险EV扣除3个百分点；无实证校准最高C",),
        )
        candidates.append(recommend(match.fixture.id, q, p, assessment))
    eligible = [c for c in candidates if c.grade is not Grade.PASS]
    if eligible:
        best = max(eligible, key=lambda c: (c.confidence, c.price.ev))
        candidates = [
            c
            if c is best or c.grade is Grade.PASS
            else replace(
                c, grade=Grade.PASS, reasons=c.reasons + ("同一完整市场已有综合评分更高方向",)
            )
            for c in candidates
        ]
    return tuple(candidates)


def analyze_match(match: ResearchMatch, research: Research) -> MatchAnalysis:
    conflicts, blockers = context(match, research)
    missing, notes = list(match.missing), list(match.notes)
    estimate, scores = None, None
    try:
        estimate = goal_inputs(json.loads(match.data), research.started)
        scores = score_matrix(estimate.home, estimate.away)
        notes.extend(estimate.notes)
        notes.append("未取得可核验ρ拟合，Dixon–Coles采用ρ=0，退化为独立Poisson。")
    except ValueError as exc:
        missing.append(str(exc))
    if not match.quotes:
        missing.append("没有可核验公开盘口")
    candidates = tuple(
        c
        for group in groups(match.quotes)
        for c in rate_group(
            group, scores, estimate.stability if estimate else 0, match, research, blockers
        )
    )
    return MatchAnalysis(
        match.fixture,
        candidates,
        tuple(notes),
        tuple(missing),
        conflicts,
        estimate.home if estimate else None,
        estimate.away if estimate else None,
        scores.common() if scores else (),
    )
