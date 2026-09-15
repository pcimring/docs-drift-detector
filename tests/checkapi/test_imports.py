from checkapi.imports import resolve_packages


def test_resolves_langchain_ecosystem_overrides():
    code = "from langchain_openai import ChatOpenAI\nimport langchain_core.messages\n"
    assert resolve_packages(code) == ["langchain-core", "langchain-openai"]


def test_skips_stdlib_modules():
    code = "import json\nimport os\nfrom pathlib import Path\n"
    assert resolve_packages(code) == []


def test_falls_back_to_hyphenated_module_name():
    code = "import numpy\n"
    assert resolve_packages(code) == ["numpy"]


def test_deduplicates_repeated_imports():
    code = "import numpy\nimport numpy as np\n"
    assert resolve_packages(code) == ["numpy"]
