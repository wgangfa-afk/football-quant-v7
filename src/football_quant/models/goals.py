"""Poisson and Dixon-Coles score distributions with explicit truncation."""

from dataclasses import dataclass
from math import exp
from typing import Literal

from football_quant.domain import number, probability


@dataclass(frozen=True)
class Scores:
    matrix: tuple[tuple[float, ...], ...]
    omitted_mass: float
    family: Literal["goals", "corners", "cards"] = "goals"

    def __post_init__(self) -> None:
        if self.family not in ("goals", "corners", "cards"):
            raise ValueError("invalid distribution family")
        if not self.matrix or not self.matrix[0]:
            raise ValueError("empty distribution")
        width = len(self.matrix[0])
        for row in self.matrix:
            if len(row) != width:
                raise ValueError("nonrectangular distribution")
            for p in row:
                probability(p)
        if abs(sum(map(sum, self.matrix)) - 1) > 1e-8:
            raise ValueError("distribution must sum to one")
        probability(self.omitted_mass)

    def result(self) -> tuple[float, float, float]:
        return tuple(
            sum(p for i, row in enumerate(self.matrix) for j, p in enumerate(row) if test(i, j))
            for test in (lambda i, j: i > j, lambda i, j: i == j, lambda i, j: i < j)
        )

    def btts(self) -> float:
        return sum(p for i, row in enumerate(self.matrix) for j, p in enumerate(row) if i and j)

    def common(self, count: int = 5) -> tuple[tuple[int, int, float], ...]:
        return tuple(
            sorted(
                ((i, j, p) for i, row in enumerate(self.matrix) for j, p in enumerate(row)),
                key=lambda item: (-item[2], item[0], item[1]),
            )[:count]
        )


def poisson(mean: float, tolerance: float = 1e-12) -> tuple[float, ...]:
    mean = number(mean, "lambda", 0)
    tolerance = probability(tolerance)
    if not 0 < mean <= 100 or not 0 < tolerance <= 1e-6:
        raise ValueError("lambda in (0,100], tolerance in (0,1e-6] required")
    values = [exp(-mean)]
    while 1 - sum(values) > tolerance:
        values.append(values[-1] * mean / len(values))
        if len(values) > 1000:
            raise ValueError("Poisson tail failed to converge")
    return tuple(values)


def score_matrix(home: float, away: float, rho: float = 0) -> Scores:
    home, away = number(home, "lambda home"), number(away, "lambda away")
    h, a = poisson(home), poisson(away)
    rho = number(rho, "rho")
    corrections = {
        (0, 0): 1 - home * away * rho,
        (0, 1): 1 + home * rho,
        (1, 0): 1 + away * rho,
        (1, 1): 1 - rho,
    }
    if min(corrections.values()) < 0:
        raise ValueError("Dixon-Coles correction has negative mass")
    raw = tuple(
        tuple(x * y * corrections.get((i, j), 1) for j, y in enumerate(a)) for i, x in enumerate(h)
    )
    total = sum(map(sum, raw))
    return Scores(tuple(tuple(p / total for p in row) for row in raw), max(0, 1 - sum(h) * sum(a)))
