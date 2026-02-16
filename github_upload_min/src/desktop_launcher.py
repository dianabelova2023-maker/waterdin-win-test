from __future__ import annotations

import os
import sys
from pathlib import Path

from streamlit.web.cli import main as streamlit_main


def _base_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[1]


def run() -> int:
    base = _base_dir()
    app_path = base / "src" / "app.py"
    os.chdir(base)
    sys.argv = [
        "streamlit",
        "run",
        str(app_path),
        "--server.headless=false",
        "--server.address=127.0.0.1",
        "--server.port=8501",
        "--browser.gatherUsageStats=false",
        "--global.developmentMode=false",
    ]
    return int(streamlit_main() or 0)


if __name__ == "__main__":
    raise SystemExit(run())
