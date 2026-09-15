import difflib
import re
from dataclasses import dataclass
from typing import Callable, Optional

from checkapi.sandbox import ExecutionResult

MODEL_NAME = "claude-sonnet-5"
MAX_RETRIES = 1

_CODE_FENCE_PATTERN = re.compile(r"```(?:python)?\n(.*?)```", re.DOTALL)


@dataclass
class FixResult:
    verified: bool
    diff: Optional[str]


def _extract_code(response_text: str) -> str:
    match = _CODE_FENCE_PATTERN.search(response_text)
    return match.group(1).strip() if match else response_text.strip()


def _build_prompt(doc_text: str, error_text: str, source_code: str) -> str:
    return (
        "The following Python code snippet from a documentation page failed "
        "when executed against the current SDK.\n\n"
        f"Doc page text:\n{doc_text}\n\n"
        f"Snippet:\n```python\n{source_code}\n```\n\n"
        f"Error:\n{error_text}\n\n"
        "Return ONLY the corrected, complete, self-contained snippet as a "
        "single python code block, no explanation."
    )


def draft_and_verify_fix(
    doc_text: str,
    error_text: str,
    source_code: str,
    execute_fn: Callable[[str], ExecutionResult],
    llm_client=None,
) -> FixResult:
    if llm_client is None:
        import anthropic

        llm_client = anthropic.Anthropic()

    prompt = _build_prompt(doc_text, error_text, source_code)
    response = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = llm_client.messages.create(
                model=MODEL_NAME,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            break
        except Exception:
            if attempt == MAX_RETRIES:
                return FixResult(verified=False, diff=None)

    try:
        fixed_code = _extract_code(response.content[0].text)
        result = execute_fn(fixed_code)
        if result.status != "pass":
            return FixResult(verified=False, diff=None)

        diff_text = "".join(
            difflib.unified_diff(
                source_code.splitlines(keepends=True),
                fixed_code.splitlines(keepends=True),
                fromfile="original",
                tofile="fixed",
            )
        )
        return FixResult(verified=True, diff=diff_text)
    except Exception:
        return FixResult(verified=False, diff=None)
