import sys
from pathlib import Path

from discovery.catalog import upsert_catalog_entries
from discovery.config import load_target
from discovery.db import get_connection
from discovery.extract import extract_code_blocks
from discovery.filter import is_runnable_candidate


def discover(target_name: str, docs_repo_path: Path, conn) -> dict:
    target = load_target(target_name)
    summary = {"pages_scanned": 0, "candidates_found": 0}
    for doc_path in sorted(Path(docs_repo_path).rglob("*.mdx")):
        text = doc_path.read_text(encoding="utf-8")
        blocks = extract_code_blocks(text, target.language)
        candidates = [b.code for b in blocks if is_runnable_candidate(b.code)]
        summary["pages_scanned"] += 1
        if not candidates:
            continue
        doc_page = str(doc_path.relative_to(docs_repo_path))
        upsert_catalog_entries(conn, target.name, doc_page, candidates)
        summary["candidates_found"] += len(candidates)
    return summary


def main():
    if len(sys.argv) != 3:
        print("Usage: python -m discovery.main <target_name> <docs_repo_path>")
        sys.exit(1)
    target_name, docs_repo_path = sys.argv[1], Path(sys.argv[2])
    conn = get_connection()
    try:
        summary = discover(target_name, docs_repo_path, conn)
        print(
            f"Scanned {summary['pages_scanned']} pages, "
            f"found {summary['candidates_found']} runnable candidates."
        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
