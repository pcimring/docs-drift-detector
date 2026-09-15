from discovery.catalog import upsert_catalog_entries


def test_upsert_creates_rows(db_conn):
    page_group_id = upsert_catalog_entries(
        db_conn, "langchain", "docs/quickstart.mdx", ["print('a')", "print('b')"]
    )
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT snippet_id, snippet_text, page_group_id FROM catalog_entry "
            "WHERE target_project = %s AND doc_page = %s ORDER BY snippet_id",
            ("langchain", "docs/quickstart.mdx"),
        )
        rows = cur.fetchall()
    assert len(rows) == 2
    assert rows[0][1] == "print('a')"
    assert rows[0][2] == page_group_id


def test_upsert_updates_existing_snippet(db_conn):
    upsert_catalog_entries(db_conn, "langchain", "docs/quickstart.mdx", ["print('old')"])
    upsert_catalog_entries(db_conn, "langchain", "docs/quickstart.mdx", ["print('new')"])
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT snippet_text FROM catalog_entry "
            "WHERE target_project = %s AND doc_page = %s",
            ("langchain", "docs/quickstart.mdx"),
        )
        rows = cur.fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "print('new')"
