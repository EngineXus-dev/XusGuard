#!/usr/bin/env bash
# XusGuard - EngineXus-dev: local-only launcher (no downloads or package installs).
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3.10+ is required. Install it manually using your OS package manager." >&2
  exit 1
fi
if [[ ! -f uniadblock.py || ! -f sources.json ]]; then
  echo "Extract the complete XusGuard repository before starting." >&2
  exit 1
fi
echo "Starting local XusGuard. Back up your system hosts file before changes."
exec python3 uniadblock.py "$@"
