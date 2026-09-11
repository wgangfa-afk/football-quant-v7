"""Per-match analysis joins verified evidence with pure football calculations."""

import json
from collections import defaultdict
from dataclasses import replace
from decimal import Decimal

from football_quant.decisions.quote_validation import check_model_evidence, quote_blockers
from football_quant.decisions.rating import Assessment, recommend
from football_quant.domain import (
    Candidate,
    Capability,
    Decision,
    Grade,
    Market,
    MatchAnalysis,
    Quote,
    Status,
)
from football_quant.evidence.quote_history import historical_quotes
from football_quant.evidence.research import Research, ResearchMatch
from football_quant.evidence.verification import reconcile, window_reason
from football_quant.markets.completeness import complete_probabilities, line_key
from football_quant.markets.pricing import price
from football_quant.models.auxiliary import auxiliary_inputs
from football_quant.models.counts import CountKind
from football_quant.models.goals import Scores, score_matrix
from football_quant.models.inputs import goal_inputs, missing_goal_fields

CLAIM_LABELS = {
    "personnel": "人员",
    "tactics": "战术",
    "schedule": "赛程",
    "motivation": "战意",
    "referee": "裁判",
    "major_change": "重大人员变化",
}
MAJOR_CHANGE_BLOCKER = "已确认核心缺阵或大规模轮换，但缺少可核验影响模型；保留情景分析"


def context(
    match: ResearchMatch, research: Research, family: str = "goals"
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    conflicts, blockers = [], []
    sources = {e.id: e for e in research.evidence}
    claims = list(match.claims)
    for key in sorted({c.key for c in claims}):
        if (key == "referee" or key.startswith("cards:")) and family != "cards":
            continue
        if key.startswith("corners:") and family != "corners":
            continue
        finding = reconcile(key, tuple(claims), research.evidence)
        if finding.status is Status.CONFLICT:
            message = f"{key}冲突：" + " / ".join(
                f"{c.value} [{c.evidence_id}]" for c in finding.assertions
            )
            conflicts.append(message)
            blockers.append(f"{key}关键证据冲突待解决")
    major = [c for c in match.claims if c.key == "major_change" and c.value != "none"]
    if major:
        blockers.append(MAJOR_CHANGE_BLOCKER)
    outside = window_reason(match.fixture, research.started, research.deadline, research.generated)
    if outside:
        blockers.append(outside)
    if any(sources[e].validation_status is not Status.VERIFIED for e in match.fixture.evidence_ids):
        blockers.append("赛程证据未核验")
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
    auxiliary = quotes[0].market in (
        Market.CORNER_TOTAL,
        Market.CORNER_HANDICAP,
        Market.CARD_TOTAL,
        Market.CARD_HANDICAP,
    )
    sources = {e.id: e for e in research.evidence}
    validations = tuple(quote_blockers(q, match.quotes, research) for q in quotes)
    market_probabilities = complete_probabilities(quotes) if not any(validations) else None
    old_quotes, _ = historical_quotes(match.quotes, research.evidence)
    candidates = []
    keys = {c.key for c in match.claims}
    quality = len(keys & {"personnel", "tactics", "schedule", "motivation"}) / 4
    source_count = len({sources[e].source_name for e in match.fixture.evidence_ids})
    for index, q in enumerate(quotes):
        missing = list(blockers)
        if q in old_quotes:
            missing.append("历史报价仅用于盘口变化，不能作为当前方向")
        missing.extend(validations[index])
        p = None
        if scores and not missing:
            mp = market_probabilities[index] if market_probabilities else None
            p = price(q, scores, mp, Decimal("0.03"))
        assessment = make_assessment(
            stability,
            quality,
            source_count,
            keys,
            scores,
            market_probabilities is not None,
            auxiliary,
            missing,
            match,
        )
        candidate = recommend(match.fixture.id, q, p, assessment)
        if p is None:
            candidate = replace(candidate, missing_fields=candidate.missing_fields + tuple(missing))
        if p is None and scores is not None:
            candidate = replace(
                candidate,
                capability=Capability.PARTIAL,
                missing_fields=tuple(missing),
                data_status=Status.CONFLICT
                if any("冲突" in r for r in missing)
                else Status.UNCERTAIN,
            )
        candidates.append(candidate)
    eligible = [c for c in candidates if c.grade is not Grade.PASS]
    if eligible:
        best = max(eligible, key=lambda c: (c.confidence, c.price.ev))
        candidates = [
            c
            if c is best or c.grade is Grade.PASS
            else replace(
                c,
                grade=Grade.PASS,
                decision=Decision.NOT_SELECTED,
                reasons=c.reasons + ("同一市场已有综合评分更高方向",),
            )
            for c in candidates
        ]
    return tuple(candidates)


def analyze_match(match: ResearchMatch, research: Research) -> MatchAnalysis:
    conflicts, blockers = context(match, research)
    missing, notes = list(match.missing), list(match.notes)
    _, movement = historical_quotes(match.quotes, research.evidence)
    notes.extend(movement)
    estimate, scores = None, None
    data = json.loads(match.data)
    if data.get("home") and any(
        r.get("xg_for") is None for r in data["home"] + data.get("away", [])
    ):
        missing.append("历史xG/xGA不完整，进球模型使用可取得的进球统计")
    try:
        if blockers:
            raise ValueError("关键事实未通过核验，暂不计算模型：" + "；".join(blockers))
        check_model_evidence(
            {k: data[k] for k in ("baseline", "home", "away") if k in data}, research
        )
        estimate = goal_inputs(json.loads(match.data), research.started)
        scores = score_matrix(estimate.home, estimate.away)
        notes.extend(estimate.notes)
        notes.append("未取得可核验ρ拟合，Dixon–Coles采用ρ=0，退化为独立Poisson。")
    except ValueError as exc:
        missing.append(str(exc))
    if not match.quotes:
        missing.append("没有可核验公开盘口")
    candidates = []
    data = json.loads(match.data)
    for group in groups(match.quotes):
        distribution, stability = scores, estimate.stability if estimate else 0
        kind = None
        if group[0].market in (Market.CORNER_TOTAL, Market.CORNER_HANDICAP):
            kind = CountKind.CORNERS
        elif group[0].market in (Market.CARD_TOTAL, Market.CARD_HANDICAP):
            kind = CountKind.CARDS
        if kind is not None:
            distribution, stability = None, 0
            try:
                check_model_evidence(data.get(kind.value), research)
                aux = auxiliary_inputs(data, kind)
                distribution, stability = aux.scores, 0.5
                notes.extend(n for n in aux.notes if n not in notes)
                if kind is CountKind.CARDS and not any(c.key == "referee" for c in match.claims):
                    missing.append("缺少裁判历史，罚牌仅为低置信方向")
            except ValueError as exc:
                missing.append(str(exc))
        group_blockers = blockers
        if kind is not None:
            aux_conflicts, group_blockers = context(match, research, kind.value)
            conflicts = tuple(dict.fromkeys(conflicts + aux_conflicts))
        candidates.extend(
            rate_group(group, distribution, stability, match, research, group_blockers)
        )
    qualitative = match.qualitative
    sources = {e.id: e for e in research.evidence}
    if qualitative and (
        any(r != MAJOR_CHANGE_BLOCKER for r in blockers)
        or any(
            e not in sources or sources[e].validation_status is not Status.VERIFIED
            for e in qualitative.evidence_ids
        )
    ):
        missing.append("定性方向证据未通过核验，保留缺失说明而不输出方向")
        qualitative = None
    capability = Capability.NONE
    if scores or any(c.price for c in candidates):
        capability = Capability.PARTIAL
        if candidates and all(c.capability is Capability.FULL for c in candidates):
            capability = Capability.FULL
    elif qualitative or (match.claims and not blockers):
        capability = Capability.QUALITATIVE
    notes.extend(
        f"{CLAIM_LABELS.get(c.key, c.key)}：{c.value} [{c.evidence_id}]" for c in match.claims
    )
    quote_conflicts = tuple(
        dict.fromkeys(reason for c in candidates for reason in c.reasons if "报价冲突" in reason)
    )
    return MatchAnalysis(
        match.fixture,
        tuple(candidates),
        tuple(notes),
        tuple(missing),
        conflicts + quote_conflicts,
        estimate.home if estimate else None,
        estimate.away if estimate else None,
        scores.common() if scores else (),
        capability,
        Status.CONFLICT
        if conflicts or quote_conflicts
        else Status.MISSING
        if missing or any(c.missing_fields for c in candidates)
        else Status.VERIFIED,
        (
            "进失球/xG混合基线（未实证校准）"
            if any(
                r.get("xg_for") is not None for side in ("home", "away") for r in data.get(side, [])
            )
            else "进失球基线（未实证校准）"
        )
        if estimate
        else None,
        qualitative,
        missing_goal_fields(data) + (("quotes",) if not match.quotes else ()),
    )


def make_assessment(
    stability: float,
    quality: float,
    source_count: int,
    keys: set[str],
    scores: Scores | None,
    complete: bool,
    auxiliary: bool,
    missing: list[str],
    match: ResearchMatch,
) -> Assessment:
    return Assessment(
        (
            stability,
            0.4 * float(scores is not None) + 0.2 * float(complete) + 0.4 * quality,
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
        auxiliary,
        tuple(missing),
        tuple(
            f"{CLAIM_LABELS.get(c.key, c.key)}：{c.value} [{c.evidence_id}]" for c in match.claims
        ),
        ("V1参数未经实战校准，情景与价格可能不一致",),
        ("风险EV扣除3个百分点；无实证校准最高C",),
        scores is not None,
    )
