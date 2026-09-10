from pathlib import Path
from zipfile import ZipFile

from football_quant.application import demo
from football_quant.reporting.word import summary, write_report


def test_word_contents_sources_and_consistency(tmp_path: Path) -> None:
    report = demo()
    path = tmp_path / "test.docx"
    write_report(report, path)
    with ZipFile(path) as z:
        xml = z.read("word/document.xml").decode()
        rels = z.read("word/_rels/document.xml.rels").decode()
    assert summary(report) in xml
    assert "足球量化分析测试报告" in xml
    assert "https://example.com/test-fixture" in rels
    for candidate in report.matches[0].candidates:
        assert f"{candidate.price.ev:+.2%}" in xml
    assert "w:tblHeader" in xml
