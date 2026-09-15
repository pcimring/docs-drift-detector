import hashlib


def make_snippet_id(doc_page: str, index: int) -> str:
    return f"{doc_page}#{index}"


def upsert_catalog_entries(conn, target_project: str, doc_page: str, snippets: list[str]) -> str:
    page_group_id = hashlib.sha256(f"{target_project}:{doc_page}".encode()).hexdigest()[:16]
    with conn.cursor() as cur:
        for index, snippet_text in enumerate(snippets):
            snippet_id = make_snippet_id(doc_page, index)
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
    conn.commit()
    return page_group_id
