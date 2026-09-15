import pytest

from discovery.main import discover

VALID_PAGE = (
    "# Quickstart\n\n"
    "```python\n"
    "from langchain_openai import ChatOpenAI\n\n"
    "llm = ChatOpenAI(model='gpt-4o-mini')\n"
    "print(llm.invoke('hi').content)\n"
    "```\n"
)


def test_discover_scans_pages_and_populates_catalog(tmp_path, db_conn):
    docs_repo = tmp_path / "docs"
    docs_repo.mkdir()
    (docs_repo / "quickstart.mdx").write_text(VALID_PAGE)
    (docs_repo / "concepts.mdx").write_text("# Concepts\n\nJust prose, no code.\n")

    summary = discover("langchain", docs_repo, db_conn)

    assert summary["pages_scanned"] == 2
    assert summary["candidates_found"] == 1
    assert summary["pages_skipped"] == 0

    with db_conn.cursor() as cur:
        cur.execute("SELECT doc_page FROM catalog_entry")
        rows = cur.fetchall()
    assert rows == [("quickstart.mdx",)]


def test_discover_skips_undecodable_page_and_keeps_going(tmp_path, db_conn):
    docs_repo = tmp_path / "docs"
    docs_repo.mkdir()
    (docs_repo / "quickstart.mdx").write_text(VALID_PAGE)
    # Invalid UTF-8: a lone continuation byte cannot start a sequence.
    (docs_repo / "broken.mdx").write_bytes(b"# Broken\n\n\xff\xfe not utf-8\n")

    summary = discover("langchain", docs_repo, db_conn)

    assert summary["pages_skipped"] == 1
    assert summary["pages_scanned"] == 1
    assert summary["candidates_found"] == 1

    with db_conn.cursor() as cur:
        cur.execute("SELECT doc_page FROM catalog_entry")
        rows = cur.fetchall()
    assert rows == [("quickstart.mdx",)]


def test_discover_raises_when_docs_path_is_missing(tmp_path, db_conn):
    missing = tmp_path / "no-such-checkout"
    with pytest.raises(NotADirectoryError, match="does not exist or is not a directory"):
        discover("langchain", missing, db_conn)


def test_discover_raises_when_docs_path_is_a_file(tmp_path, db_conn):
    not_a_dir = tmp_path / "docs.mdx"
    not_a_dir.write_text(VALID_PAGE)
    with pytest.raises(NotADirectoryError):
        discover("langchain", not_a_dir, db_conn)
