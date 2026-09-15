from dataclasses import dataclass
from pathlib import Path

import yaml

DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config" / "targets.yaml"


@dataclass
class TargetConfig:
    name: str
    docs_repo: str
    code_repo: str
    language: str


def load_target(name: str, config_path: Path = DEFAULT_CONFIG_PATH) -> TargetConfig:
    with open(config_path) as f:
        all_targets = yaml.safe_load(f)
    if name not in all_targets:
        raise KeyError(f"Unknown target: {name}")
    entry = all_targets[name]
    return TargetConfig(
        name=name,
        docs_repo=entry["docs_repo"],
        code_repo=entry["code_repo"],
        language=entry["language"],
    )
