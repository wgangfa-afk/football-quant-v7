"""Load saved research with provenance and no-network enforcement by design."""

import json
from decimal import InvalidOperation
from pathlib import Path
from typing import Any

from football_quant.acquisition.imports import (
    evidence_record,
    fixture_record,
    quote_record,
    timestamp,
)
from football_quant.domain import Mode, Qualitative
from football_quant.evidence.merge import merge_matches
from football_quant.evidence.research import Research, ResearchMatch, supported_value
from football_quant.evidence.verification import Claim
from football_quant.storage.files import read_json, verify_snapshot


def validate_inputs(value: Any, snapshots: dict[str, str]) -> None:
    if isinstance(value, dict):
        if "evidence_id" in value:
            supported_value(value, snapshots)
        for child in value.values():
            validate_inputs(child, snapshots)
    elif isinstance(value, list):
        for child in value:
            validate_inputs(child, snapshots)


def qualitative_record(raw: dict[str, Any] | None) -> Qualitative | None:
    if raw is None:
        return None
    rows = raw["supports"] + raw["objections"]
    return Qualitative(
        raw["direction"],
        tuple(f"{r['reasoning']} [{r['evidence_id']}]" for r in raw["supports"]),
        tuple(f"{r['reasoning']} [{r['evidence_id']}]" for r in raw["objections"]),
        tuple(raw["uncertainties"]),
        tuple(sorted({r["evidence_id"] for r in rows})),
    )


def load_research(path: Path) -> Research:
    raw = read_json(path)
    mode = Mode(raw["mode"])
    sources = tuple(evidence_record(row, path.parent) for row in raw["evidence"])
    if len({e.id for e in sources}) != len(sources):
        raise ValueError("duplicate evidence IDs")
    if mode is Mode.LIVE and any(e.mode is not Mode.LIVE for e in sources):
        raise ValueError("test evidence forbidden in live research")
    snapshots = {e.id: verify_snapshot(path.parent, e) for e in sources}
    matches = []
    for row in raw["matches"]:
        fixture = fixture_record(row["fixture"])
        if not fixture.evidence_ids or any(e not in snapshots for e in fixture.evidence_ids):
            raise ValueError("fixture requires known evidence")
        validate_inputs(row, snapshots)
        accepted, quote_errors = [], []
        for q in row.get("quotes", []):
            try:
                accepted.append(quote_record(q))
            except (ValueError, InvalidOperation) as exc:
                quote_errors.append(
                    f"拒绝无效报价 {q.get('market')}/{q.get('selection')}：{exc}；"
                    f"原始值 {q.get('original_value')} {q.get('original_format')}"
                )
        quotes = tuple(accepted)
        if any(q.evidence_id not in snapshots for q in quotes):
            raise ValueError("unknown quote evidence")
        claims = tuple(Claim(c["key"], c["value"], c["evidence_id"]) for c in row.get("claims", []))
        matches.append(
            ResearchMatch(
                fixture,
                quotes,
                claims,
                json.dumps(row.get("history", {}), ensure_ascii=False),
                tuple(row.get("notes", [])),
                tuple(row.get("missing", [])) + tuple(quote_errors),
                qualitative_record(row.get("qualitative")),
            )
        )
    start, end, generated = (timestamp(raw[k]) for k in ("started", "deadline", "generated"))
    if not start < end or generated < start:
        raise ValueError("invalid research time window")
    if any(e.retrieved_at_utc > generated for e in sources):
        raise ValueError("evidence collected after generation")
    return Research(
        mode,
        start,
        end,
        generated,
        sources,
        merge_matches(tuple(matches)),
        tuple(raw["coverage_notes"]),
        path.parent,
    )
