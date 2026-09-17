from pathlib import Path

EM_DASH = "—"
EXCLUDED_DIRS = {".venv", ".git", "node_modules", ".pytest_cache", "__pycache__", ".superpowers"}
EXCLUDED_FILES = {"test_no_em_dashes.py"}
TEXT_SUFFIXES = {
    ".py", ".md", ".sql", ".yml", ".yaml", ".toml", ".txt", ".json", ".cfg", ".ini", ".example",
}


def _repo_text_files(repo_root: Path):
    for path in repo_root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue
        if path.name in EXCLUDED_FILES:
            continue
        if path.suffix in TEXT_SUFFIXES or path.name.startswith(".env"):
            yield path


def test_repo_contains_no_em_dash():
    repo_root = Path(__file__).resolve().parent.parent
    offenders = []
    for path in _repo_text_files(repo_root):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if EM_DASH in text:
            offenders.append(str(path.relative_to(repo_root)))

    assert not offenders, f"em dash found in: {offenders}"
