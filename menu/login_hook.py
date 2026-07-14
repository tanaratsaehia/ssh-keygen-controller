from pathlib import Path

from .paths import AGENT_ENV_PATH, KEYS_DIR

MARKER_START = "# >>> sshctl ssh-agent auto-load >>>"
MARKER_END = "# <<< sshctl ssh-agent auto-load <<<"

# Reuses one ssh-agent process across shell sessions (persisted via
# AGENT_ENV_PATH) instead of spawning a fresh one per terminal. rc=2 from
# `ssh-add -l` specifically means "can't reach an agent" — that's the only
# case that should start a new one.
_SNIPPET = f'''{MARKER_START}
SSHCTL_AGENT_ENV="{AGENT_ENV_PATH}"
if [ -z "${{SSH_AUTH_SOCK:-}}" ] && [ -f "$SSHCTL_AGENT_ENV" ]; then
    . "$SSHCTL_AGENT_ENV" > /dev/null 2>&1
fi
ssh-add -l > /dev/null 2>&1
if [ "$?" = "2" ]; then
    eval "$(ssh-agent -s)" > "$SSHCTL_AGENT_ENV"
fi
command -v sshctl > /dev/null 2>&1 && sshctl load-keys --quiet
{MARKER_END}
'''


def install(profile_path: Path = None) -> bool:
    profile_path = profile_path or (Path.home() / ".bashrc")
    KEYS_DIR.mkdir(parents=True, exist_ok=True)

    text = profile_path.read_text() if profile_path.exists() else ""
    if MARKER_START in text:
        return False

    with profile_path.open("a") as f:
        f.write("\n" + _SNIPPET)
    return True
