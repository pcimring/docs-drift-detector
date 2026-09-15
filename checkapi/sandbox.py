import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

EXECUTION_TIMEOUT_SECONDS = 30
INSTALL_TIMEOUT_SECONDS = 60

# Snippets executed here are doc-page code, and the fix-drafting path executes
# LLM output derived from third-party doc text. The child process therefore gets
# an explicit allowlist rather than a copy of the host environment, so the
# tool's own credentials (DATABASE_URL, GITHUB_TOKEN, ...) are never visible to
# it. Provider keys stay on the list because some doc snippets legitimately call
# those providers directly.
_PASSTHROUGH_ENV_VARS = (
    "PATH",
    "HOME",
    "LANG",
    "LC_ALL",
    "TMPDIR",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
)

TRANSIENT_ERROR_PATTERN = re.compile(
    r"RateLimitError|Timeout|ConnectionError|APIConnectionError|"
    r"Service Unavailable|"
    r"(?:Status|Code|Error)\s*:\s*5\d{2}|"
    r"5\d{2}\s+(?:Server Error|Internal Server Error|Bad Gateway|Service Unavailable|Gateway Timeout|Too Many Requests)|"
    r"(?:500|502|503|504|505)\s+(?:error|exception)|"
    r"HTTP\s+5\d{2}",
    re.IGNORECASE,
)


class HarnessError(Exception):
    """Raised when the harness itself (pip install, subprocess launch) fails,
    as opposed to the snippet under test failing on its own."""


@dataclass
class ExecutionResult:
    status: str  # "pass" | "fail" | "timeout"
    stdout: str
    stderr: str
    error_text: str | None


def install_packages(packages: list[str], target_dir: Path) -> None:
    if not packages:
        return
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--target", str(target_dir), *packages],
        capture_output=True,
        text=True,
        timeout=INSTALL_TIMEOUT_SECONDS,
    )
    if result.returncode != 0:
        raise HarnessError(f"pip install failed: {result.stderr[-2000:]}")


def execute_snippet(
    code: str,
    extra_sys_path: Path | None = None,
    env: dict | None = None,
    timeout: int = EXECUTION_TIMEOUT_SECONDS,
) -> ExecutionResult:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        script_path = f.name

    run_env = {key: os.environ[key] for key in _PASSTHROUGH_ENV_VARS if key in os.environ}
    if env:
        run_env.update(env)
    if extra_sys_path is not None:
        existing = run_env.get("PYTHONPATH", "")
        run_env["PYTHONPATH"] = (
            f"{extra_sys_path}{os.pathsep}{existing}" if existing else str(extra_sys_path)
        )

    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=run_env,
        )
    except subprocess.TimeoutExpired:
        return ExecutionResult(status="timeout", stdout="", stderr="", error_text="execution timed out")
    finally:
        Path(script_path).unlink(missing_ok=True)

    if result.returncode == 0:
        return ExecutionResult(status="pass", stdout=result.stdout, stderr="", error_text=None)
    return ExecutionResult(
        status="fail",
        stdout=result.stdout,
        stderr=result.stderr,
        error_text=result.stderr.strip()[-2000:],
    )


def is_transient_error(error_text: str | None) -> bool:
    if not error_text:
        return False
    return bool(TRANSIENT_ERROR_PATTERN.search(error_text))
