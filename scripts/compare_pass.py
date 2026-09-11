"""Deterministic counterfactuals on the same existing synthetic research package."""

import json
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

from football_quant.acquisition.package import load_research
from football_quant.decisions.analysis import analyze_match
from football_quant.domain import Market
from football_quant.evidence.research import Research
from football_quant.evidence.verification import Claim


def cases() -> dict[str, Research]:
    research = load_research(Path("fixtures/research-test/manifest.json"))
    match = research.matches[0]
    q = next(q for q in match.quotes if q.market is Market.RESULT)
    single = replace(match, quotes=(q,))
    data = json.loads(match.data)
    data.pop("corners", None)
    data.pop("cards", None)
    incompatible = json.loads(match.data)
    incompatible["baseline"]["same_basis"] = False
    variants = {
        "complete": match,
        "single": single,
        "no_odds": replace(match, quotes=()),
        "no_history": replace(single, data="{}"),
        "unsupported_model": replace(single, data=json.dumps(incompatible)),
        "no_auxiliary": replace(match, data=json.dumps(data)),
        "unsupported_rules": replace(single, quotes=(replace(q, rules="extra_time"),)),
        "negative_ev": replace(
            single, quotes=(replace(q, original_value="1.01", decimal_odds=Decimal("1.01")),)
        ),
        "identity_conflict": replace(
            single,
            claims=match.claims
            + (Claim("kickoff", "first", "e1"), Claim("kickoff", "second", "e1")),
        ),
    }
    return {name: replace(research, matches=(m,)) for name, m in variants.items()}


def measure(research: Research) -> dict[str, object]:
    result = analyze_match(research.matches[0], research)
    return {
        "lambda": [result.lambda_home, result.lambda_away],
        "missing": result.missing,
        "conflicts": result.conflicts,
        "candidates": [
            {
                "market": c.quote.market.value,
                "selection": c.quote.selection,
                "grade": c.grade.value,
                "ev": str(c.price.ev) if c.price else None,
                "devig": c.price.devig_probability if c.price else None,
                "reasons": c.reasons,
            }
            for c in result.candidates
        ],
    }


if __name__ == "__main__":
    print(
        json.dumps({name: measure(r) for name, r in cases().items()}, ensure_ascii=False, indent=2)
    )
