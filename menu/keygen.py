import subprocess
from pathlib import Path

from .device import hostname
from .paths import KEYS_DIR


def _slug(repo: str) -> str:
    return repo.replace("/", "_")


def key_dir(repo: str) -> Path:
    return KEYS_DIR / _slug(repo)


def private_key_path(repo: str) -> Path:
    return key_dir(repo) / "id_ed25519"


def public_key_path(repo: str) -> Path:
    return private_key_path(repo).with_suffix(".pub")


def key_exists(repo: str) -> bool:
    return private_key_path(repo).exists()


def generate_key(repo: str):
    """Generate a fresh, passphrase-less ed25519 deploy key dedicated to this
    (device, repo) pair. Comment embeds the hostname so the same repo cloned
    on multiple devices produces distinguishable entries in GitHub's deploy
    key list."""
    d = key_dir(repo)
    d.mkdir(parents=True, exist_ok=True)
    priv = private_key_path(repo)
    comment = f"{hostname()}-{_slug(repo)}-deploy"
    subprocess.run(
        [
            "ssh-keygen", "-t", "ed25519",
            "-N", "",
            "-C", comment,
            "-f", str(priv),
            "-q",
        ],
        check=True,
    )
    priv.chmod(0o600)
    return priv, public_key_path(repo)


def read_public_key(repo: str) -> str:
    return public_key_path(repo).read_text().strip()


def delete_key(repo: str) -> None:
    d = key_dir(repo)
    if not d.exists():
        return
    for f in d.iterdir():
        f.unlink()
    d.rmdir()
