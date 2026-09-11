"""Evidence checks preserve missing facts and competing assertions."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from urllib.parse import urlsplit

from football_quant.domain import Evidence, Fixture, Status, aware


@dataclass(frozen=True)
class Claim:
    key: str
    value: str
    evidence_id: str


@dataclass(frozen=True)
class Finding:
    key: str
    assertions: tuple[Claim, ...]
    status: Status
    reason: str
    independent_sources: int


def reconcile(key: str, claims: tuple[Claim, ...], sources: tuple[Evidence, ...]) -> Finding:
    selected = tuple(c for c in claims if c.key == key)
    if not selected:
        return Finding(key, (), Status.MISSING, "无可核验来源", 0)
    by_id = {e.id: e for e in sources}
    if any(c.evidence_id not in by_id for c in selected):
        raise ValueError("claim references unknown evidence")
    # Operator/source names and hostnames are both required to differ.
    names = {by_id[c.evidence_id].source_name for c in selected}
    hosts = {urlsplit(by_id[c.evidence_id].source_url).hostname for c in selected}
    count = min(len(names), len(hosts))
    if len({c.value for c in selected}) > 1:
        return Finding(key, selected, Status.CONFLICT, "来源冲突，保留全部原值", count)
    verified = count >= 2 and all(
        by_id[c.evidence_id].validation_status is Status.VERIFIED for c in selected
    )
    return Finding(
        key,
        selected,
        Status.VERIFIED if verified else Status.UNCERTAIN,
        "多源一致" if verified else "独立来源不足或未核验",
        count,
    )


def freshness(
    source: Evidence, at: datetime, maximum_age: timedelta = timedelta(hours=6)
) -> str | None:
    aware(at)
    if source.retrieved_at_utc > at:
        return "采集时间在任务生成时间之后"
    observed = source.observed_at_utc
    if observed is None:
        return "页面未提供盘口观察时间，报价新鲜度不确定"
    if observed > source.retrieved_at_utc:
        return "盘口观察时间晚于采集时间"
    if at - observed > maximum_age:
        return "盘口已过期（超过6小时政策窗口）"
    return None


def window_reason(
    fixture: Fixture, start: datetime, end: datetime, generated: datetime
) -> str | None:
    for value in (start, end, generated):
        aware(value)
    if end <= start:
        raise ValueError("deadline must be after start")
    if fixture.kickoff <= start:
        return "采集时已开赛或已结束"
    if fixture.kickoff > end:
        return "比赛在截止时间之后"
    if fixture.kickoff <= generated:
        return "报告生成时已开赛，不再属于赛前可执行方向"
    return None


def deduplicate(fixtures: tuple[Fixture, ...]) -> tuple[Fixture, ...]:
    result: dict[tuple[str, str, str, datetime], Fixture] = {}
    for f in fixtures:
        key = (
            f.home.casefold().strip(),
            f.away.casefold().strip(),
            f.competition.casefold().strip(),
            f.kickoff,
        )
        if key in result:
            old = result[key]
            result[key] = Fixture(
                old.id,
                old.home,
                old.away,
                old.competition,
                old.kickoff,
                tuple(sorted(set(old.evidence_ids + f.evidence_ids))),
            )
        else:
            result[key] = f
    return tuple(sorted(result.values(), key=lambda f: (f.kickoff, f.id)))
