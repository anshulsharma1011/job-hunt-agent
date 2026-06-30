#!/usr/bin/env bash
# scale_up.sh — one-shot setup for Job Hunt Agent on macOS
# Safe to re-run: every step checks before acting.
#
# Run directly to install/start everything (manual venv activation required):
#   ./scale_up.sh
#
# Source to also auto-activate the venv in your current shell:
#   source ./scale_up.sh

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

ok()   { echo -e "${GREEN}✓${NC} $*"; }
info() { echo -e "${BLUE}→${NC} $*"; }
warn() { echo -e "${YELLOW}!${NC} $*"; }
fail() { echo -e "${RED}✗${NC} $*"; $_SOURCED && return 1 || exit 1; }
header() { echo -e "\n${BOLD}$*${NC}"; }

# ── Guard ──────────────────────────────────────────────────────────────────────

if [[ "$(uname)" != "Darwin" ]]; then
  fail "This script is for macOS only."
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

header "Job Hunt Agent — Scale Up"
echo "This script installs all prerequisites and configures the project."
echo "It is safe to re-run at any time."
echo ""

# ── 1. Homebrew ────────────────────────────────────────────────────────────────

header "Step 1 — Homebrew"
if command -v brew &>/dev/null; then
  ok "Homebrew already installed ($(brew --version | head -1))"
else
  info "Installing Homebrew…"
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

  # Add Homebrew to PATH for Apple Silicon
  if [[ -f /opt/homebrew/bin/brew ]]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
  fi
  ok "Homebrew installed"
fi

# ── 2. Git ─────────────────────────────────────────────────────────────────────

header "Step 2 — Git"
if command -v git &>/dev/null; then
  ok "Git already installed ($(git --version))"
else
  info "Installing Git…"
  brew install git
  ok "Git installed"
fi

# ── 3. Python 3.12 ────────────────────────────────────────────────────────────

header "Step 3 — Python 3.12"
if command -v python3.12 &>/dev/null; then
  ok "Python 3.12 already installed ($(python3.12 --version))"
else
  info "Installing Python 3.12…"
  brew install python@3.12
  brew link python@3.12 --force 2>/dev/null || true
  ok "Python 3.12 installed"
fi

# ── 4. uv (package manager) ───────────────────────────────────────────────────
# uv replaces pip for venv creation and package installation. It avoids a known
# issue on macOS Tahoe (beta) where pip's xmlrpc.client import fails due to a
# libexpat symbol mismatch between Homebrew Python and the macOS system library.

header "Step 4 — uv (package manager)"
if command -v uv &>/dev/null; then
  ok "uv already installed ($(uv --version))"
else
  info "Installing uv…"
  brew install uv
  ok "uv installed"
fi

# ── 5. MongoDB ────────────────────────────────────────────────────────────────

header "Step 5 — MongoDB"
if brew list mongodb-community &>/dev/null 2>&1; then
  ok "MongoDB already installed"
else
  info "Installing MongoDB…"
  brew tap mongodb/brew 2>/dev/null || true
  brew install mongodb-community
  ok "MongoDB installed"
fi

if brew services list | grep -q "mongodb-community.*started"; then
  ok "MongoDB service already running"
else
  info "Starting MongoDB service…"
  brew services start mongodb-community
  ok "MongoDB started"
fi

# Quick connectivity check
if mongosh --eval "db.runCommand({ connectionStatus: 1 })" --quiet &>/dev/null 2>&1; then
  ok "MongoDB responding on localhost:27017"
else
  warn "MongoDB may still be starting — if you see errors later, run: brew services restart mongodb-community"
fi

# ── 6. Ollama ─────────────────────────────────────────────────────────────────

header "Step 6 — Ollama"
if command -v ollama &>/dev/null; then
  ok "Ollama already installed"
else
  info "Installing Ollama…"
  brew install ollama
  ok "Ollama installed"
fi

if curl -sf http://localhost:11434/ &>/dev/null; then
  ok "Ollama already responding on localhost:11434"
else
  info "Starting Ollama service…"
  brew services start ollama 2>/dev/null || true
  # Give it a moment to bind
  sleep 3
  if curl -sf http://localhost:11434/ &>/dev/null; then
    ok "Ollama started and responding on localhost:11434"
  else
    warn "Ollama did not start — run: brew services restart ollama"
  fi
fi

# ── 7. AI Model ───────────────────────────────────────────────────────────────

header "Step 7 — AI Model (llama3.1:8b)"
INSTALLED_MODELS=$(ollama list 2>/dev/null || true)
if echo "$INSTALLED_MODELS" | grep -q "llama3.1:8b"; then
  ok "llama3.1:8b already downloaded"
else
  info "Downloading llama3.1:8b (~5 GB). This takes 10–20 minutes on a typical connection…"
  ollama pull llama3.1:8b
  ok "llama3.1:8b downloaded"
fi

# ── 8. Python virtualenv + dependencies ───────────────────────────────────────

header "Step 8 — Python virtual environment"
if [[ -d "$SCRIPT_DIR/.venv" ]]; then
  # Verify uv can use the existing venv — it may be broken if Python was upgraded
  if ! uv pip list --python "$SCRIPT_DIR/.venv/bin/python" &>/dev/null 2>&1; then
    warn "Existing .venv is broken — recreating…"
    rm -rf "${SCRIPT_DIR:?}/.venv"
    uv venv "$SCRIPT_DIR/.venv" --python python3.12
    ok "Virtual environment recreated"
  else
    ok "Virtual environment already exists and is healthy"
  fi
else
  info "Creating .venv with Python 3.12…"
  uv venv "$SCRIPT_DIR/.venv" --python python3.12
  ok "Virtual environment created"
fi

info "Installing Python dependencies…"
uv pip install --quiet -r "$SCRIPT_DIR/requirements.txt" --python "$SCRIPT_DIR/.venv/bin/python"
ok "Dependencies installed"

# ── 9. Environment file ───────────────────────────────────────────────────────

header "Step 9 — Environment configuration"
ENV_FILE="$SCRIPT_DIR/.env"

if [[ -f "$ENV_FILE" ]]; then
  ok ".env already exists — skipping creation"
else
  info "Creating .env from .env.example…"
  cp "$SCRIPT_DIR/.env.example" "$ENV_FILE"
  ok ".env created"
fi

# Adzuna credentials — prompt only if both are still empty
ADZUNA_ID_SET=$(grep -E "^ADZUNA_APP_ID=.+" "$ENV_FILE" || true)
ADZUNA_KEY_SET=$(grep -E "^ADZUNA_API_KEY=.+" "$ENV_FILE" || true)

if [[ -z "$ADZUNA_ID_SET" || -z "$ADZUNA_KEY_SET" ]]; then
  echo ""
  echo "Adzuna is one of the job sources (free tier — https://developer.adzuna.com)."
  echo "You can skip this now and fill in .env later."
  echo ""
  read -rp "Enter ADZUNA_APP_ID   (press Enter to skip): " ADZUNA_APP_ID
  read -rp "Enter ADZUNA_API_KEY  (press Enter to skip): " ADZUNA_API_KEY

  if [[ -n "$ADZUNA_APP_ID" ]]; then
    sed -i '' "s|^ADZUNA_APP_ID=.*|ADZUNA_APP_ID=${ADZUNA_APP_ID}|" "$ENV_FILE"
  fi
  if [[ -n "$ADZUNA_API_KEY" ]]; then
    sed -i '' "s|^ADZUNA_API_KEY=.*|ADZUNA_API_KEY=${ADZUNA_API_KEY}|" "$ENV_FILE"
  fi

  if [[ -n "$ADZUNA_APP_ID" && -n "$ADZUNA_API_KEY" ]]; then
    ok "Adzuna credentials saved to .env"
  else
    warn "Adzuna credentials not set — Adzuna source will be disabled until you fill them in .env"
  fi
else
  ok "Adzuna credentials already set in .env"
fi

# ── Virtual environment activation ────────────────────────────────────────────

header "Virtual environment"
if $_SOURCED; then
  info "Activating venv…"
  source "$SCRIPT_DIR/.venv/bin/activate"
  ok "Virtual environment activated (${VIRTUAL_ENV})"
else
  warn "Run as a script — cannot activate the venv in your terminal. Either:"
  echo "       source ./scale_up.sh       # auto-activates the venv"
  echo "       source .venv/bin/activate  # or run this manually in your terminal"
fi

# ── Done ──────────────────────────────────────────────────────────────────────

echo ""
echo -e "${BOLD}Ready. To run the agent:${NC}"
echo "  job-hunt run"
echo ""
