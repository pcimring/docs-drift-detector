import re

_PATTERNS = [
    r"NameError: name '(\w+)' is not defined",
    r"has no attribute '(\w+)'",
    r"No module named '([\w.]+)'",
]


def extract_broken_identifier(error_text: str | None) -> str | None:
    if not error_text:
        return None
    for pattern in _PATTERNS:
        match = re.search(pattern, error_text)
        if match:
            return match.group(1)
    return None


def find_flagged_locations(page_text: str, identifier: str | None, exclude_block: str) -> list[dict]:
    if not identifier:
        return []
    excluded_lines = {line.strip() for line in exclude_block.strip().splitlines()}
    pattern = re.compile(rf"\b{re.escape(identifier)}\b")
    flagged = []
    for line_no, line in enumerate(page_text.splitlines(), start=1):
        stripped = line.strip()
        if stripped in excluded_lines:
            continue
        if pattern.search(line):
            flagged.append({"line": line_no, "text": stripped})
    return flagged
