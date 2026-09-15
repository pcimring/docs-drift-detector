import sys
from pathlib import Path

from dotenv import load_dotenv

from discovery.catalog import upsert_catalog_entries
from discovery.config import load_target
from discovery.db import get_connection
from discovery.extract import extract_code_blocks
from discovery.filter import is_runnable_candidate


def discover(target_name: str, docs_repo_path: Path, conn) -> dict:
    docs_root = Path(docs_repo_path)
    if not docs_root.is_dir():
        # rglob() on a missing directory yields nothing instead of raising,
        # which would let a broken checkout report a successful empty run.
        raise NotADirectoryError(
            f"Docs repo path does not exist or is not a directory: {docs_root}"
        )
    target = load_target(target_name)
    summary = {"pages_scanned": 0, "candidates_found": 0, "pages_skipped": 0}
    for doc_path in sorted(docs_root.rglob("*.mdx")):
        try:
            text = doc_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            # One unreadable file must not discard the whole run's progress.
            summary["pages_skipped"] += 1
            continue
        blocks = extract_code_blocks(text, target.language)
        candidates = [b.code for b in blocks if is_runnable_candidate(b.code)]
        summary["pages_scanned"] += 1
        doc_page = str(doc_path.relative_to(docs_root))
        # Called even when the page has no candidates, so that a page which
        # lost its last snippet upstream gets its stale rows pruned too.
        upsert_catalog_entries(conn, target.name, doc_page, candidates)
        summary["candidates_found"] += len(candidates)
    return summary


def main():
    load_dotenv()
    if len(sys.argv) != 3:
        print("Usage: python -m discovery.main <target_name> <docs_repo_path>")
        sys.exit(1)
    target_name, docs_repo_path = sys.argv[1], Path(sys.argv[2])
    conn = get_connection()
    try:
        summary = discover(target_name, docs_repo_path, conn)
    finally:
        conn.close()
    print(
        f"Scanned {summary['pages_scanned']} pages "
        f"({summary['pages_skipped']} skipped), "
        f"found {summary['candidates_found']} runnable candidates."
    )
    if summary["pages_scanned"] == 0:
        print(
            f"No pages were scanned under {docs_repo_path}. The docs checkout is "
            "probably empty or wrong, so this run is failing.",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
