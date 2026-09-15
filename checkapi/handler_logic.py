from checkapi import orchestrator, rate_limit


def build_response(conn, target_name: str, page_group_id: str, client_ip: str) -> tuple[int, dict]:
    if rate_limit.is_rate_limited(conn, client_ip):
        return 429, {"error": "rate_limited"}
    rate_limit.record_request(conn, client_ip)
    summary = orchestrator.check_page(conn, target_name, page_group_id)
    return 200, summary
