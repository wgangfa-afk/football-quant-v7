"""Local task files: no football decisions and no database."""

import json
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from enum import Enum
from hashlib import sha256
from pathlib import Path
from typing import Any

from football_quant.domain import Evidence, Report


def inside(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("snapshot path escapes research package")
    return path


def verify_snapshot(root: Path, evidence: Evidence) -> str:
    raw = inside(root, evidence.snapshot_path).read_bytes()
    if sha256(raw).hexdigest() != evidence.content_hash:
        raise ValueError(f"snapshot hash mismatch: {evidence.id}")
    return raw.decode("utf-8")


def encode(value: object) -> str:
    if isinstance(value, (datetime, Decimal, Enum)):
        return value.isoformat() if isinstance(value, datetime) else str(value)
    raise TypeError(f"unsupported serialization type {type(value).__name__}")


def save_report(report: Report, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(asdict(report), default=encode, ensure_ascii=False, sort_keys=True, indent=2)
    path.write_text(text + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    def invalid(value: str) -> None:
        raise ValueError(f"non-finite JSON: {value}")

    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON field {key}")
            result[key] = value
        return result

    data = json.loads(
        path.read_text(encoding="utf-8"), parse_constant=invalid, object_pairs_hook=unique
    )
    if not isinstance(data, dict):
        raise ValueError("research package must be an object")
    return data
