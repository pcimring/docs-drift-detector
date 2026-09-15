import pytest

from discovery.config import load_target


def test_load_target_returns_langchain_config():
    target = load_target("langchain")
    assert target.name == "langchain"
    assert target.docs_repo == "langchain-ai/docs"
    assert target.code_repo == "langchain-ai/langchain"
    assert target.language == "python"


def test_load_target_raises_for_unknown_name():
    with pytest.raises(KeyError):
        load_target("nonexistent")
