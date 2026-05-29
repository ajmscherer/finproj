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

PORT=8501
if lsof -iTCP:"$PORT" -sTCP:LISTEN -t >/dev/null 2>&1; then
  echo "Port $PORT is already in use (another Streamlit instance may be running)." >&2
  echo "Stop the other app or run: $0 --server.port 8502" >&2
  exit 1
fi

exec "$PYTHON" -m streamlit run gui/app.py --server.address localhost --server.headless false "$@"
