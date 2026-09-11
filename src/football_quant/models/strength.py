"""Evidence-backed long/recent, opponent-adjusted goal-rate ensemble."""

from dataclasses import dataclass
from datetime import datetime
from math import exp, log

from football_quant.domain import aware, number, probability


@dataclass(frozen=True)
class History:
    played: datetime
    goals_for: float
    goals_against: float
    opponent_attack: float
    opponent_defence: float
    xg_for: float | None
    xg_against: float | None
    evidence_id: str

    def __post_init__(self) -> None:
        aware(self.played)
        for name in ("goals_for", "goals_against", "opponent_attack", "opponent_defence"):
            number(getattr(self, name), name, 0)
        if min(self.opponent_attack, self.opponent_defence) <= 0:
            raise ValueError("opponent factors must be positive")
        for value in (self.xg_for, self.xg_against):
            if value is not None:
                number(value, "xG", 0)
        if (self.xg_for is None) != (self.xg_against is None):
            raise ValueError("paired same-provider xG/xGA required")


@dataclass(frozen=True)
class GoalEstimate:
    home: float
    away: float
    stability: float
    notes: tuple[str, ...]


def rates(history: tuple[History, ...], at: datetime, half_life: float) -> tuple[float, float]:
    aware(at)
    if number(half_life, "half life") <= 0:
        raise ValueError("positive half life required")
    weights = []
    attack, defence = [], []
    for row in history:
        days = (at - row.played).total_seconds() / 86400
        if days <= 0:
            raise ValueError("history must precede forecast")
        weight = exp(-log(2) * days / half_life)
        weights.append(weight)
        # Equal goals/xG blend only if both same-provider inputs exist.
        gf = row.goals_for if row.xg_for is None else (row.goals_for + row.xg_for) / 2
        ga = (
            row.goals_against
            if row.xg_against is None
            else (row.goals_against + row.xg_against) / 2
        )
        attack.append(weight * gf / row.opponent_defence)
        defence.append(weight * ga / row.opponent_attack)
    if not weights or sum(weights) <= 1e-12:
        raise ValueError("insufficient recent historical mass")
    return sum(attack) / sum(weights), sum(defence) / sum(weights)


def estimate(
    home: tuple[History, ...],
    away: tuple[History, ...],
    at: datetime,
    league_home: float,
    league_away: float,
    same_basis: bool,
) -> GoalEstimate:
    if same_basis is not True:
        raise ValueError("跨联赛或升降级基准缺少可验证桥接")
    if len(home) < 8 or len(away) < 8:
        raise ValueError("主客场历史各至少8场，否则不生成λ")
    for base in (league_home, league_away):
        if number(base, "league baseline") <= 0:
            raise ValueError("联赛主客基准必须为正")
    if len({r.played for r in home}) != len(home) or len({r.played for r in away}) != len(away):
        raise ValueError("duplicate historical match times")
    long_h, long_a = rates(home, at, 180), rates(away, at, 180)
    recent_h, recent_a = rates(home, at, 45), rates(away, at, 45)
    long = (long_h[0] * long_a[1] / league_home, long_a[0] * long_h[1] / league_away)
    recent = (recent_h[0] * recent_a[1] / league_home, recent_a[0] * recent_h[1] / league_away)
    blended = tuple(0.65 * a + 0.35 * b for a, b in zip(long, recent, strict=True))
    if min(blended) <= 0:
        raise ValueError("零进球样本不能构造虚假正λ，需要额外基准证据")
    disagreement = max(abs(a - b) / max(a, b, 0.01) for a, b in zip(long, recent, strict=True))
    stability = probability(max(0, 1 - disagreement))
    notes = (
        "长期与近期模型按65%和35%融合，半衰期180天和45天，参数尚未回测校准。",
        "按主客场拆分及对手攻防比率归一化，不使用积分排名推断实力。",
        "进球与同口径xG各占一半；无xG时仅用进球并披露缺失。",
    )
    return GoalEstimate(*blended, stability, notes)
