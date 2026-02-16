from __future__ import annotations

import atexit
import json
import os
import socket
import sys
import time
import threading
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import streamlit.config as st_config
import webview
from streamlit.web import bootstrap


def _base_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[1]


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _wait_server(url: str, timeout_s: float = 30.0) -> bool:
    end = time.time() + timeout_s
    checks = [f"{url}/_stcore/health", f"{url}/healthz"]
    while time.time() < end:
        for check_url in checks:
            try:
                with urlopen(check_url, timeout=1.5) as resp:
                    if int(resp.status) == 200:
                        return True
            except HTTPError as e:
                # Keep waiting; health endpoint can be temporarily unavailable.
                if int(e.code) in (404, 503):
                    pass
            except URLError:
                pass
            except Exception:
                pass
        time.sleep(0.25)
    return False


def _run_streamlit_thread(app_path: Path, port: int, state: dict) -> threading.Thread:
    def _target() -> None:
        try:
            # Force production frontend and fixed bind options for desktop mode.
            st_config.set_option("global.developmentMode", False, "command-line argument or environment variable")
            st_config.set_option("server.port", int(port), "command-line argument or environment variable")
            st_config.set_option("server.address", "127.0.0.1", "command-line argument or environment variable")
            st_config.set_option("server.headless", True, "command-line argument or environment variable")
            st_config.set_option("browser.serverAddress", "127.0.0.1", "command-line argument or environment variable")
            st_config.set_option("browser.serverPort", int(port), "command-line argument or environment variable")
            st_config.set_option("server.fileWatcherType", "none", "command-line argument or environment variable")

            # Streamlit tries to register POSIX signal handlers.
            # In desktop mode we run it in a worker thread, so disable this step.
            bootstrap._set_up_signal_handler = lambda _server: None  # type: ignore[attr-defined]
            bootstrap.run(
                str(app_path),
                False,
                [],
                {
                    "server.headless": True,
                    "server.address": "127.0.0.1",
                    "server.port": port,
                    "browser.gatherUsageStats": False,
                    "global.developmentMode": False,
                    "server.fileWatcherType": "none",
                },
            )
        except Exception as exc:
            state["error"] = repr(exc)

    th = threading.Thread(target=_target, name="streamlit-main", daemon=True)
    th.start()
    return th


def _is_trial_expired(base: Path) -> bool:
    policy_path = base / "src" / "trial_policy.json"
    if not policy_path.exists():
        return False
    try:
        raw = json.loads(policy_path.read_text(encoding="utf-8"))
        expires_utc = str(raw.get("expires_utc", "")).strip()
        if not expires_utc:
            return False
        if expires_utc.endswith("Z"):
            expires_utc = expires_utc[:-1] + "+00:00"
        dt_exp = datetime.fromisoformat(expires_utc)
        return datetime.now(timezone.utc) >= dt_exp.astimezone(timezone.utc)
    except Exception:
        return False


def main() -> int:
    base = _base_dir()
    app_path = base / "src" / "app.py"
    if not app_path.exists():
        raise FileNotFoundError(f"Streamlit app not found: {app_path}")
    if _is_trial_expired(base):
        return 0

    os.chdir(base)
    os.environ["WATERDIN_NATIVE"] = "1"
    os.environ["STREAMLIT_GLOBAL_DEVELOPMENT_MODE"] = "false"
    os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
    port = _find_free_port()
    url = f"http://127.0.0.1:{port}"
    os.environ["BROWSER"] = "none"
    state: dict = {}
    _run_streamlit_thread(app_path, port, state)
    atexit.register(lambda: None)

    if not _wait_server(url):
        details = state.get("error", "причина не получена")
        raise RuntimeError(f"Не удалось запустить локальный сервер приложения. Детали: {details}")

    window = webview.create_window(
        "Waterdin",
        url=url,
        width=1360,
        height=900,
        min_size=(1100, 720),
    )

    webview.start(debug=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
