from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest

from football_quant.acquisition.pages import extract, public_url
from football_quant.application import demo
from football_quant.domain import Mode, Status
from football_quant.evidence.verification import (
    Claim,
    deduplicate,
    freshness,
    reconcile,
    window_reason,
)
from football_quant.storage.files import verify_snapshot


def test_saved_html_extracts_visible_table_and_json_ld() -> None:
    page = Path("fixtures/page.html").read_text()
    extracted = extract(page, ".html")
    assert extracted["rows"][1] == ("2.10", "3.40", "3.60")
    assert extracted["json_ld"][0]["@type"] == "SportsEvent"
    assert "@type" not in extracted["text"]


@pytest.mark.parametrize(
    "url",
    [
        "https://api.example.com/odds",
        "https://e.com/api/x",
        "https://name:pass@example.com",
        "https://e.com/?token=x",
    ],
)
def test_forbidden_urls(url: str) -> None:
    with pytest.raises(ValueError):
        public_url(url)


def test_conflicts_missing_and_independent_sources() -> None:
    a = demo().evidence[0]
    b = replace(a, id="b", source_url="https://other.example.org/page", source_name="independent")
    claims = (Claim("kickoff", "13:00", a.id), Claim("kickoff", "14:00", b.id))
    result = reconcile("kickoff", claims, (a, b))
    assert result.status is Status.CONFLICT
    assert result.assertions == claims
    assert result.independent_sources == 2
    assert reconcile("injury", claims, (a, b)).status is Status.MISSING
    equal = (claims[0], replace(claims[1], value="13:00"))
    assert reconcile("kickoff", equal, (a, b)).status is Status.VERIFIED


def test_freshness_and_window_boundary() -> None:
    report = demo()
    source = report.evidence[0]
    assert "未提供" in freshness(source, report.generated)
    source = replace(source, observed_at_utc=report.started - timedelta(hours=7))
    assert "过期" in freshness(source, report.generated)
    f = report.matches[0].fixture
    assert window_reason(f, report.started, report.deadline, report.generated) is None
    assert "已开赛" in window_reason(f, report.started, report.deadline, f.kickoff)
    assert window_reason(f, report.started, f.kickoff, report.generated) is None


def test_dedup_aware_equivalent_times() -> None:
    from zoneinfo import ZoneInfo

    f = demo().matches[0].fixture
    b = replace(
        f,
        id="other",
        kickoff=f.kickoff.astimezone(ZoneInfo("Asia/Shanghai")),
        evidence_ids=("new",),
    )
    result = deduplicate((f, b))
    assert len(result) == 1
    assert result[0].evidence_ids == ("new", "test-1")


def test_snapshot_tamper_and_test_live_isolation(tmp_path: Path) -> None:
    report = demo()
    e = replace(report.evidence[0], snapshot_path="snapshot.txt")
    (tmp_path / "snapshot.txt").write_text("tampered")
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_snapshot(tmp_path, e)
    with pytest.raises(ValueError, match="test evidence"):
        replace(report, mode=Mode.LIVE)
