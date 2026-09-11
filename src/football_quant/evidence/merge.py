"""Merge duplicate discoveries while preserving contradictory kickoff/history claims."""

from dataclasses import replace

from football_quant.evidence.research import ResearchMatch
from football_quant.evidence.verification import Claim


def merge_matches(matches: tuple[ResearchMatch, ...]) -> tuple[ResearchMatch, ...]:
    result: dict[tuple[str, str, str, str], ResearchMatch] = {}
    ids: dict[str, tuple[str, str, str, str]] = {}
    for match in matches:
        f = match.fixture
        key = (
            f.home.casefold().strip(),
            f.away.casefold().strip(),
            f.competition.casefold().strip(),
            f.kickoff.date().isoformat(),
        )
        if f.id in ids and ids[f.id] != key:
            raise ValueError("same fixture ID has incompatible identities")
        ids[f.id] = key
        if key not in result:
            result[key] = match
            continue
        old = result[key]
        claims = old.claims + match.claims
        if old.fixture.kickoff != f.kickoff:
            claims += (
                Claim("kickoff", old.fixture.kickoff.isoformat(), old.fixture.evidence_ids[0]),
                Claim("kickoff", f.kickoff.isoformat(), f.evidence_ids[0]),
            )
        if old.data != match.data:
            claims += (
                Claim("history", old.data, old.fixture.evidence_ids[0]),
                Claim("history", match.data, f.evidence_ids[0]),
            )
        fixture = replace(
            old.fixture, evidence_ids=tuple(sorted(set(old.fixture.evidence_ids + f.evidence_ids)))
        )
        result[key] = replace(
            old,
            fixture=fixture,
            quotes=tuple(dict.fromkeys(old.quotes + match.quotes)),
            claims=tuple(dict.fromkeys(claims)),
            notes=old.notes + match.notes,
            missing=tuple(dict.fromkeys(old.missing + match.missing)),
        )
    return tuple(sorted(result.values(), key=lambda m: (m.fixture.kickoff, m.fixture.id)))
