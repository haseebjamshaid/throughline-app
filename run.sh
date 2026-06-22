#!/usr/bin/env bash
#
# throughline — run the app (app-managed Ollama lifecycle)
#
# Starts Ollama (only if it isn't already running), the FastAPI backend,
# and the Vite frontend. On exit it tears everything down: stops the backend
# and frontend, unloads models from RAM, and stops Ollama if WE started it.
# Everything runs fully locally — no cloud.
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

OLLAMA_HOST_URL="http://127.0.0.1:11434"
BACKEND_URL="http://localhost:8000"
FRONTEND_URL="http://localhost:5173"

# Models to unload on exit (free RAM).
MODELS=("embeddinggemma:300m" "qwen3-vl:4b" "qwen3.5:9b")

# RAM-safe Ollama config (16 GB target): keep at most ONE model resident at a
# time and unload it ~30s after idle. Honours any value you already exported.
export OLLAMA_MAX_LOADED_MODELS="${OLLAMA_MAX_LOADED_MODELS:-1}"
export OLLAMA_KEEP_ALIVE="${OLLAMA_KEEP_ALIVE:-30s}"

STARTED_OLLAMA=0
OLLAMA_PID=""
BACKEND_PID=""
FRONTEND_PID=""

ollama_is_up() {
  curl -fsS "${OLLAMA_HOST_URL}/api/version" >/dev/null 2>&1
}

# ----- teardown ------------------------------------------------------------
cleanup() {
  trap - EXIT INT TERM
  printf '\n'
  info "Shutting down"

  if [[ -n "$FRONTEND_PID" ]]; then
    kill "$FRONTEND_PID" >/dev/null 2>&1 || true
    wait "$FRONTEND_PID" 2>/dev/null || true
    ok "Frontend stopped"
  fi

  if [[ -n "$BACKEND_PID" ]]; then
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
    wait "$BACKEND_PID" 2>/dev/null || true
    ok "Backend stopped"
  fi

  # Best-effort: unload models from RAM so nothing lingers resident.
  if ollama_is_up; then
    local m
    for m in "${MODELS[@]}"; do
      ollama stop "$m" >/dev/null 2>&1 || true
    done
    ok "Models unloaded from RAM"
  fi

  # Only stop Ollama if we were the ones who started it.
  if [[ "$STARTED_OLLAMA" == "1" && -n "$OLLAMA_PID" ]]; then
    kill "$OLLAMA_PID" >/dev/null 2>&1 || true
    wait "$OLLAMA_PID" 2>/dev/null || true
    ok "Ollama stopped (it was started by this app)"
  else
    ok "Left the pre-existing Ollama instance running"
  fi

  ok "Goodbye"
}
trap cleanup EXIT INT TERM

# ----- start Ollama (only if not already running) --------------------------
info "Starting Ollama (app-managed)"
if ollama_is_up; then
  ok "Ollama is already running — reusing it (won't stop it on exit)"
else
  ollama serve >/dev/null 2>&1 &
  OLLAMA_PID=$!
  STARTED_OLLAMA=1
  # wait up to ~30s for the API to respond
  for i in $(seq 1 30); do
    if ollama_is_up; then
      break
    fi
    sleep 1
  done
  if ! ollama_is_up; then
    err "Ollama did not become ready in time."
    exit 1
  fi
  ok "Ollama is ready"
fi

# ----- start backend -------------------------------------------------------
info "Starting backend (FastAPI on ${BACKEND_URL})"
uv --directory "${SCRIPT_DIR}/server" run uvicorn throughline.main:app --port 8000 &
BACKEND_PID=$!
ok "Backend starting (pid ${BACKEND_PID})"

# ----- start frontend ------------------------------------------------------
info "Starting frontend (Vite on ${FRONTEND_URL})"
npm --prefix "${SCRIPT_DIR}/app" run dev &
FRONTEND_PID=$!
ok "Frontend starting (pid ${FRONTEND_PID})"

# ----- ready ---------------------------------------------------------------
printf '\n'
info "throughline is running"
printf '  %sApp:%s %s\n' "$BOLD" "$RESET" "$FRONTEND_URL"
printf '  %sAPI:%s %s  %s(docs: %s/docs)%s\n' "$BOLD" "$RESET" "$BACKEND_URL" "$DIM" "$BACKEND_URL" "$RESET"
printf '\n%s\n' "${DIM}Press Ctrl+C to stop everything (and free model RAM).${RESET}"

# Wait on the long-running children; cleanup runs via trap on exit/interrupt.
wait
