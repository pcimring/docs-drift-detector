from dataclasses import dataclass


@dataclass
class CatalogRow:
    snippet_id: str
    doc_page: str
    snippet_text: str


def get_page_group(conn, page_group_id: str) -> list[CatalogRow]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT snippet_id, doc_page, snippet_text FROM catalog_entry "
            "WHERE page_group_id = %s ORDER BY id",
            (page_group_id,),
        )
        rows = cur.fetchall()
    return [CatalogRow(snippet_id=r[0], doc_page=r[1], snippet_text=r[2]) for r in rows]
