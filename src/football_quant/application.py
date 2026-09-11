"""Application orchestration and explicit test demonstration."""

import argparse
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from pathlib import Path

from football_quant.acquisition.package import load_research
from football_quant.decisions.analysis import analyze_match
from football_quant.decisions.rating import Assessment, recommend
from football_quant.domain import (
    Evidence,
    Fixture,
    Market,
    MatchAnalysis,
    Mode,
    Quote,
    Report,
    Status,
)
from football_quant.markets.odds import devig
from football_quant.markets.pricing import price
from football_quant.models.goals import score_matrix
from football_quant.reporting.word import summary, write_report
from football_quant.storage.files import save_report


def demo() -> Report:
    root = Path(__file__).resolve().parents[2]
    snapshot = root / "fixtures/m1_snapshot.txt"
    start = datetime(2030, 1, 1, 10, tzinfo=UTC)
    evidence = Evidence(
        "test-1",
        "https://example.com/test-fixture",
        "合成数学测试数据",
        start,
        None,
        None,
        "test_fixture",
        sha256(snapshot.read_bytes()).hexdigest(),
        "fixed_fixture",
        Status.VERIFIED,
        Mode.TEST,
        str(snapshot),
    )
    fixture = Fixture(
        "test-match",
        "测试主队",
        "测试客队",
        "合成测试联赛",
        datetime(2030, 1, 1, 13, tzinfo=UTC),
        (evidence.id,),
    )
    scores = score_matrix(1.6, 1.1, -0.08)
    assessment = Assessment(
        (0.8, 0.9, 0.5, 0.8, 0.5, 0.8, 0.7, 0.8, 0.8, 0),
        False,
        False,
        (),
        ("固定测试输入下主队进球均值较高",),
        ("仅为测试，不是实战证据",),
        ("未校准模型最高 C；官方首发不是硬门槛",),
    )
    candidates = []
    odds = tuple(map(Decimal, ("2.10", "3.40", "3.60")))
    for direction, current, market_p in zip(
        ("home", "draw", "away"), odds, devig(odds), strict=True
    ):
        quote = Quote(
            Market.RESULT,
            direction,
            None,
            str(current),
            "EU",
            current,
            evidence.id,
            "TEST",
            "regular_time",
        )
        candidates.append(recommend(fixture.id, quote, price(quote, scores, market_p), assessment))
    quote = Quote(
        Market.HANDICAP,
        "home",
        Decimal("-.25"),
        ".92",
        "HK",
        Decimal("1.92"),
        evidence.id,
        "TEST",
        "regular_time",
    )
    market_p = devig((Decimal("1.92"), Decimal("1.94")))[0]
    candidates.append(recommend(fixture.id, quote, price(quote, scores, market_p), assessment))
    match = MatchAnalysis(
        fixture,
        tuple(candidates),
        ("这是可复现链路验收，不是真实比赛分析。",),
        ("角球、罚牌未在此测试样例提供",),
        (),
        1.6,
        1.1,
        scores.common(),
    )
    return Report(
        Mode.TEST,
        start,
        datetime(2030, 1, 1, 22, tzinfo=UTC),
        start,
        (evidence,),
        (match,),
        ("覆盖1场合成赛事；不得混入真实报告。",),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Football Quant V7")
    parser.add_argument("command", choices=("demo", "analyze"))
    parser.add_argument("--output", type=Path, default=Path("outputs/m1-test.docx"))
    parser.add_argument("--input", type=Path)
    parser.add_argument("--generated-at", help="Explicit aware time for deterministic reruns")
    args = parser.parse_args()
    if args.command == "demo":
        report = demo()
    else:
        if args.input is None:
            parser.error("analyze requires --input")
        research = load_research(args.input)
        if args.generated_at:
            from football_quant.acquisition.imports import timestamp

            research = replace(research, generated=timestamp(args.generated_at))
        elif research.mode is Mode.LIVE:
            research = replace(research, generated=datetime.now(UTC))
        report = Report(
            research.mode,
            research.started,
            research.deadline,
            research.generated,
            research.evidence,
            tuple(analyze_match(m, research) for m in research.matches),
            research.coverage,
        )
    save_report(report, args.output.with_suffix(".json"))
    write_report(report, args.output)
    print(summary(report))


if __name__ == "__main__":
    main()
