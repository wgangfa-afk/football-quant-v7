"""Validated research package records used by the application."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from football_quant.domain import Evidence, Fixture, Mode, Quote
from football_quant.evidence.verification import Claim


@dataclass(frozen=True)
class ResearchMatch:
    fixture: Fixture
    quotes: tuple[Quote, ...]
    claims: tuple[Claim, ...]
    data: str
    notes: tuple[str, ...]
    missing: tuple[str, ...]


@dataclass(frozen=True)
class Research:
    mode: Mode
    started: datetime
    deadline: datetime
    generated: datetime
    evidence: tuple[Evidence, ...]
    matches: tuple[ResearchMatch, ...]
    coverage: tuple[str, ...]
    root: Path


def supported_value(row: dict[str, Any], snapshots: dict[str, str]) -> None:
    evidence_id, excerpt = row["evidence_id"], row["excerpt"]
    if evidence_id not in snapshots or not isinstance(excerpt, str) or not excerpt.strip():
        raise ValueError("every analytical input requires a source and excerpt")
    if excerpt not in snapshots[evidence_id]:
        raise ValueError(f"input excerpt not found in snapshot: {evidence_id}")
