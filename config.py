"""
Config manager — reads/writes ~/.shellsage/config.json
"""

import json
import os
import uuid
from pathlib import Path

CONFIG_DIR  = Path.home() / ".shellsage"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULTS = {
    "api_url":          "https://your-site.netlify.app",
    "shell":            None,
    "theme":            "cyberpunk",
    "typing_animation": True,
    "auto_copy":        False,
    "session_id":       None,
    "history_sync":     True,
}


def load() -> dict:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        cfg = DEFAULTS.copy()
        cfg["session_id"] = str(uuid.uuid4())
        save(cfg)
        return cfg
    try:
        with open(CONFIG_FILE) as f:
            cfg = json.load(f)
        updated = False
        for k, v in DEFAULTS.items():
            if k not in cfg:
                cfg[k] = v
                updated = True
        if not cfg.get("session_id"):
            cfg["session_id"] = str(uuid.uuid4())
            updated = True
        if updated:
            save(cfg)
        return cfg
    except Exception:
        cfg = DEFAULTS.copy()
        cfg["session_id"] = str(uuid.uuid4())
        save(cfg)
        return cfg


def save(cfg: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


def get(key: str, default=None):
    return load().get(key, default)


def set_value(key: str, value):
    cfg = load()
    cfg[key] = value
    save(cfg)


def get_shell() -> str:
    cfg = load()
    if cfg.get("shell"):
        return cfg["shell"]
    return os.environ.get("SHELL", "/bin/bash").split("/")[-1]


def get_api_url() -> str:
    cfg = load()
    url = cfg.get("api_url", "")
    if not url or "your-site" in url:
        raise EnvironmentError(
            "API URL not configured!\n"
            "Run: shellsage config --set api_url=https://your-site.netlify.app"
        )
    return url.rstrip("/")
