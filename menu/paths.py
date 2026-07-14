from pathlib import Path

HOME = Path.home()

KEYS_DIR = HOME / ".ssh" / "deploy-keys"
AGENT_ENV_PATH = KEYS_DIR / ".agent-env"

CONFIG_DIR = HOME / ".ssh-keygen-controller"
CONFIG_PATH = CONFIG_DIR / "config.json"

DEFAULT_CLONE_ROOT = HOME / "repos"
