#!/usr/bin/env bash
# Uni-Adblock local installer: review the checked-out source before elevation.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is required. Install it using your OS package manager." >&2
  exit 1
fi
if [[ ! -f uniadblock.py || ! -f sources.json ]]; then
  echo "Run this script from an extracted official repository archive." >&2
  exit 1
fi
echo "Starting local Uni-Adblock. Review source and back up your hosts file before writing."
exec python3 uniadblock.py "$@"
