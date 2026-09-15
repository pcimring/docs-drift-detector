from pathlib import Path

from discovery.extract import extract_code_blocks

FIXTURE = Path(__file__).parent.parent / "fixtures" / "sample_page.mdx"


def test_extract_python_blocks_only():
    text = FIXTURE.read_text()
    blocks = extract_code_blocks(text, "python")
    assert len(blocks) == 2
    assert all(b.language == "python" for b in blocks)


def test_extract_returns_empty_for_missing_language():
    text = FIXTURE.read_text()
    blocks = extract_code_blocks(text, "ruby")
    assert blocks == []
