import json
from pathlib import Path
from typing import Optional

from .paths import CONFIG_DIR, CONFIG_PATH

# config.json only ever stores repo/clone-path metadata, never key material —
# that's what makes it safe to copy to a fresh device and bulk-regenerate.
_DEFAULT = {"repos": {}}


def load() -> dict:
    if not CONFIG_PATH.exists():
        return dict(_DEFAULT)
    return json.loads(CONFIG_PATH.read_text())


def save(config: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2) + "\n")


def add_repo(repo: str, clone_path: Path) -> None:
    config = load()
    config["repos"][repo] = {"clone_path": str(clone_path)}
    save(config)


def remove_repo(repo: str) -> None:
    config = load()
    config["repos"].pop(repo, None)
    save(config)


def get_repo(repo: str) -> Optional[dict]:
    return load()["repos"].get(repo)


def all_repos() -> dict:
    return load()["repos"]
