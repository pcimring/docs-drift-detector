import os

RATE_LIMIT_MAX_REQUESTS = int(os.environ.get("RATE_LIMIT_MAX_PER_HOUR", "20"))


def is_rate_limited(conn, ip_address: str, max_requests: int | None = None) -> bool:
    limit = RATE_LIMIT_MAX_REQUESTS if max_requests is None else max_requests
    with conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM rate_limit_event "
            "WHERE ip_address = %s AND created_at > now() - interval '60 minutes'",
            (ip_address,),
        )
        count = cur.fetchone()[0]
    return count >= limit


def record_request(conn, ip_address: str) -> None:
    with conn.cursor() as cur:
        cur.execute("INSERT INTO rate_limit_event (ip_address) VALUES (%s)", (ip_address,))
    conn.commit()
