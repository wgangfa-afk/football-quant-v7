"""Infrastructure-free immutable research records."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from math import isfinite


class Mode(StrEnum):
    TEST = "test"
    LIVE = "live"


class Status(StrEnum):
    VERIFIED = "verified"
    UNCERTAIN = "uncertain"
    CONFLICT = "conflict"
    MISSING = "missing"


class Grade(StrEnum):
    S = "S"
    A = "A"
    B = "B"
    C = "C"
    PASS = "PASS"


class Market(StrEnum):
    RESULT = "1x2"
    HANDICAP = "asian_handicap"
    TOTAL = "asian_total"
    GOALS = "exact_goals"
    BTTS = "btts"
    CORNER_TOTAL = "corner_total"
    CORNER_HANDICAP = "corner_handicap"
    CARD_TOTAL = "card_total"
    CARD_HANDICAP = "card_handicap"


def number(value: object, name: str, minimum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise ValueError(f"{name}: finite numeric input required")
    result = float(value)
    if not isfinite(result) or (minimum is not None and result < minimum):
        raise ValueError(f"{name}: invalid finite range")
    return result


def probability(value: object, name: str = "probability") -> float:
    result = number(value, name, 0)
    if result > 1:
        raise ValueError(f"{name}: must be in [0,1]")
    return result


def aware(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timezone-aware datetime required")
    return value


@dataclass(frozen=True)
class Fixture:
    id: str
    home: str
    away: str
    competition: str
    kickoff: datetime
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        aware(self.kickoff)
        if not all((self.id, self.home, self.away, self.competition)):
            raise ValueError("fixture identity is required")


@dataclass(frozen=True)
class Evidence:
    id: str
    source_url: str
    source_name: str
    retrieved_at_utc: datetime
    observed_at_utc: datetime | None
    published_at_utc: datetime | None
    source_type: str
    content_hash: str
    extraction_method: str
    validation_status: Status
    mode: Mode
    snapshot_path: str

    def __post_init__(self) -> None:
        for value in (self.retrieved_at_utc, self.observed_at_utc, self.published_at_utc):
            if value is not None:
                aware(value)
                if value.utcoffset().total_seconds() != 0:
                    raise ValueError("evidence timestamps must be UTC")
        if len(self.content_hash) != 64 or any(
            c not in "0123456789abcdef" for c in self.content_hash
        ):
            raise ValueError("SHA256 required")
        if not self.source_url.startswith(("http://", "https://")):
            raise ValueError("public source URL required")


@dataclass(frozen=True)
class Quote:
    market: Market
    selection: str
    line: Decimal | None
    original_value: str
    original_format: str
    decimal_odds: Decimal
    evidence_id: str
    bookmaker: str
    rules: str

    def __post_init__(self) -> None:
        if number(self.decimal_odds, "odds") <= 1:
            raise ValueError("decimal odds must exceed 1")
        if self.line is not None:
            number(self.line, "line")
        if not self.rules or not self.bookmaker:
            raise ValueError("explicit rules and bookmaker required")


@dataclass(frozen=True)
class Price:
    model_probability: float
    implied_probability: float
    devig_probability: float | None
    fair_odds: Decimal | None
    current_odds: Decimal
    ev: Decimal
    risk_ev: Decimal
    states: tuple[float, float, float, float, float]


@dataclass(frozen=True)
class Candidate:
    fixture_id: str
    quote: Quote
    price: Price | None
    grade: Grade
    confidence: float
    completeness: float
    supports: tuple[str, ...]
    objections: tuple[str, ...]
    risks: tuple[str, ...]
    reasons: tuple[str, ...]
    score_components: tuple[tuple[str, float], ...]


@dataclass(frozen=True)
class MatchAnalysis:
    fixture: Fixture
    candidates: tuple[Candidate, ...]
    notes: tuple[str, ...]
    missing: tuple[str, ...]
    conflicts: tuple[str, ...]
    lambda_home: float | None
    lambda_away: float | None
    scores: tuple[tuple[int, int, float], ...]


@dataclass(frozen=True)
class Report:
    mode: Mode
    started: datetime
    deadline: datetime
    generated: datetime
    evidence: tuple[Evidence, ...]
    matches: tuple[MatchAnalysis, ...]
    coverage_notes: tuple[str, ...]

    def __post_init__(self) -> None:
        for value in (self.started, self.deadline, self.generated):
            aware(value)
        if self.deadline <= self.started or self.generated < self.started:
            raise ValueError("invalid report time window")
        if self.mode is Mode.LIVE and any(e.mode is Mode.TEST for e in self.evidence):
            raise ValueError("test evidence forbidden in live report")
