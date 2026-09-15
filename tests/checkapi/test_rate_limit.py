from checkapi.rate_limit import is_rate_limited, record_request


def test_ip_under_limit_is_not_rate_limited(db_conn):
    record_request(db_conn, "1.2.3.4")
    record_request(db_conn, "1.2.3.4")
    assert is_rate_limited(db_conn, "1.2.3.4", max_requests=3) is False


def test_ip_at_limit_is_rate_limited(db_conn):
    for _ in range(3):
        record_request(db_conn, "1.2.3.4")
    assert is_rate_limited(db_conn, "1.2.3.4", max_requests=3) is True


def test_different_ips_are_tracked_independently(db_conn):
    for _ in range(3):
        record_request(db_conn, "1.2.3.4")
    assert is_rate_limited(db_conn, "5.6.7.8", max_requests=3) is False
