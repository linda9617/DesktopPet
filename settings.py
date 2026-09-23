"""Tiny JSON settings store under %APPDATA%\\deskpet."""

from __future__ import annotations

import json
import os
from pathlib import Path

DEFAULTS = {
    "skin": "cat",
    "pos_x": None,
    "pos_y": None,
    "scale": 1.0,
    "idle_yawn_s": 40.0,
    "idle_sleep_s": 75.0,
    "always_on_top": True,
}


def config_path() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home())
    return Path(base) / "deskpet" / "settings.json"


def load() -> dict:
    data = dict(DEFAULTS)
    path = config_path()
    try:
        if path.is_file():
            stored = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(stored, dict):
                data.update({k: v for k, v in stored.items() if k in DEFAULTS})
    except (OSError, ValueError):
        pass
    return data


def save(data: dict) -> None:
    path = config_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {k: data.get(k, v) for k, v in DEFAULTS.items()}
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError:
        pass
