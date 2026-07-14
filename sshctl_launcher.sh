#!/bin/bash
# Static, portable launcher symlinked into ~/.local/bin/sshctl by install.sh.
# Reopens the sshctl menu (or runs a subcommand) without re-running the bootstrap.
set -euo pipefail

SELF="$(readlink -f "${BASH_SOURCE[0]}")"
DIR="$(cd "$(dirname "$SELF")" && pwd)"

cd "$DIR"
exec python3 -m menu "$@"
