from pathlib import Path

from discovery.main import discover

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "langchain_docs_sample"


def test_discover_against_pinned_langchain_sample(db_conn):
    summary = discover("langchain", FIXTURE_DIR, db_conn)

    assert summary["pages_scanned"] == 2
    assert summary["candidates_found"] == 2

    with db_conn.cursor() as cur:
        cur.execute("SELECT doc_page FROM catalog_entry ORDER BY doc_page")
        rows = [row[0] for row in cur.fetchall()]
    assert rows == ["chat_models.mdx", "quickstart.mdx"]
