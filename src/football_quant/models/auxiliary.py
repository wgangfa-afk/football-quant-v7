"""Source-required corner/card inputs; never fall back to goal parameters."""

from typing import Any

from football_quant.models.counts import CountEstimate, CountInputs, CountKind, count_model


def auxiliary_inputs(data: dict[str, Any], kind: CountKind) -> CountEstimate:
    raw = data.get(kind.value)
    if not raw:
        raise ValueError(f"缺少{kind.value}独立历史数据")
    values = []
    for field in ("home_for", "home_against", "away_for", "away_against"):
        rows = raw.get(field, [])
        for r in rows:
            if not r.get("evidence_id") or not r.get("excerpt"):
                raise ValueError("辅助历史统计缺少证据")
            if r.get("units") != raw["units"]:
                raise ValueError("历史和当前盘口计数口径不一致")
        values.append(tuple(r["count"] for r in rows))
    return count_model(CountInputs(kind, *values, raw["units"]))
