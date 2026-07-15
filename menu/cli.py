import argparse
import shutil
from pathlib import Path

from . import agent, clone as clone_mod, config_store, keygen, login_hook
from .paths import CD_TARGET_PATH, DEFAULT_CLONE_ROOT


def _print_pubkey_instructions(repo: str) -> None:
    pubkey = keygen.read_public_key(repo)
    print()
    print(f"  Public key for {repo}:")
    print(f"  {pubkey}")
    print()
    print("  Add it as a READ-ONLY deploy key here (leave 'Allow write access' unchecked):")
    print(f"  https://github.com/{repo}/settings/keys/new")
    print()


def cmd_add(repo: str, path: str = None) -> int:
    if config_store.get_repo(repo):
        print(f"  {repo} is already tracked. Use 'regenerate' to rotate its key.")
        return 1

    owner, name = repo.split("/", 1)
    default_path = DEFAULT_CLONE_ROOT / owner / name
    if path is None:
        entered = input(f"  Clone path [{default_path}]: ").strip()
        clone_path = Path(entered).expanduser() if entered else default_path
    else:
        clone_path = Path(path).expanduser()

    priv, _ = keygen.generate_key(repo)
    config_store.add_repo(repo, clone_path)
    _print_pubkey_instructions(repo)
    input("  Press Enter once the deploy key is added on GitHub...")

    agent.load_key(priv)
    print(f"  Cloning {repo} into {clone_path} ...")
    ok, err = clone_mod.clone_repo(repo, clone_path)
    print("  Cloned." if ok else f"  Clone failed: {err}")
    return 0 if ok else 1


def cmd_list() -> int:
    repos = config_store.all_repos()
    if not repos:
        print("  No repos tracked yet.")
        return 0
    for repo, meta in repos.items():
        has_key = "yes" if keygen.key_exists(repo) else "MISSING"
        cloned = "yes" if Path(meta["clone_path"]).exists() else "no"
        print(f"  {repo:<40} key={has_key:<8} cloned={cloned:<4} path={meta['clone_path']}")
    return 0


def cmd_regenerate(repo: str) -> int:
    if not config_store.get_repo(repo):
        print(f"  {repo} is not tracked. Use 'add' first.")
        return 1

    keygen.delete_key(repo)
    priv, _ = keygen.generate_key(repo)
    _print_pubkey_instructions(repo)
    print("  Remove the OLD deploy key for this device on GitHub:")
    print(f"  https://github.com/{repo}/settings/keys")
    input("  Press Enter once the new deploy key is added on GitHub...")

    agent.load_key(priv)
    return 0


def cmd_remove(repo: str, delete_clone: bool = False) -> int:
    meta = config_store.get_repo(repo)
    if not meta:
        print(f"  {repo} is not tracked.")
        return 1

    keygen.delete_key(repo)
    config_store.remove_repo(repo)
    print(f"  {repo} untracked and local key deleted.")
    print(f"  Remove its deploy key on GitHub: https://github.com/{repo}/settings/keys")

    if delete_clone:
        shutil.rmtree(meta["clone_path"], ignore_errors=True)
        print(f"  Deleted clone at {meta['clone_path']}")
    return 0


def cmd_clone(repo: str, force: bool = False) -> int:
    meta = config_store.get_repo(repo)
    if not meta:
        print(f"  {repo} is not tracked. Use 'add' first.")
        return 1

    dest = Path(meta["clone_path"])
    if dest.exists() and any(dest.iterdir()) and not force:
        print(f"  {dest} already exists and is non-empty. Nothing to do.")
        return 0

    if not keygen.key_exists(repo):
        print(f"  No key found for {repo}. Run 'regenerate' first.")
        return 1

    agent.load_key(keygen.private_key_path(repo))
    ok, err = clone_mod.clone_repo(repo, dest)
    print("  Cloned." if ok else f"  Clone failed: {err}")
    return 0 if ok else 1


def cmd_reset() -> int:
    """Bulk provisioning path for a fresh device: config.json (repo + clone
    path only, no key material) can be copied from an existing device, then
    this walks every tracked repo, generating any missing key and cloning
    anything not already present."""
    repos = config_store.all_repos()
    if not repos:
        print("  No repos tracked yet.")
        return 0

    for repo, meta in repos.items():
        print(f"\n== {repo} ==")
        if not keygen.key_exists(repo):
            priv, _ = keygen.generate_key(repo)
            _print_pubkey_instructions(repo)
            input("  Press Enter once the deploy key is added on GitHub...")
        else:
            priv = keygen.private_key_path(repo)

        agent.load_key(priv)

        dest = Path(meta["clone_path"])
        if dest.exists() and any(dest.iterdir()):
            print(f"  Already cloned at {dest}")
            continue

        ok, err = clone_mod.clone_repo(repo, dest)
        print("  Cloned." if ok else f"  Clone failed: {err}")
    return 0


def _cloned_repos() -> dict:
    return {r: m for r, m in config_store.all_repos().items() if Path(m["clone_path"]).exists()}


def cmd_goto(repo: str = None) -> int:
    """Selects a cloned project's path and hands it off via CD_TARGET_PATH.
    A plain Python subprocess can't change its parent shell's directory, so
    the actual `cd` happens in the shell function installed by
    login_hook.install(), which reads this file after sshctl exits."""
    cloned = _cloned_repos()
    if not cloned:
        print("  No cloned projects found yet.")
        return 1

    if repo is None:
        items = list(cloned.items())
        print()
        print("  Cloned projects:")
        for i, (r, meta) in enumerate(items, 1):
            print(f"   {i}) {r}  ->  {meta['clone_path']}")
        choice = input("  > ").strip()
        try:
            repo, meta = items[int(choice) - 1]
        except (ValueError, IndexError):
            print("  Invalid selection.")
            return 1
    else:
        meta = cloned.get(repo)
        if not meta:
            print(f"  {repo} is not tracked or not cloned.")
            return 1

    CD_TARGET_PATH.parent.mkdir(parents=True, exist_ok=True)
    CD_TARGET_PATH.write_text(meta["clone_path"])
    print(f"  -> {meta['clone_path']}")
    return 0


def cmd_load_keys(quiet: bool = False) -> int:
    repos = config_store.all_repos()
    keys = [keygen.private_key_path(r) for r in repos if keygen.key_exists(r)]
    agent.load_all(keys, quiet=quiet)
    return 0


def cmd_install_hook() -> int:
    installed = login_hook.install()
    print("  Shell login hook installed." if installed else "  Shell login hook already present.")
    return 0


def _prompt_repo() -> str:
    return input("  owner/repo: ").strip()


def _clear_screen() -> None:
    # Move cursor home and clear the visible screen (not scrollback) —
    # standard ANSI, works on any terminal a Raspberry Pi test device uses.
    print("\033[H\033[2J", end="")


def _interactive_menu() -> int:
    actions = {
        "1": ("Add repo", lambda: cmd_add(_prompt_repo())),
        "2": ("List repos", cmd_list),
        "3": ("Regenerate key", lambda: cmd_regenerate(_prompt_repo())),
        "4": ("Remove repo", lambda: cmd_remove(_prompt_repo())),
        "5": ("Clone / re-clone", lambda: cmd_clone(_prompt_repo())),
        "6": ("Reset device (bulk generate + clone)", cmd_reset),
        "7": ("Load keys into ssh-agent now", cmd_load_keys),
        "8": ("Go to project (cd)", cmd_goto),
    }
    while True:
        _clear_screen()
        print("\n  sshctl — SSH deploy key manager")
        for key, (label, _) in actions.items():
            print(f"   {key}) {label}")
        print("   0) Exit")

        choice = input("  > ").strip()
        if choice == "0":
            return 0

        action = actions.get(choice)
        if not action:
            print("  Unknown option.")
            input("  Press Enter to continue...")
            continue

        try:
            action[1]()
        except KeyboardInterrupt:
            print()
        except Exception as e:
            print(f"  Error: {e}")

        input("\n  Press Enter to continue...")


def main(argv) -> int:
    parser = argparse.ArgumentParser(prog="sshctl")
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("add")
    p.add_argument("repo")
    p.add_argument("--path")

    sub.add_parser("list")

    p = sub.add_parser("regenerate")
    p.add_argument("repo")

    p = sub.add_parser("remove")
    p.add_argument("repo")
    p.add_argument("--delete-clone", action="store_true")

    p = sub.add_parser("clone")
    p.add_argument("repo")
    p.add_argument("--force", action="store_true")

    sub.add_parser("reset")

    p = sub.add_parser("load-keys")
    p.add_argument("--quiet", action="store_true")

    sub.add_parser("install-hook")

    p = sub.add_parser("goto")
    p.add_argument("repo", nargs="?")

    args = parser.parse_args(argv)

    if args.command == "add":
        return cmd_add(args.repo, args.path)
    if args.command == "list":
        return cmd_list()
    if args.command == "regenerate":
        return cmd_regenerate(args.repo)
    if args.command == "remove":
        return cmd_remove(args.repo, args.delete_clone)
    if args.command == "clone":
        return cmd_clone(args.repo, args.force)
    if args.command == "reset":
        return cmd_reset()
    if args.command == "load-keys":
        return cmd_load_keys(args.quiet)
    if args.command == "install-hook":
        return cmd_install_hook()
    if args.command == "goto":
        return cmd_goto(args.repo)

    return _interactive_menu()
