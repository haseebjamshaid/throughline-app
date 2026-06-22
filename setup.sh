#!/usr/bin/env bash
#
# throughline — one-time setup
#
# Installs prerequisites (Ollama, uv, node), pulls the three local models,
# and installs backend + frontend dependencies. Idempotent: safe to re-run.
# Everything runs fully locally — no cloud, no API keys.
#
set -euo pipefail

# ----- pretty output -------------------------------------------------------
if [[ -t 1 ]]; then
  BOLD=$'\033[1m'; DIM=$'\033[2m'; RED=$'\033[31m'; GREEN=$'\033[32m'
  YELLOW=$'\033[33m'; BLUE=$'\033[34m'; RESET=$'\033[0m'
else
  BOLD=""; DIM=""; RED=""; GREEN=""; YELLOW=""; BLUE=""; RESET=""
fi

info()  { printf '%s\n' "${BLUE}==>${RESET} ${BOLD}$*${RESET}"; }
ok()    { printf '%s\n' "${GREEN}  ok${RESET} $*"; }
warn()  { printf '%s\n' "${YELLOW}  !! ${RESET}$*"; }
err()   { printf '%s\n' "${RED}error:${RESET} $*" >&2; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Models to pull: "name|approx size"
MODELS=(
  "embeddinggemma:300m|~622 MB"
  "qwen3-vl:4b|~3.3 GB"
  "qwen3.5:9b|~6.6 GB"
)

MODEL_PULL_ATTEMPTS=10

# ----- prerequisite checks -------------------------------------------------
info "Checking platform"
if [[ "$(uname -s)" != "Darwin" ]]; then
  err "This setup script targets macOS (Apple Silicon)."
  err "On other platforms, install Ollama, uv, and node manually, then run ./run.sh."
  exit 1
fi
ok "macOS detected"

info "Checking Homebrew"
if ! command -v brew >/dev/null 2>&1; then
  err "Homebrew is not installed."
  err "Install it from https://brew.sh and re-run ./setup.sh"
  exit 1
fi
ok "Homebrew found"

# ----- install prerequisites ----------------------------------------------
ensure_brew_pkg() {
  local cmd="$1" pkg="$2"
  if command -v "$cmd" >/dev/null 2>&1; then
    ok "$cmd already installed"
  else
    info "Installing $pkg via Homebrew"
    brew install "$pkg"
    ok "$pkg installed"
  fi
}

ensure_brew_pkg ollama ollama
ensure_brew_pkg uv uv
ensure_brew_pkg node node

# ----- Ollama is app-managed, not a login service --------------------------
# throughline starts/stops Ollama itself (see run.sh). Make sure it is not
# also running as an always-on Homebrew login service.
info "Ensuring Ollama is not registered as an always-on login service"
brew services stop ollama >/dev/null 2>&1 || true
ok "Ollama will be app-managed (started by ./run.sh, stopped on quit)"

# ----- temporary Ollama server for pulling models --------------------------
OLLAMA_HOST_URL="http://127.0.0.1:11434"
STARTED_OLLAMA=0
OLLAMA_PID=""

ollama_is_up() {
  curl -fsS "${OLLAMA_HOST_URL}/api/version" >/dev/null 2>&1
}

start_temp_ollama() {
  if ollama_is_up; then
    ok "Ollama is already serving — using the running instance"
    return
  fi
  info "Starting a temporary Ollama server to pull models"
  ollama serve >/dev/null 2>&1 &
  OLLAMA_PID=$!
  STARTED_OLLAMA=1
  # wait up to ~30s for it to come up
  local i
  for i in $(seq 1 30); do
    if ollama_is_up; then
      ok "Ollama server is ready"
      return
    fi
    sleep 1
  done
  err "Ollama server did not become ready in time."
  exit 1
}

stop_temp_ollama() {
  if [[ "$STARTED_OLLAMA" == "1" && -n "$OLLAMA_PID" ]]; then
    info "Stopping the temporary Ollama server (it is app-managed at runtime)"
    kill "$OLLAMA_PID" >/dev/null 2>&1 || true
    wait "$OLLAMA_PID" 2>/dev/null || true
    ok "Temporary Ollama server stopped"
  fi
}
trap stop_temp_ollama EXIT

start_temp_ollama

# ----- pull models with a resilient retry loop -----------------------------
# The big model can fail on flaky networks (TLS timeouts / connection resets).
# Retrying resumes from cache, so a patient loop gets there eventually.
pull_model() {
  local name="$1" size="$2" attempt
  if ollama show "$name" >/dev/null 2>&1; then
    ok "$name already present (skipping download)"
    return
  fi
  info "Pulling ${name} (${size})"
  if [[ "$name" == "qwen3.5:9b" ]]; then
    warn "This is the large model — it may take a while on a slow or flaky network."
    warn "If it fails, the retry loop resumes from cache; just be patient."
  fi
  for attempt in $(seq 1 "$MODEL_PULL_ATTEMPTS"); do
    if ollama pull "$name"; then
      ok "$name pulled"
      return
    fi
    warn "pull of ${name} failed (attempt ${attempt}/${MODEL_PULL_ATTEMPTS}); retrying — resumes from cache"
    sleep 3
  done
  err "Failed to pull ${name} after ${MODEL_PULL_ATTEMPTS} attempts."
  err "Check your network and re-run ./setup.sh — it resumes from cache."
  exit 1
}

info "Pulling local models (~10 GB total)"
for entry in "${MODELS[@]}"; do
  name="${entry%%|*}"
  size="${entry##*|}"
  pull_model "$name" "$size"
done
ok "All models present"

# temporary Ollama no longer needed; the EXIT trap stops it
stop_temp_ollama
trap - EXIT

# ----- backend dependencies ------------------------------------------------
info "Installing backend dependencies (uv)"
uv --directory "${SCRIPT_DIR}/server" sync --extra dev
ok "Backend dependencies installed"

# ----- frontend dependencies -----------------------------------------------
info "Installing frontend dependencies (npm)"
npm --prefix "${SCRIPT_DIR}/app" install
ok "Frontend dependencies installed"

# ----- done ----------------------------------------------------------------
printf '\n%s\n' "${GREEN}${BOLD}Setup complete${RESET}"
printf '%s\n' "  next:"
printf '%s\n' "  1. ${BOLD}./scripts/setup-vault.sh${RESET}  — create your private Obsidian vault + git sync"
printf '%s\n' "       (forking? override THROUGHLINE_VAULT / THROUGHLINE_VAULT_REPO / THROUGHLINE_GIT_NAME / THROUGHLINE_GIT_EMAIL)"
printf '%s\n' "  2. ${BOLD}./run.sh${RESET}                   — start throughline (app-managed Ollama)"
