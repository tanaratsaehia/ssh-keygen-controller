# sshctl

A per-repo SSH deploy key generator and manager for test devices that need
to clone multiple GitHub repos.

Every repo gets its own dedicated SSH keypair (a GitHub deploy key) instead
of one key shared across everything. Keys and clone paths are tracked in a
small local config so you can list, regenerate, or remove them later, and
so a fresh device can be provisioned from the same repo list.

## Why per-repo keys

GitHub deploy keys are scoped to a single repository. Generating one keypair
per (device, repo) pair — rather than one key for your whole GitHub account
— means:

- Revoking access to one repo never affects any other repo or device.
- Each device's key is labeled with its hostname, so GitHub's deploy-key
  list tells you exactly which physical device a key belongs to.
- Keys default to **read-only**, so a compromised device can't push.

## How cloning works

`sshctl` clones using the plain, default GitHub SSH URL
(`git@github.com:owner/repo.git`) — nothing custom. To make that work with
many per-repo keys, all tracked private keys are loaded into `ssh-agent`;
SSH offers each one in turn and GitHub accepts whichever is a valid deploy
key for that repo. A shell-login hook keeps `ssh-agent` populated across
reboots, so this happens automatically every time you open a terminal.

If a clone fails (e.g. the deploy key hasn't propagated on GitHub's side
yet), `sshctl` retries a few times and then reports git's actual error —
it never silently falls back to HTTPS or an unauthenticated clone.

## Requirements

- Linux (Debian/Ubuntu-family — Raspberry Pi OS, Ubuntu, etc.)
- `python3` (standard library only, no extra Python packages)
- `git` and `openssh-client` — `install.sh` installs these via `apt-get` if
  missing

## Install

```bash
git clone https://github.com/tanaratsaehia/ssh-keygen-controller.git
cd ssh-keygen-controller
./install.sh
```

This will:

1. Check for `python3`, `git`, `ssh-keygen` (installing missing apt packages
   if needed — you'll be asked for `sudo`).
2. Symlink the `sshctl` command into `~/.local/bin`.
3. Install a shell-login hook (appended to `~/.bashrc`) that keeps
   `ssh-agent` running and loaded with your tracked keys across reboots.
4. Launch the interactive menu.

Re-running `./install.sh` any time is safe — every step is idempotent.

Open a **new shell** (or `source ~/.bashrc`) after the first install so the
`ssh-agent` hook takes effect.

## Usage

Run `sshctl` with no arguments to reopen the interactive menu at any time:

```
  sshctl — SSH deploy key manager
   1) Add repo
   2) List repos
   3) Regenerate key
   4) Remove repo
   5) Clone / re-clone
   6) Reset device (bulk generate + clone)
   7) Load keys into ssh-agent now
   8) Go to project (cd)
   0) Exit
```

Or use the equivalent non-interactive subcommands, e.g. in scripts:

```bash
sshctl add owner/repo [--path /custom/clone/path]
sshctl list
sshctl regenerate owner/repo
sshctl remove owner/repo [--delete-clone]
sshctl clone owner/repo [--force]
sshctl reset
sshctl load-keys [--quiet]
sshctl goto [owner/repo]
```

### Adding a repo

```bash
sshctl add owner/repo
```

1. Prompts for a clone path (defaults to `~/repos/owner/repo`).
2. Generates a new ed25519 keypair dedicated to this repo + device.
3. Prints the public key and a direct link to add it as a **read-only**
   deploy key on GitHub:
   `https://github.com/owner/repo/settings/keys/new`
4. Waits for you to confirm you've added it, then clones the repo over SSH.

### Regenerating a key

```bash
sshctl regenerate owner/repo
```

Deletes the old local key, generates a new one, and prints both the new
key to add on GitHub **and** a reminder link to go delete the old one —
`sshctl` can't remove it for you automatically, since key registration is
manual by design (no GitHub token required).

### Provisioning a fresh device

`config.json` only ever stores `owner/repo → clone path` — never key
material — so it's safe to copy to a brand-new device:

```bash
scp ~/.ssh-keygen-controller/config.json newdevice:~/.ssh-keygen-controller/config.json
ssh newdevice
sshctl reset
```

`reset` walks every tracked repo, generates a fresh device-specific key for
any repo that doesn't already have one on this device, prompts you to add
each one on GitHub, and clones anything not already present.

### Jumping to a cloned project

```bash
sshctl goto
```

Lists every tracked repo that's actually cloned on this device and lets you
pick one; running `sshctl goto owner/repo` skips the picker. Your shell
lands in that repo's directory when the command returns.

This only works from an interactive shell that has the login hook installed
(see [Provisioning a fresh device](#provisioning-a-fresh-device) / re-run
`install.sh` on existing devices) — a plain child process can never change
its parent shell's working directory, so `install-hook` also defines a
`sshctl` shell function in `~/.bashrc` that does the actual `cd` once the
underlying command exits. Non-interactive uses (scripts, `sshctl_launcher.sh`
run directly) just print the resolved path instead.

## Where things live

| What | Where |
|---|---|
| Deploy keys | `~/.ssh/deploy-keys/<owner>_<repo>/id_ed25519{,.pub}` |
| Tracked repos / clone paths | `~/.ssh-keygen-controller/config.json` |
| Cloned repos | `~/repos/<owner>/<repo>` by default, or wherever you chose |
| ssh-agent session file | `~/.ssh/deploy-keys/.agent-env` |

## Security notes

- Keys are passphrase-less so the shell-login hook can load them into
  `ssh-agent` without an interactive prompt. Protection relies on file
  permissions (`600`) and physical/access control of the device — normal
  for automated deploy-key setups.
- Keys default to read-only. Leave "Allow write access" unchecked when
  adding the deploy key on GitHub unless you specifically need push access.
- Registration is manual copy-paste on purpose — `sshctl` never needs a
  GitHub token or API access.
