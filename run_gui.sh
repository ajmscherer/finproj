#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [[ -f .venv/bin/activate ]]; then
  # shellcheck source=/dev/null
  source .venv/bin/activate
fi

if command -v python3 &>/dev/null; then
  PYTHON=python3
elif command -v python &>/dev/null; then
  PYTHON=python
else
  echo "Error: Python not found. Install Python 3.10+ and try again." >&2
  exit 1
fi

if ! "$PYTHON" -c "import streamlit" 2>/dev/null; then
  echo "Installing GUI dependencies from requirements-gui.txt..."
  "$PYTHON" -m pip install -r requirements-gui.txt
fi

exec "$PYTHON" -m streamlit run gui/app.py --server.address localhost "$@"
