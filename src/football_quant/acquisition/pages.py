"""Offline extraction from lawfully saved public page content; no HTTP client."""

import csv
import io
import json
from html.parser import HTMLParser
from urllib.parse import urlsplit


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[tuple[str, ...]] = []
        self.text: list[str] = []
        self.json_ld: list[str] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None
        self._script: list[str] | None = None
        self._hidden = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "script":
            self._hidden += 1
            if dict(attrs).get("type") == "application/ld+json":
                self._script = []
        if tag == "style":
            self._hidden += 1
        if tag == "tr":
            self._row = []
        if tag in ("td", "th"):
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._script is not None:
            self._script.append(data)
        if self._hidden:
            return
        if self._cell is not None:
            self._cell.append(data)
        if data.strip():
            self.text.append(data.strip())

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._script is not None:
            self.json_ld.append("".join(self._script))
            self._script = None
        if tag in ("script", "style"):
            self._hidden = max(0, self._hidden - 1)
        if tag in ("td", "th") and self._cell is not None:
            if self._row is not None:
                self._row.append(" ".join(self._cell).strip())
            self._cell = None
        if tag == "tr" and self._row is not None:
            self.tables.append(tuple(self._row))
            self._row = None


def public_url(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("public page URL required")
    if parsed.username or parsed.password:
        raise ValueError("credentials forbidden")
    hostname = parsed.hostname.lower()
    if hostname == "localhost" or hostname.startswith(("127.", "10.", "192.168.")):
        raise ValueError("public page required")
    segments = parsed.path.lower().split("/")
    if "api" in segments or hostname.startswith("api.") or "graphql" in segments:
        raise ValueError("data interface URLs forbidden")
    if any(key in parsed.query.lower() for key in ("token=", "key=", "password=", "auth=")):
        raise ValueError("credential-bearing URL forbidden")
    return url


def extract(content: str, extension: str) -> dict[str, object]:
    if extension == ".html":
        parser = PageParser()
        parser.feed(content)
        return {
            "text": "\n".join(parser.text),
            "rows": parser.tables,
            "json_ld": [json.loads(s) for s in parser.json_ld],
        }
    if extension == ".csv":
        return {"rows": list(csv.DictReader(io.StringIO(content)))}
    if extension == ".txt":
        return {"text": content}
    if extension == ".jsonld":
        return {"json_ld": [json.loads(content)]}
    raise ValueError("only saved HTML, text, CSV and JSON-LD are accepted")
