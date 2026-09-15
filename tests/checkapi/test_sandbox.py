import subprocess
from pathlib import Path

import pytest

from checkapi.sandbox import (
    HarnessError,
    execute_snippet,
    install_packages,
    is_transient_error,
)


def test_execute_snippet_pass():
    result = execute_snippet("print('hi')")
    assert result.status == "pass"
    assert "hi" in result.stdout
    assert result.error_text is None


def test_execute_snippet_fail_captures_error_text():
    result = execute_snippet("raise ValueError('boom')")
    assert result.status == "fail"
    assert "ValueError: boom" in result.error_text


def test_execute_snippet_timeout():
    result = execute_snippet("import time\ntime.sleep(2)", timeout=1)
    assert result.status == "timeout"


def test_install_packages_noop_for_empty_list(tmp_path):
    install_packages([], tmp_path)  # must not raise, must not shell out


def test_install_packages_calls_pip_with_target(monkeypatch, tmp_path):
    captured = {}

    def fake_run(cmd, capture_output, text, timeout):
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("checkapi.sandbox.subprocess.run", fake_run)

    install_packages(["numpy"], tmp_path)

    assert "--target" in captured["cmd"]
    assert str(tmp_path) in captured["cmd"]
    assert "numpy" in captured["cmd"]


def test_install_packages_raises_harness_error_on_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "checkapi.sandbox.subprocess.run",
        lambda cmd, capture_output, text, timeout: subprocess.CompletedProcess(
            cmd, returncode=1, stdout="", stderr="no matching distribution"
        ),
    )

    with pytest.raises(HarnessError):
        install_packages(["not-a-real-package"], tmp_path)


def test_is_transient_error_detects_provider_hiccups():
    assert is_transient_error("anthropic.RateLimitError: rate limit exceeded") is True
    assert is_transient_error("requests.exceptions.ConnectionError: reset") is True


def test_is_transient_error_detects_http_status_codes():
    # Real HTTP status codes with context should match
    assert is_transient_error("HTTP 503 Service Unavailable") is True
    assert is_transient_error("Status: 500 Internal Server Error") is True
    assert is_transient_error("502 Bad Gateway") is True
    assert is_transient_error("504 Gateway Timeout") is True


def test_is_transient_error_false_for_genuine_bugs():
    assert is_transient_error("ValueError: boom") is False
    assert is_transient_error(None) is False


def test_is_transient_error_rejects_coincidental_line_numbers():
    # A traceback with a line number like 512 should NOT match as transient
    traceback = """Traceback (most recent call last):
  File "adapters.py", line 512, in send
    raise ValueError("something went wrong")
ValueError: something went wrong"""
    assert is_transient_error(traceback) is False


def test_execute_snippet_with_extra_sys_path(tmp_path):
    # Create a simple module in tmp_path
    module_dir = tmp_path / "mymodule"
    module_dir.mkdir()
    (module_dir / "__init__.py").write_text("VALUE = 42")

    # Execute snippet that imports from the module
    code = """
import sys
from mymodule import VALUE
print(f"got {VALUE}")
"""
    result = execute_snippet(code, extra_sys_path=tmp_path)
    assert result.status == "pass"
    assert "got 42" in result.stdout


def test_execute_snippet_with_env(tmp_path):
    # Pass a custom env var and verify snippet can read it
    code = """
import os
val = os.environ.get("TEST_CUSTOM_VAR", "not_set")
print(f"env_value:{val}")
"""
    result = execute_snippet(code, env={"TEST_CUSTOM_VAR": "my_test_value"})
    assert result.status == "pass"
    assert "env_value:my_test_value" in result.stdout
