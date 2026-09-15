import hashlib


def make_snippet_id(doc_page: str, snippet_text: str) -> str:
    """Build a content-addressed identifier for one snippet on one page.

    The id hashes the snippet body rather than its position on the page, so a
    snippet keeps the same id when unrelated snippets around it are inserted,
    removed or reordered upstream. Positional ids silently re-pointed at
    different code whenever a page was edited.
    """
    digest = hashlib.sha256(snippet_text.encode("utf-8")).hexdigest()[:12]
    return f"{doc_page}#{digest}"


def upsert_catalog_entries(conn, target_project: str, doc_page: str, snippets: list[str]) -> str:
    """Write this run's snippets for one page, then prune the page's stale rows.

    Everything below runs in a single transaction (one commit at the end), so a
    page is never left half-pruned. Pruning is scoped to this exact
    (target_project, doc_page) — other pages and other targets are untouched.
    """
    page_group_id = hashlib.sha256(f"{target_project}:{doc_page}".encode()).hexdigest()[:16]
    current_snippet_ids = []
    with conn.cursor() as cur:
        for snippet_text in snippets:
            snippet_id = make_snippet_id(doc_page, snippet_text)
            current_snippet_ids.append(snippet_id)
            cur.execute(
                """
                INSERT INTO catalog_entry
                    (target_project, doc_page, snippet_id, snippet_text, page_group_id)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (target_project, doc_page, snippet_id)
                DO UPDATE SET snippet_text = EXCLUDED.snippet_text
                """,
                (target_project, doc_page, snippet_id, snippet_text, page_group_id),
            )
        # Drop rows for snippets that no longer exist on this page upstream.
        # The ::text[] cast keeps this valid when the page has no snippets at
        # all, in which case every row for the page is pruned.
        cur.execute(
            """
            DELETE FROM catalog_entry
            WHERE target_project = %s
              AND doc_page = %s
              AND NOT (snippet_id = ANY(%s::text[]))
            """,
            (target_project, doc_page, current_snippet_ids),
        )
    conn.commit()
    return page_group_id
