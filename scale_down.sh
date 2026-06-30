#!/usr/bin/env bash
# scale_down.sh — stop all Job Hunt Agent background services
#
# Run directly to stop services only:
#   ./scale_down.sh
#
# Source to also auto-deactivate the active venv:
#   source ./scale_down.sh

# Detect whether we are being sourced or executed
_SOURCED=false
[[ "${BASH_SOURCE[0]}" != "${0}" ]] && _SOURCED=true

# Only apply strict mode when executed directly — sourcing with set -e would
# cause any subsequent error in the parent shell to exit the terminal.
if ! $_SOURCED; then
  set -euo pipefail
fi

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

ok()     { echo -e "${GREEN}✓${NC} $*"; }
info()   { echo -e "${BLUE}→${NC} $*"; }
warn()   { echo -e "${YELLOW}!${NC} $*"; }
header() { echo -e "\n${BOLD}$*${NC}"; }

if [[ "$(uname)" != "Darwin" ]]; then
  echo -e "${RED}✗${NC} This script is for macOS only."
  $_SOURCED && return 1 || exit 1
fi

header "Job Hunt Agent — Scale Down"
echo ""

# ── MongoDB ───────────────────────────────────────────────────────────────────

header "MongoDB"
if brew services list | grep -q "mongodb-community.*started"; then
  info "Stopping MongoDB…"
  brew services stop mongodb-community
  ok "MongoDB stopped"
else
  ok "MongoDB already stopped"
fi

# ── Ollama ────────────────────────────────────────────────────────────────────

header "Ollama"
# Kill llama-server first — it's a child process that brew services stop won't reap.
if pgrep -x "llama-server" > /dev/null 2>&1; then
  info "Killing llama-server…"
  pkill -x "llama-server"
  ok "llama-server killed"
else
  ok "llama-server not running"
fi

# Use pgrep to check the actual process — brew services state can be stale (shows
# "error" instead of "started" after a failed bootstrap, even when ollama is alive).
if pgrep -x "ollama" > /dev/null 2>&1; then
  info "Stopping Ollama…"
  brew services stop ollama 2>/dev/null || true
  pkill -x "ollama" 2>/dev/null || true
  ok "Ollama stopped"
else
  ok "Ollama already stopped"
fi

# ── Virtual environment ───────────────────────────────────────────────────────

header "Virtual environment"
if $_SOURCED; then
  if [[ -n "${VIRTUAL_ENV:-}" ]]; then
    info "Deactivating venv (${VIRTUAL_ENV})…"
    deactivate
    ok "Virtual environment deactivated"
  else
    ok "No virtual environment active"
  fi
else
  warn "Run as a script — cannot deactivate the venv in your terminal. Either:"
  echo "       source ./scale_down.sh    # auto-deactivates the venv"
  echo "       deactivate                # or run this manually in your terminal"
fi

# ── Done ──────────────────────────────────────────────────────────────────────

echo ""
echo -e "${BOLD}Done. All services stopped.${NC}"
echo "Run ./scale_up.sh to bring everything back up."
echo ""
