#!/usr/bin/env bash
# XusGuard Desktop: local Tkinter. No remote execution or automatic privilege escalation.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3.10+ required." >&2
  exit 1
fi
if ! python3 -c "import tkinter" >/dev/null 2>&1; then
  echo "Tkinter is missing. Install python3-tk via your OS package manager." >&2
  exit 1
fi
exec python3 xusguard_gui.py "$@"
