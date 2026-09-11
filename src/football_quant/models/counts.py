"""Independent count models with their own data, dispersion and settlement units."""

from dataclasses import dataclass
from enum import StrEnum
from math import exp, lgamma, log
from statistics import mean, variance

from football_quant.domain import number
from football_quant.models.goals import Scores


class CountKind(StrEnum):
    CORNERS = "corners"
    CARDS = "cards"


@dataclass(frozen=True)
class CountInputs:
    kind: CountKind
    home_for: tuple[int, ...]
    home_against: tuple[int, ...]
    away_for: tuple[int, ...]
    away_against: tuple[int, ...]
    units: str

    def __post_init__(self) -> None:
        expected = "corners" if self.kind is CountKind.CORNERS else "yellow_cards"
        if self.units != expected:
            raise ValueError("计数口径不支持或不一致；V1罚牌仅支持黄牌张数")
        for values in (self.home_for, self.home_against, self.away_for, self.away_against):
            if len(values) < 8:
                raise ValueError("角球或罚牌各项至少8场独立历史样本")
            for value in values:
                number(value, "count", 0)
                if not isinstance(value, int):
                    raise ValueError("count observations must be integers")


@dataclass(frozen=True)
class CountEstimate:
    scores: Scores
    home: float
    away: float
    notes: tuple[str, ...]


def negative_binomial(mu: float, dispersion: float) -> tuple[float, ...]:
    if number(mu, "count mean") <= 0 or number(dispersion, "dispersion") <= 0:
        raise ValueError("positive count mean and dispersion required")
    if mu > 100 or dispersion < 0.1:
        raise ValueError("count distribution outside validated numerical range")
    p = dispersion / (dispersion + mu)
    values = []
    for n in range(1000):
        log_p = (
            lgamma(n + dispersion)
            - lgamma(dispersion)
            - lgamma(n + 1)
            + dispersion * log(p)
            + n * log(1 - p)
        )
        values.append(exp(log_p))
        if 1 - sum(values) < 1e-11:
            return tuple(values)
    raise ValueError("count tail failed to converge")


def marginal(scored: tuple[int, ...], conceded: tuple[int, ...]) -> tuple[float, tuple[float, ...]]:
    from football_quant.models.goals import poisson

    mu = (mean(scored) + mean(conceded)) / 2
    if mu <= 0:
        raise ValueError("计数均值为零，缺少可靠分布输入")
    var = (variance(scored) + variance(conceded)) / 2
    if var <= mu:
        return mu, poisson(mu)
    return mu, negative_binomial(mu, mu * mu / (var - mu))


def count_model(inputs: CountInputs) -> CountEstimate:
    home, h = marginal(inputs.home_for, inputs.away_against)
    away, a = marginal(inputs.away_for, inputs.home_against)
    mass = sum(h) * sum(a)
    matrix = tuple(tuple(x * y / mass for y in a) for x in h)
    label = "角球" if inputs.kind is CountKind.CORNERS else "黄牌"
    return CountEstimate(
        Scores(matrix, 1 - mass, inputs.kind.value),
        home,
        away,
        (
            f"{label}独立计数模型：主队均值{home:.2f}、客队均值{away:.2f}。",
            "使用对应主客场获得/送出历史；样本过度离散时采用负二项，否则Poisson基线。",
            "两队计数独立假设未校准，忽略比分状态相关性，V1辅助市场最高C。",
        ),
    )
