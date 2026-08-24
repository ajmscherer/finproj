# finproj - demo-warning shown only on remote / hosted runtimes
# Copyright (C) 2025-2026 Alex Scherer

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "gui"))
sys.path.insert(0, str(PROJECT_ROOT / "code"))


class HostnameIsLocalTest(unittest.TestCase):
    def setUp(self) -> None:
        import app as gui_app

        self.fn = gui_app._hostname_is_local

    def test_loopback_and_localhost(self) -> None:
        for host in (
            "",
            "localhost",
            "localhost:8501",
            "127.0.0.1",
            "127.0.0.1:8501",
            "::1",
            "[::1]",
            "0.0.0.0",
        ):
            self.assertTrue(self.fn(host), host)

    def test_private_lan(self) -> None:
        self.assertTrue(self.fn("192.168.1.10"))
        self.assertTrue(self.fn("10.0.0.5:8501"))
        self.assertTrue(self.fn("macbook.local"))

    def test_public_host_is_remote(self) -> None:
        self.assertFalse(self.fn("demo.example.com"))
        self.assertFalse(self.fn("app-name.streamlit.app"))
        self.assertFalse(self.fn("8.8.8.8"))


class RuntimeIsLocalTest(unittest.TestCase):
    def setUp(self) -> None:
        import app as gui_app

        self.app = gui_app

    def test_demo_env_forces_remote(self) -> None:
        with patch.dict(os.environ, {"RUN_REMOTE": "1"}, clear=False):
            self.assertFalse(self.app._runtime_is_local())

    def test_demo_env_off_forces_local(self) -> None:
        with patch.dict(os.environ, {"RUN_REMOTE": "0"}, clear=False):
            self.assertTrue(self.app._runtime_is_local())


if __name__ == "__main__":
    unittest.main()
