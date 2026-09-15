from discovery.catalog import upsert_catalog_entries

from checkapi.catalog_reader import get_page_group


def test_get_page_group_returns_all_rows_for_group(db_conn):
    page_group_id = upsert_catalog_entries(
        db_conn, "langchain", "docs/quickstart.mdx", ["print('a')", "print('b')"]
    )

    rows = get_page_group(db_conn, page_group_id)

    assert len(rows) == 2
    assert {row.snippet_text for row in rows} == {"print('a')", "print('b')"}
    assert all(row.doc_page == "docs/quickstart.mdx" for row in rows)


def test_get_page_group_returns_empty_for_unknown_group(db_conn):
    assert get_page_group(db_conn, "nonexistent-group") == []
