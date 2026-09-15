from discovery.main import discover


def test_discover_scans_pages_and_populates_catalog(tmp_path, db_conn):
    docs_repo = tmp_path / "docs"
    docs_repo.mkdir()
    (docs_repo / "quickstart.mdx").write_text(
        "# Quickstart\n\n"
        "```python\n"
        "from langchain_openai import ChatOpenAI\n\n"
        "llm = ChatOpenAI(model='gpt-4o-mini')\n"
        "print(llm.invoke('hi').content)\n"
        "```\n"
    )
    (docs_repo / "concepts.mdx").write_text("# Concepts\n\nJust prose, no code.\n")

    summary = discover("langchain", docs_repo, db_conn)

    assert summary["pages_scanned"] == 2
    assert summary["candidates_found"] == 1

    with db_conn.cursor() as cur:
        cur.execute("SELECT doc_page FROM catalog_entry")
        rows = cur.fetchall()
    assert rows == [("quickstart.mdx",)]
