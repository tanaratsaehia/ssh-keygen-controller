import subprocess
from pathlib import Path
from typing import Iterable


def load_key(key_path: Path, quiet: bool = False) -> bool:
    result = subprocess.run(
        ["ssh-add", str(key_path)],
        capture_output=True, text=True,
    )
    if result.returncode != 0 and not quiet:
        print(f"  ! ssh-add failed for {key_path}: {result.stderr.strip()}")
    return result.returncode == 0


def load_all(key_paths: Iterable[Path], quiet: bool = False) -> bool:
    ok = True
    for key_path in key_paths:
        if not load_key(key_path, quiet=quiet):
            ok = False
    return ok
