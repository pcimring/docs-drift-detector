import os

import requests

GITHUB_API_BASE = "https://api.github.com"


def fetch_page_text(repo: str, path: str) -> str:
    url = f"{GITHUB_API_BASE}/repos/{repo}/contents/{path}"
    headers = {"Accept": "application/vnd.github.raw+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    return response.text
