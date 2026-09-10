"""Translate verified historical records into football model inputs."""

from datetime import datetime
from typing import Any

from football_quant.domain import aware, number
from football_quant.models.strength import GoalEstimate, History, estimate


def historical_row(row: dict[str, Any]) -> History:
    return History(
        aware(datetime.fromisoformat(row["played"])),
        row["goals_for"],
        row["goals_against"],
        row["opponent_attack"],
        row["opponent_defence"],
        row.get("xg_for"),
        row.get("xg_against"),
        row["evidence_id"],
    )


def goal_inputs(data: dict[str, Any], at: datetime) -> GoalEstimate:
    if not data:
        raise ValueError("缺少带来源的历史统计，不能生成预期进球")
    for key in ("baseline", "home", "away"):
        if key not in data:
            raise ValueError(f"缺少历史模型输入 {key}")
    baseline = data["baseline"]
    if not baseline.get("evidence_id") or not baseline.get("excerpt"):
        raise ValueError("联赛基准缺少来源")
    for side in ("home", "away"):
        for row in data[side]:
            if not row.get("evidence_id") or not row.get("excerpt"):
                raise ValueError("历史数据缺少来源")
            if row.get("venue") != side:
                raise ValueError("必须使用对应主客场历史拆分")
            if row.get("xg_for") is not None and not row.get("xg_provider"):
                raise ValueError("xG缺少供应商口径")
    providers = {
        r["xg_provider"]
        for side in ("home", "away")
        for r in data[side]
        if r.get("xg_for") is not None
    }
    if len(providers) > 1:
        raise ValueError("xG供应商冲突，不能混合")
    return estimate(
        tuple(historical_row(r) for r in data["home"]),
        tuple(historical_row(r) for r in data["away"]),
        at,
        number(baseline["home"], "league home"),
        number(baseline["away"], "league away"),
        baseline["same_basis"],
    )
