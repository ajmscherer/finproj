# finproj - back-compat Streamlit entry (GUI lives in gui/v1)
# Copyright (C) 2025-2026 Alex Scherer
#
# Prefer: streamlit run gui/v1/app.py
# This file keeps older launchers working.

from __future__ import annotations

import runpy
import sys
from pathlib import Path

_V1_APP = Path(__file__).resolve().parent / "v1" / "app.py"
sys.path.insert(0, str(_V1_APP.parent))
runpy.run_path(str(_V1_APP), run_name="__main__")
