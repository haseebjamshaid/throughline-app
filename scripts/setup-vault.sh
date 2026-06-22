#!/usr/bin/env bash
#
# throughline — create & wire a DEDICATED, PRIVATE Obsidian vault for your data.
#
# This is separate from the throughline *code* repo. Your vault holds your
# notes — taste (films/songs/books/quotes) AND private self-material
# (ambitions/fears/journal). It is a PRIVATE git repo, synced by the Obsidian
# Git plugin, and registered as its own vault in Obsidian (alongside any others).
#
# Override defaults via env vars (THROUGHLINE_VAULT, THROUGHLINE_VAULT_REPO, ...).
set -euo pipefail

VAULT="${THROUGHLINE_VAULT:-$HOME/throughline-vault}"
REPO_SSH="${THROUGHLINE_VAULT_REPO:-git@github.com:haseebjamshaid/throughline-vault.git}"
SSH_KEY="${THROUGHLINE_SSH_KEY:-$HOME/.ssh/id_personal}"
GIT_NAME="${THROUGHLINE_GIT_NAME:-Haseeb Jamshaid}"
GIT_EMAIL="${THROUGHLINE_GIT_EMAIL:-88651579+haseebjamshaid@users.noreply.github.com}"

bold() { printf '\033[1m%s\033[0m\n' "$*"; }

bold "==> throughline vault → $VAULT"
mkdir -p "$VAULT/attachments"

# A small readme so it opens as a real, navigable Obsidian vault.
if [ ! -f "$VAULT/README.md" ]; then
  cat > "$VAULT/README.md" <<'EOF'
# throughline vault

your private second brain. one note = one thing that makes you you:
taste — movie · song · book · quote
self — ambition · fear · experience · journal   (private, never leaves this machine)

throughline reads these locally and becomes the brain on top.
EOF
fi

# NEVER commit the derived index or obsidian's local workspace state.
cat > "$VAULT/.gitignore" <<'EOF'
.throughline/
.DS_Store
.obsidian/workspace*.json
.obsidian/cache
EOF

# Git init + your identity (repo-local; pushes over your personal SSH key).
if [ ! -d "$VAULT/.git" ]; then
  git -C "$VAULT" init -q -b main
fi
git -C "$VAULT" config user.name "$GIT_NAME"
git -C "$VAULT" config user.email "$GIT_EMAIL"
if [ -f "$SSH_KEY" ]; then
  git -C "$VAULT" config core.sshCommand "ssh -i $SSH_KEY -o IdentitiesOnly=yes"
fi
git -C "$VAULT" add -A
git -C "$VAULT" commit -q -m "chore: start throughline vault" 2>/dev/null || echo "   (nothing new to commit)"

# Obsidian won't auto-register a brand-new folder via URI — it needs a one-time
# "open folder as vault". Bring Obsidian up and tell the user exactly what to click.
bold "==> add this folder to Obsidian (one time)"
open -a Obsidian 2>/dev/null || true
echo "   in Obsidian → vault switcher (bottom-left) → Manage vaults… → Open folder as vault →"
echo "   $VAULT"

# Private GitHub sync. The repo must exist & be PRIVATE on your personal account.
bold "==> github sync (private)"
git -C "$VAULT" remote remove origin 2>/dev/null || true
git -C "$VAULT" remote add origin "$REPO_SSH"
if git -C "$VAULT" push -u origin main 2>/dev/null; then
  echo "   pushed → $REPO_SSH"
else
  cat <<EOF
   couldn't push yet. create the repo first:
     • github.com → New repository → name 'throughline-vault' → set PRIVATE (it has your self-material) → create
     • then: git -C "$VAULT" push -u origin main
   (or set THROUGHLINE_VAULT_REPO to a repo you've already made.)
EOF
fi

cat <<EOF

$(bold "one manual step — turn on sync:")
  in Obsidian → Settings → Community plugins → Browse → install "Git" → enable it,
  then set auto-commit + auto-push. that keeps this vault backed up & synced everywhere.

$(bold "then point throughline at it:")
  open the app → vault → connect → $VAULT
EOF
