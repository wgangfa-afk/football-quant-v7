"""Transparent policy score, not a calibrated win probability."""

from dataclasses import dataclass

from football_quant.domain import (
    Advantage,
    Candidate,
    Capability,
    Decision,
    Grade,
    Price,
    Quote,
    Status,
    probability,
)

WEIGHTS = (0.15, 0.15, 0.10, 0.12, 0.10, 0.08, 0.08, 0.07, 0.07, 0.08)
NAMES = (
    "稳定性",
    "数据完整",
    "多源一致",
    "基本面",
    "市场价格",
    "人员",
    "战术",
    "赛程",
    "联赛质量",
    "校准",
)


@dataclass(frozen=True)
class Assessment:
    components: tuple[float, ...]
    calibrated: bool
    auxiliary: bool
    blockers: tuple[str, ...]
    supports: tuple[str, ...]
    objections: tuple[str, ...]
    risks: tuple[str, ...]
    model_available: bool = False

    def __post_init__(self) -> None:
        if len(self.components) != 10:
            raise ValueError("ten rating components required")
        for value in self.components:
            probability(value)


def recommend(
    fixture_id: str, quote: Quote, price: Price | None, assessment: Assessment
) -> Candidate:
    components = list(assessment.components)
    components[4] = max(0, min(1, 0.5 + float(price.ev) * 2)) if price else 0
    score = sum(w * v for w, v in zip(WEIGHTS, components, strict=True))
    blockers = list(assessment.blockers)
    if price is None and not assessment.model_available:
        blockers.append("缺少可核验模型概率")
    grade = Grade.PASS
    if not blockers:
        for minimum, label in ((0.90, Grade.S), (0.80, Grade.A), (0.68, Grade.B), (0.50, Grade.C)):
            if score >= minimum:
                grade = label
                break
        if grade is not Grade.PASS and (not assessment.calibrated or assessment.auxiliary):
            grade = Grade.C
        if grade is Grade.PASS:
            blockers.append("综合证据评分不足50分")
    return Candidate(
        fixture_id,
        quote,
        price,
        grade,
        score if price else None,
        components[1],
        assessment.supports,
        assessment.objections,
        assessment.risks,
        tuple(blockers),
        tuple(zip(NAMES, components, strict=True)) if price else (),
        Capability.FULL
        if price and price.devig_probability is not None
        else Capability.PARTIAL
        if price
        else Capability.NONE,
        Decision.UNAVAILABLE
        if price is None
        else Decision.REJECTED
        if grade is Grade.PASS
        else Decision.DIRECTION,
        Advantage.UNKNOWN
        if price is None
        else Advantage.POSITIVE
        if price.ev > 0
        else Advantage.NONPOSITIVE,
        Status.MISSING if price is None or price.devig_probability is None else Status.VERIFIED,
        ("model_probability",)
        if price is None
        else ("devig_probability: 缺少同口径可比时间完整互斥市场",)
        if price.devig_probability is None
        else (),
    )
