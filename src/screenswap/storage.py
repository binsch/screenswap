from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

LAYOUTS_DIR = Path.home() / ".screenswap"


def save_layout(name: str, monitors: list[dict]) -> None:
    LAYOUTS_DIR.mkdir(exist_ok=True)
    path = LAYOUTS_DIR / f"{name}.json"
    path.write_text(json.dumps({
        "name": name,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "monitors": monitors,
    }, indent=2))


def load_layout(name: str) -> dict:
    path = LAYOUTS_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(name)
    return json.loads(path.read_text())


def list_layouts() -> list[str]:
    if not LAYOUTS_DIR.exists():
        return []
    return sorted(p.stem for p in LAYOUTS_DIR.glob("*.json"))


def delete_layout(name: str) -> None:
    path = LAYOUTS_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(name)
    path.unlink()
