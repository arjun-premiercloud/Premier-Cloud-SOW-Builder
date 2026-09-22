#!/usr/bin/env bash
set -euo pipefail
CONFIG_DIR="${GOOGLE_WORKSPACE_CLI_CONFIG_DIR:-$HOME/.config/gws}"
if ! command -v gws >/dev/null 2>&1; then
  command -v npm >/dev/null 2>&1 || { echo "gws: npm missing" >&2; exit 0; }
  npm install -g @googleworkspace/cli >/dev/null 2>&1 \
    || { echo "gws: install failed" >&2; exit 0; }
fi
if ! command -v gws >/dev/null 2>&1; then
  npm_bin="$(npm prefix -g 2>/dev/null)/bin"
  [ -x "$npm_bin/gws" ] && export PATH="$npm_bin:$PATH"
fi
command -v gws >/dev/null 2>&1 || { echo "gws: not on PATH" >&2; exit 0; }
echo "gws: $(gws --version 2>/dev/null | head -1)"
if [ -z "${GOOGLE_WORKSPACE_CLI_TOKEN:-}" ] \
   && [ -z "${GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE:-}" ] \
   && [ ! -f "$CONFIG_DIR/credentials.json" ] \
   && [ -n "${GOOGLE_WORKSPACE_CLI_CREDENTIALS:-}" ]; then
  mkdir -p "$CONFIG_DIR"
  ( umask 077; printf '%s' "$GOOGLE_WORKSPACE_CLI_CREDENTIALS" > "$CONFIG_DIR/credentials.json" )
  echo "gws: staged inline credential -> $CONFIG_DIR/credentials.json (0600)"
fi
status="$(gws auth status 2>/dev/null || true)"
user="$(printf '%s\n' "$status" | grep -o '"user": *"[^"]*"' | head -1 | sed 's/.*: *"//; s/"$//')"
valid="$(printf '%s\n' "$status" | grep -o '"token_valid": *[A-Za-z]*' | head -1 | sed 's/.*: *//')"
case "$valid" in true|True) echo "gws: authenticated as ${user:-unknown}" ;;
  *) echo "gws: NO valid credential" >&2 ;; esac
