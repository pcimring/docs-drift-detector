import json
import logging
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

from discovery.db import get_connection

from checkapi.handler_logic import build_response

DEFAULT_TARGET = "langchain"


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        page_group_id = params.get("page_group_id", [None])[0]
        target_name = params.get("target", [DEFAULT_TARGET])[0]

        if not page_group_id:
            self._respond(400, {"error": "page_group_id is required"})
            return

        forwarded_for = self.headers.get("x-forwarded-for")
        client_ip = forwarded_for.split(",")[0].strip() if forwarded_for else self.client_address[0]

        conn = None
        try:
            conn = get_connection()
            status_code, body = build_response(conn, target_name, page_group_id, client_ip)
        except Exception:
            logging.getLogger(__name__).exception(
                "Unhandled error in check endpoint (page_group_id=%s, target=%s)",
                page_group_id,
                target_name,
            )
            status_code, body = 500, {"error": "internal_error"}
        finally:
            if conn is not None:
                conn.close()

        self._respond(status_code, body)

    def _respond(self, status_code: int, body: dict) -> None:
        payload = json.dumps(body).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)
