"""Strict evidence/fixture/quote imports from Codex-reviewed research files."""

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from football_quant.acquisition.pages import public_url
from football_quant.domain import Evidence, Fixture, Market, Mode, Quote, Status, aware
from football_quant.markets.odds import OddsFormat, to_decimal
from football_quant.storage.files import verify_snapshot


def timestamp(value: str) -> datetime:
    return aware(datetime.fromisoformat(value)).astimezone(UTC)


def evidence_record(row: dict[str, Any], root: Path) -> Evidence:
    evidence = Evidence(
        id=row["id"],
        source_url=public_url(row["source_url"]),
        source_name=row["source_name"],
        retrieved_at_utc=timestamp(row["retrieved_at_utc"]),
        observed_at_utc=timestamp(row["observed_at_utc"]) if row.get("observed_at_utc") else None,
        published_at_utc=timestamp(row["published_at_utc"])
        if row.get("published_at_utc")
        else None,
        source_type=row["source_type"],
        content_hash=row["content_hash"],
        extraction_method=row["extraction_method"],
        validation_status=Status(row["validation_status"]),
        mode=Mode(row["mode"]),
        snapshot_path=row["snapshot_path"],
    )
    verify_snapshot(root, evidence)
    return evidence


def fixture_record(row: dict[str, Any]) -> Fixture:
    return Fixture(
        row["id"],
        row["home"],
        row["away"],
        row["competition"],
        timestamp(row["kickoff"]),
        tuple(row["evidence_ids"]),
    )


def quote_record(row: dict[str, Any]) -> Quote:
    required = (
        "market",
        "selection",
        "original_value",
        "original_format",
        "evidence_id",
        "bookmaker",
        "rules",
    )
    missing = tuple(k for k in required if not row.get(k))
    if missing:
        raise ValueError("missing quote fields: " + ", ".join(missing))
    original = row["original_value"]
    if not isinstance(original, str):
        raise ValueError("original odds must retain page text as a string")
    line = row.get("line")
    if line is not None and not isinstance(line, str):
        raise ValueError("line must be a decimal string")
    return Quote(
        Market(row["market"]),
        row["selection"],
        Decimal(line) if line else None,
        original,
        row["original_format"],
        to_decimal(Decimal(original), OddsFormat(row["original_format"])),
        row["evidence_id"],
        row["bookmaker"],
        row["rules"],
    )
