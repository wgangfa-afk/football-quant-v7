from dataclasses import replace
from pathlib import Path

import pytest

from football_quant.acquisition.package import load_research
from football_quant.decisions.analysis import analyze_match
from football_quant.domain import Grade, Market, Report
from football_quant.evidence.merge import merge_matches
from football_quant.reporting.word import write_report

PACKAGE = Path("fixtures/research-test/manifest.json")


def test_saved_package_to_multimarket_word(tmp_path: Path) -> None:
    research = load_research(PACKAGE)
    result = analyze_match(research.matches[0], research)
    assert result == analyze_match(research.matches[0], research)
    assert result.lambda_home > 0
    assert len(result.candidates) == 7
    assert all(c.price is not None for c in result.candidates)
    assert {c.quote.market for c in result.candidates} == {
        Market.RESULT,
        Market.CORNER_TOTAL,
        Market.CARD_TOTAL,
    }
    assert sum(c.grade is Grade.C for c in result.candidates) == 3
    report = Report(
        research.mode,
        research.started,
        research.deadline,
        research.generated,
        research.evidence,
        (result,),
        research.coverage,
    )
    path = tmp_path / "integrated.docx"
    write_report(report, path)
    from docx import Document

    text = "\n".join(p.text for p in Document(path).paragraphs)
    assert "香港水位" in text
    assert "罚牌大小" in text
    assert "角球大小" in text


def test_missing_goal_history_does_not_poison_auxiliary() -> None:
    import json

    research = load_research(PACKAGE)
    match = research.matches[0]
    data = json.loads(match.data)
    del data["baseline"]
    match = replace(match, data=json.dumps(data))
    result = analyze_match(match, research)
    assert result.lambda_home is None
    assert all(c.price is None for c in result.candidates if c.quote.market is Market.RESULT)
    assert all(
        c.price is not None for c in result.candidates if c.quote.market is Market.CORNER_TOTAL
    )


def test_dedup_preserves_history_and_time_conflicts() -> None:
    from datetime import timedelta

    research = load_research(PACKAGE)
    match = research.matches[0]
    changed = replace(
        match,
        fixture=replace(
            match.fixture, id="another", kickoff=match.fixture.kickoff + timedelta(hours=1)
        ),
    )
    merged = merge_matches((match, changed))
    assert len(merged) == 1
    assert len(merged[0].quotes) == 7
    result = analyze_match(merged[0], research)
    assert result.conflicts
    assert all(c.grade is Grade.PASS for c in result.candidates)


def test_bad_excerpt_is_not_accepted(tmp_path: Path) -> None:
    import json
    import shutil

    raw = json.loads(PACKAGE.read_text())
    shutil.copy(PACKAGE.parent / "snapshot.txt", tmp_path)
    raw["matches"][0]["quotes"][0]["excerpt"] = "not in snapshot"
    (tmp_path / "manifest.json").write_text(json.dumps(raw))
    with pytest.raises(ValueError, match="excerpt not found"):
        load_research(tmp_path / "manifest.json")


def test_earlier_quotes_cannot_be_current_recommendations() -> None:
    from datetime import timedelta

    from football_quant.evidence.quote_history import historical_quotes

    research = load_research(PACKAGE)
    source = research.evidence[0]
    earlier = replace(
        source, id="earlier", observed_at_utc=source.observed_at_utc - timedelta(hours=1)
    )
    current = research.matches[0].quotes[0]
    old = replace(current, evidence_id="earlier")
    historical, notes = historical_quotes((current, old), (source, earlier))
    assert historical == frozenset((old,))
    assert "最早可见值不等于已核验初盘" in notes[0]
