from discovery.catalog import upsert_catalog_entries


def test_upsert_creates_rows(db_conn):
    page_group_id = upsert_catalog_entries(
        db_conn, "langchain", "docs/quickstart.mdx", ["print('a')", "print('b')"]
    )
    with db_conn.cursor() as cur:
        # Order by the serial primary key: snippet ids are content hashes now,
        # so they do not sort in insertion order.
        cur.execute(
            "SELECT snippet_id, snippet_text, page_group_id FROM catalog_entry "
            "WHERE target_project = %s AND doc_page = %s ORDER BY id",
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


def test_snippet_id_is_stable_when_other_snippets_shift(db_conn):
    upsert_catalog_entries(db_conn, "langchain", "docs/quickstart.mdx", ["print('b')"])
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT snippet_id FROM catalog_entry WHERE snippet_text = %s", ("print('b')",)
        )
        original_id = cur.fetchone()[0]

    # An upstream edit inserts a new snippet ahead of the existing one.
    upsert_catalog_entries(
        db_conn, "langchain", "docs/quickstart.mdx", ["print('a')", "print('b')"]
    )
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT snippet_id FROM catalog_entry WHERE snippet_text = %s", ("print('b')",)
        )
        rows = cur.fetchall()
    assert len(rows) == 1
    assert rows[0][0] == original_id


def test_upsert_prunes_snippets_removed_upstream(db_conn):
    upsert_catalog_entries(
        db_conn, "langchain", "docs/quickstart.mdx", ["print('a')", "print('b')", "print('c')"]
    )
    # Upstream edit removes the first snippet from the page.
    upsert_catalog_entries(
        db_conn, "langchain", "docs/quickstart.mdx", ["print('b')", "print('c')"]
    )
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT snippet_text FROM catalog_entry "
            "WHERE target_project = %s AND doc_page = %s",
            ("langchain", "docs/quickstart.mdx"),
        )
        rows = cur.fetchall()
    assert len(rows) == 2
    assert {row[0] for row in rows} == {"print('b')", "print('c')"}


def test_pruning_is_scoped_to_one_page(db_conn):
    upsert_catalog_entries(db_conn, "langchain", "docs/other.mdx", ["print('x')", "print('y')"])
    upsert_catalog_entries(db_conn, "langchain", "docs/quickstart.mdx", ["print('a')"])
    # Re-run the quickstart page with entirely different content: the other
    # page's rows must survive.
    upsert_catalog_entries(db_conn, "langchain", "docs/quickstart.mdx", ["print('z')"])
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT snippet_text FROM catalog_entry "
            "WHERE target_project = %s AND doc_page = %s",
            ("langchain", "docs/other.mdx"),
        )
        other_rows = {row[0] for row in cur.fetchall()}
    assert other_rows == {"print('x')", "print('y')"}


def test_pruning_is_scoped_to_one_target_project(db_conn):
    upsert_catalog_entries(db_conn, "phoenix", "docs/quickstart.mdx", ["print('a')"])
    upsert_catalog_entries(db_conn, "langchain", "docs/quickstart.mdx", ["print('b')"])
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT snippet_text FROM catalog_entry WHERE target_project = %s", ("phoenix",)
        )
        rows = [row[0] for row in cur.fetchall()]
    assert rows == ["print('a')"]


def test_upsert_with_no_snippets_clears_the_page(db_conn):
    upsert_catalog_entries(db_conn, "langchain", "docs/quickstart.mdx", ["print('a')"])
    upsert_catalog_entries(db_conn, "langchain", "docs/quickstart.mdx", [])
    with db_conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM catalog_entry")
        assert cur.fetchone()[0] == 0
