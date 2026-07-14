#!/bin/bash
# Bootstrap entry point for sshctl — per-repo SSH deploy key generator and
# manager for test devices.
#
# First run: checks for python3/git/openssh-client (installs missing apt
# packages), symlinks `sshctl` into ~/.local/bin, installs the ssh-agent
# auto-load shell hook, then launches the interactive menu.
#
# Re-running is safe and cheap: every step is idempotent.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/tmp/sshctl-install.log"

# ── Formatting ────────────────────────────────────────────────────────────────
_B='\033[1m'; _G='\033[1;32m'; _C='\033[0;36m'; _R='\033[1;31m'; _Y='\033[1;33m'; _D='\033[0m'

banner() {
    clear
    printf '\n'
    printf "${_B}  ╔══════════════════════════════════════════════════╗${_D}\n"
    printf "${_B}  ║        sshctl — SSH Deploy Key Manager            ║${_D}\n"
    printf "${_B}  ╚══════════════════════════════════════════════════╝${_D}\n"
    printf '\n'
    printf "  Log: %s\n\n" "$LOG_FILE"
}

step() { printf "  ${_C}→${_D}  %-52s" "$*..."; }
ok()   { printf "${_G}✓${_D}\n"; }
fail() {
    printf "${_R}✗${_D}\n\n"
    printf "  ${_R}ERROR:${_D} %s\n" "${1:-unknown error}"
    printf "  Check log for details: %s\n\n" "$LOG_FILE"
    exit 1
}

ensure_sshctl_command() {
    mkdir -p "$HOME/.local/bin"
    ln -sf "$SCRIPT_DIR/sshctl_launcher.sh" "$HOME/.local/bin/sshctl"
    chmod +x "$SCRIPT_DIR/sshctl_launcher.sh"

    case ":$PATH:" in
        *":$HOME/.local/bin:"*) ;;
        *)
            printf '\n  %sNOTE:%s ~/.local/bin is not in your PATH, so the `sshctl` command\n' "$_Y" "$_D"
            printf "  won't work yet. On Ubuntu/Debian, ~/.profile adds it automatically —\n"
            printf '  but only at login, so %slog out and back in%s (or run the line\n' "$_B" "$_D"
            printf '  below in every open terminal):\n'
            printf '    export PATH="$HOME/.local/bin:$PATH"\n'
            ;;
    esac
}

# ── Start ─────────────────────────────────────────────────────────────────────
banner
: > "$LOG_FILE"

# ── Step 1: python3 ────────────────────────────────────────────────────────────
step "python3"
command -v python3 >/dev/null 2>&1 || fail "python3 not found — install it first (apt-get install -y python3)"
ok

# ── Step 2: git / openssh-client ───────────────────────────────────────────────
step "git / openssh-client"
MISSING_APT=()
command -v git >/dev/null 2>&1 || MISSING_APT+=(git)
command -v ssh-keygen >/dev/null 2>&1 || MISSING_APT+=(openssh-client)

if [ ${#MISSING_APT[@]} -gt 0 ]; then
    printf '\n  [sudo required for apt-get]\n\n'
    sudo apt-get update >> "$LOG_FILE" 2>&1 || fail "apt-get update failed"
    sudo apt-get install -y "${MISSING_APT[@]}" >> "$LOG_FILE" 2>&1 \
        || fail "apt-get install failed (see log)"
    printf "  ${_G}✓${_D}  Installed: %s\n" "${MISSING_APT[*]}"
else
    ok
fi

# ── Step 3: 'sshctl' launcher command ──────────────────────────────────────────
step "'sshctl' launcher command"
ensure_sshctl_command
ok

# ── Step 4: ssh-agent auto-load shell hook ─────────────────────────────────────
step "ssh-agent auto-load shell hook"
cd "$SCRIPT_DIR"
python3 -m menu install-hook >> "$LOG_FILE" 2>&1 || fail "hook install failed (see log)"
ok

printf '\n'
printf "  ${_G}${_B}Bootstrap complete.${_D}  Launching menu...\n"
printf "  (Run '${_B}sshctl${_D}' any time to reopen it. Open a new shell to pick up\n"
printf "  the ssh-agent auto-load hook.)\n\n"
cd "$SCRIPT_DIR"
exec python3 -m menu
