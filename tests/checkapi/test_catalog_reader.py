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


def test_get_page_group_returns_rows_in_page_order_not_digest_order(db_conn):
    # These three snippets' content-addressed ids sort as two, three, one, so a
    # digest-ordered query would not return them in the order they appear on the
    # page.
    snippets = ["print('one')", "print('two')", "print('three')"]
    page_group_id = upsert_catalog_entries(db_conn, "langchain", "docs/quickstart.mdx", snippets)

    rows = get_page_group(db_conn, page_group_id)

    assert [row.snippet_text for row in rows] == snippets
    assert sorted(row.snippet_id for row in rows) != [row.snippet_id for row in rows]


def test_get_page_group_returns_empty_for_unknown_group(db_conn):
    assert get_page_group(db_conn, "nonexistent-group") == []
