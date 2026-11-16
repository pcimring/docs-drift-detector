import json
import sys

from dotenv import load_dotenv

from checkapi.orchestrator import check_page
from discovery.db import get_connection


def main():
    load_dotenv()
    if len(sys.argv) != 3:
        print("Usage: python -m checkapi.main <target_name> <page_group_id>")
        sys.exit(1)
    target_name, page_group_id = sys.argv[1], sys.argv[2]
    conn = get_connection()
    try:
        summary = check_page(conn, target_name, page_group_id)
    finally:
        conn.close()
    print(json.dumps(summary))
    if summary["snippets_checked"] == 0:
        print(
            f"No samples found for page_group_id {page_group_id}.",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
