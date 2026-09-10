from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_formal_specifications_are_present() -> None:
    for name in ("product", "data-policy", "markets", "mathematics", "report", "architecture"):
        assert len((ROOT / "docs" / f"{name}.md").read_text()) > 200


def test_no_data_api_or_old_project_dependencies() -> None:
    forbidden = ("theoddsapi", "the-odds-api", "api.the-odds-api", "zuqiu", "requests", "httpx")
    for path in (ROOT / "src").rglob("*.py"):
        content = path.read_text().lower()
        assert not any(token in content for token in forbidden), path


def test_network_is_blocked() -> None:
    import socket

    with pytest.raises(AssertionError, match="Network is forbidden"):
        socket.create_connection(("example.com", 443))
