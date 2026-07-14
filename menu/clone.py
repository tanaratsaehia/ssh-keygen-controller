import os
import subprocess
import time
from pathlib import Path
from typing import Tuple

# accept-new (not the default "ask") so a first-time connection to
# github.com's host key doesn't hang waiting for interactive confirmation on
# a headless test device.
GIT_SSH_COMMAND = "ssh -o StrictHostKeyChecking=accept-new"


def clone_repo(repo: str, dest_path: Path, retries: int = 3, delay: int = 4) -> Tuple[bool, str]:
    """Clone via the plain default GitHub SSH URL. All tracked keys are
    expected to already be loaded into ssh-agent — SSH offers each one in
    turn and GitHub accepts whichever is a valid deploy key for this repo.
    Retries a few times before giving up, since a deploy key just added on
    GitHub's side can take a moment to propagate."""
    dest_path = Path(dest_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    url = f"git@github.com:{repo}.git"

    env = dict(os.environ)
    env["GIT_SSH_COMMAND"] = GIT_SSH_COMMAND

    last_err = ""
    for attempt in range(1, retries + 1):
        result = subprocess.run(
            ["git", "clone", url, str(dest_path)],
            env=env,
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            return True, ""
        last_err = result.stderr.strip()
        if attempt < retries:
            time.sleep(delay)
    return False, last_err
