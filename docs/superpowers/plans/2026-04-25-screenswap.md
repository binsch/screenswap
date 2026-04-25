# screenswap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a pip-installable Python CLI tool that saves and restores Windows monitor layouts by name.

**Architecture:** Three modules: `storage.py` handles JSON layout files in `~/.screenswap/`, `display.py` reads and applies Windows monitor configuration via `ctypes` (stdlib, no extra dependency), and `cli.py` wires them together with `click`. Pure logic in `display.py` is unit-tested; Windows API calls are exercised manually via the CLI.

**Tech Stack:** Python 3.8+, click, pytest, pytest-mock (ctypes is stdlib)

---

## File Map

| File | Responsibility |
|---|---|
| `pyproject.toml` | Package metadata, dependencies, `screenswap` entry point |
| `src/screenswap/__init__.py` | Package marker |
| `src/screenswap/storage.py` | Save/load/list/delete layouts as JSON in `~/.screenswap/` |
| `src/screenswap/display.py` | ctypes structs, pure helpers, `get_current_monitors`, `apply_layout` |
| `src/screenswap/cli.py` | `click` group with save/load/list/delete commands |
| `tests/__init__.py` | Test package marker |
| `tests/test_storage.py` | Full unit tests for storage (pure Python, `tmp_path`) |
| `tests/test_display.py` | Unit tests for pure helpers only (`_extract_hardware_id`, `_match_monitors`, `_rightmost_x`) |
| `tests/test_cli.py` | CLI integration tests via `CliRunner` with mocked storage + display |

---

## Task 1: Project scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `src/screenswap/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "screenswap"
version = "0.1.0"
description = "Save and restore Windows monitor layouts by name"
requires-python = ">=3.8"
dependencies = [
    "click",
]

[project.scripts]
screenswap = "screenswap.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["src/screenswap"]
```

- [ ] **Step 2: Create package and test directories**

```bash
mkdir -p src/screenswap tests
touch src/screenswap/__init__.py tests/__init__.py
```

- [ ] **Step 3: Install package in editable mode with test deps**

```bash
pip install -e . click pytest pytest-mock
```

Expected output ends with: `Successfully installed screenswap-0.1.0`

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml src/ tests/
git commit -m "chore: project scaffold"
```

---

## Task 2: Storage module

**Files:**
- Create: `src/screenswap/storage.py`
- Create: `tests/test_storage.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_storage.py`:

```python
import pytest
from screenswap.storage import delete_layout, list_layouts, load_layout, save_layout

SAMPLE_MONITORS = [
    {
        "hardware_id": "SAM711A",
        "width": 3440,
        "height": 1440,
        "position_x": 0,
        "position_y": 0,
        "is_primary": True,
        "refresh_rate": 165,
        "orientation": 0,
    }
]


@pytest.fixture(autouse=True)
def layouts_dir(tmp_path, monkeypatch):
    monkeypatch.setattr("screenswap.storage.LAYOUTS_DIR", tmp_path)
    return tmp_path


def test_save_creates_json_file(layouts_dir):
    save_layout("test", SAMPLE_MONITORS)
    assert (layouts_dir / "test.json").exists()


def test_save_and_load_roundtrip():
    save_layout("productivity", SAMPLE_MONITORS)
    result = load_layout("productivity")
    assert result["name"] == "productivity"
    assert result["monitors"] == SAMPLE_MONITORS
    assert "saved_at" in result


def test_load_nonexistent_raises():
    with pytest.raises(FileNotFoundError):
        load_layout("nope")


def test_list_empty_returns_empty():
    assert list_layouts() == []


def test_list_returns_sorted_names():
    save_layout("zebra", SAMPLE_MONITORS)
    save_layout("alpha", SAMPLE_MONITORS)
    assert list_layouts() == ["alpha", "zebra"]


def test_save_overwrites_existing():
    save_layout("test", SAMPLE_MONITORS)
    updated = [{**SAMPLE_MONITORS[0], "width": 2560}]
    save_layout("test", updated)
    result = load_layout("test")
    assert result["monitors"][0]["width"] == 2560


def test_delete_removes_file(layouts_dir):
    save_layout("test", SAMPLE_MONITORS)
    delete_layout("test")
    assert not (layouts_dir / "test.json").exists()


def test_delete_nonexistent_raises():
    with pytest.raises(FileNotFoundError):
        delete_layout("nope")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_storage.py -v
```

Expected: `ModuleNotFoundError: No module named 'screenswap.storage'`

- [ ] **Step 3: Implement `storage.py`**

Create `src/screenswap/storage.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_storage.py -v
```

Expected: `8 passed`

- [ ] **Step 5: Commit**

```bash
git add src/screenswap/storage.py tests/test_storage.py
git commit -m "feat: storage module"
```

---

## Task 3: Display module

**Files:**
- Create: `src/screenswap/display.py`
- Create: `tests/test_display.py`

The pure helper functions (`_extract_hardware_id`, `_match_monitors`, `_rightmost_x`) are fully unit-tested. The Windows API functions (`get_current_monitors`, `apply_layout`) are implemented but tested manually via the CLI in Task 4.

- [ ] **Step 1: Write failing tests for pure helpers**

Create `tests/test_display.py`:

```python
import pytest
from screenswap.display import MonitorConfig, _extract_hardware_id, _match_monitors, _rightmost_x


def make_monitor(**kwargs) -> MonitorConfig:
    defaults = dict(
        hardware_id="SAM711A",
        device_name="\\\\.\\DISPLAY1",
        width=3440,
        height=1440,
        position_x=0,
        position_y=0,
        is_primary=True,
        refresh_rate=165,
        orientation=0,
    )
    defaults.update(kwargs)
    return MonitorConfig(**defaults)


# _extract_hardware_id

def test_extract_hardware_id_samsung():
    assert _extract_hardware_id("MONITOR\\SAM711A\\{4d36e96e}\\0000") == "SAM711A"


def test_extract_hardware_id_lg():
    assert _extract_hardware_id("MONITOR\\GSM5BD3\\{4d36e96e}\\0004") == "GSM5BD3"


def test_extract_hardware_id_malformed_returns_input():
    assert _extract_hardware_id("NODOTS") == "NODOTS"


# _match_monitors

def test_match_by_hardware_id():
    saved = [{"hardware_id": "SAM711A", "width": 3440, "height": 1440}]
    live = [make_monitor(hardware_id="SAM711A")]
    matched, extras = _match_monitors(saved, live)
    assert len(matched) == 1
    assert matched[0][1].hardware_id == "SAM711A"
    assert extras == []


def test_match_fallback_to_resolution():
    saved = [{"hardware_id": "UNKNOWN", "width": 3440, "height": 1440}]
    live = [make_monitor(hardware_id="SAM711A", width=3440, height=1440)]
    matched, extras = _match_monitors(saved, live)
    assert len(matched) == 1
    assert matched[0][1].hardware_id == "SAM711A"


def test_match_unmatched_raises():
    saved = [{"hardware_id": "SAM711A", "width": 3440, "height": 1440}]
    live = [make_monitor(hardware_id="OTHERHW", width=2560, height=1440)]
    with pytest.raises(RuntimeError, match="SAM711A"):
        _match_monitors(saved, live)


def test_match_extra_monitor_in_extras():
    saved = [{"hardware_id": "SAM711A", "width": 3440, "height": 1440}]
    extra = make_monitor(
        hardware_id="EXTRA", device_name="\\\\.\\DISPLAY3",
        width=1920, height=1080, is_primary=False,
    )
    live = [make_monitor(hardware_id="SAM711A"), extra]
    matched, extras = _match_monitors(saved, live)
    assert len(matched) == 1
    assert len(extras) == 1
    assert extras[0].hardware_id == "EXTRA"


def test_match_two_monitors_both_matched():
    saved = [
        {"hardware_id": "SAM711A", "width": 3440, "height": 1440},
        {"hardware_id": "GSM5BD3", "width": 2560, "height": 1440},
    ]
    live = [
        make_monitor(hardware_id="SAM711A"),
        make_monitor(hardware_id="GSM5BD3", device_name="\\\\.\\DISPLAY2",
                     width=2560, is_primary=False),
    ]
    matched, extras = _match_monitors(saved, live)
    assert len(matched) == 2
    assert extras == []


# _rightmost_x

def test_rightmost_x_single_monitor():
    saved = [{"position_x": 0, "width": 3440}]
    assert _rightmost_x(saved) == 3440


def test_rightmost_x_side_by_side():
    saved = [
        {"position_x": 0, "width": 3440},
        {"position_x": -2560, "width": 2560},
    ]
    assert _rightmost_x(saved) == 3440


def test_rightmost_x_stacked():
    saved = [
        {"position_x": 0, "width": 2560},
        {"position_x": -440, "width": 3440},
    ]
    assert _rightmost_x(saved) == 3000
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_display.py -v
```

Expected: `ModuleNotFoundError: No module named 'screenswap.display'`

- [ ] **Step 3: Implement `display.py`**

Create `src/screenswap/display.py`:

```python
from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass


class _POINTL(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class _DEVMODE(ctypes.Structure):
    _fields_ = [
        ("dmDeviceName", ctypes.c_char * 32),
        ("dmSpecVersion", wintypes.WORD),
        ("dmDriverVersion", wintypes.WORD),
        ("dmSize", wintypes.WORD),
        ("dmDriverExtra", wintypes.WORD),
        ("dmFields", wintypes.DWORD),
        ("dmPosition", _POINTL),
        ("dmDisplayOrientation", wintypes.DWORD),
        ("dmDisplayFixedOutput", wintypes.DWORD),
        ("dmColor", ctypes.c_short),
        ("dmDuplex", ctypes.c_short),
        ("dmYResolution", ctypes.c_short),
        ("dmTTOption", ctypes.c_short),
        ("dmCollate", ctypes.c_short),
        ("dmFormName", ctypes.c_char * 32),
        ("dmLogPixels", wintypes.WORD),
        ("dmBitsPerPel", wintypes.DWORD),
        ("dmPelsWidth", wintypes.DWORD),
        ("dmPelsHeight", wintypes.DWORD),
        ("dmDisplayFlags", wintypes.DWORD),
        ("dmDisplayFrequency", wintypes.DWORD),
    ]


class _DISPLAY_DEVICE(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("DeviceName", ctypes.c_char * 32),
        ("DeviceString", ctypes.c_char * 128),
        ("StateFlags", wintypes.DWORD),
        ("DeviceID", ctypes.c_char * 128),
        ("DeviceKey", ctypes.c_char * 128),
    ]


_ENUM_CURRENT_SETTINGS = -1
_ATTACHED = 0x00000001
_PRIMARY = 0x00000004
_DM_POSITION = 0x00000020
_DM_PELSWIDTH = 0x00080000
_DM_PELSHEIGHT = 0x00100000
_DM_DISPLAYFREQUENCY = 0x00400000
_DM_DISPLAYORIENTATION = 0x00000080
_CDS_UPDATEREGISTRY = 0x00000001
_CDS_NORESET = 0x10000000
_CDS_SET_PRIMARY = 0x00000010
_DISP_CHANGE_SUCCESSFUL = 0

_user32 = ctypes.windll.user32


@dataclass
class MonitorConfig:
    hardware_id: str
    device_name: str
    width: int
    height: int
    position_x: int
    position_y: int
    is_primary: bool
    refresh_rate: int
    orientation: int


def _extract_hardware_id(device_id: str) -> str:
    parts = device_id.split("\\")
    return parts[1] if len(parts) >= 2 else device_id


def _match_monitors(
    saved: list[dict], live: list[MonitorConfig]
) -> tuple[list[tuple[dict, MonitorConfig]], list[MonitorConfig]]:
    matched: list[tuple[dict, MonitorConfig]] = []
    remaining = list(live)

    for entry in saved:
        match = next((m for m in remaining if m.hardware_id == entry["hardware_id"]), None)
        if match is None:
            match = next(
                (m for m in remaining
                 if m.width == entry["width"] and m.height == entry["height"]),
                None,
            )
        if match is None:
            raise RuntimeError(
                f"Monitor {entry['hardware_id']} ({entry['width']}x{entry['height']}) "
                "not found. Is it connected?"
            )
        matched.append((entry, match))
        remaining.remove(match)

    return matched, remaining


def _rightmost_x(saved: list[dict]) -> int:
    return max(s["position_x"] + s["width"] for s in saved)


def get_current_monitors() -> list[MonitorConfig]:
    monitors = []
    i = 0
    while True:
        adapter = _DISPLAY_DEVICE()
        adapter.cb = ctypes.sizeof(_DISPLAY_DEVICE)
        if not _user32.EnumDisplayDevicesA(None, i, ctypes.byref(adapter), 0):
            break
        if adapter.StateFlags & _ATTACHED:
            monitor_dd = _DISPLAY_DEVICE()
            monitor_dd.cb = ctypes.sizeof(_DISPLAY_DEVICE)
            _user32.EnumDisplayDevicesA(adapter.DeviceName, 0, ctypes.byref(monitor_dd), 0)

            dm = _DEVMODE()
            dm.dmSize = ctypes.sizeof(_DEVMODE)
            _user32.EnumDisplaySettingsA(
                adapter.DeviceName, _ENUM_CURRENT_SETTINGS, ctypes.byref(dm)
            )

            device_id = monitor_dd.DeviceID.decode(errors="replace")
            monitors.append(MonitorConfig(
                hardware_id=_extract_hardware_id(device_id),
                device_name=adapter.DeviceName.decode(),
                width=dm.dmPelsWidth,
                height=dm.dmPelsHeight,
                position_x=dm.dmPosition.x,
                position_y=dm.dmPosition.y,
                is_primary=bool(adapter.StateFlags & _PRIMARY),
                refresh_rate=dm.dmDisplayFrequency,
                orientation=dm.dmDisplayOrientation,
            ))
        i += 1
    return monitors


def apply_layout(saved_monitors: list[dict]) -> list[str]:
    live = get_current_monitors()
    matched, extras = _match_monitors(saved_monitors, live)

    warnings: list[str] = []
    x_cursor = _rightmost_x(saved_monitors)
    for extra in extras:
        extra.position_x = x_cursor
        extra.position_y = 0
        x_cursor += extra.width
        warnings.append(
            f"Monitor {extra.hardware_id} repositioned to avoid overlap. "
            "Consider running 'screenswap save <name>' to include it in this layout."
        )

    for entry, live_mon in matched:
        dm = _DEVMODE()
        dm.dmSize = ctypes.sizeof(_DEVMODE)
        _user32.EnumDisplaySettingsA(
            live_mon.device_name.encode(), _ENUM_CURRENT_SETTINGS, ctypes.byref(dm)
        )
        dm.dmPelsWidth = entry["width"]
        dm.dmPelsHeight = entry["height"]
        dm.dmPosition.x = entry["position_x"]
        dm.dmPosition.y = entry["position_y"]
        dm.dmDisplayFrequency = entry["refresh_rate"]
        dm.dmDisplayOrientation = entry["orientation"]
        dm.dmFields = (
            _DM_PELSWIDTH | _DM_PELSHEIGHT | _DM_POSITION |
            _DM_DISPLAYFREQUENCY | _DM_DISPLAYORIENTATION
        )
        flags = _CDS_UPDATEREGISTRY | _CDS_NORESET
        if entry["is_primary"]:
            flags |= _CDS_SET_PRIMARY
        result = _user32.ChangeDisplaySettingsExA(
            live_mon.device_name.encode(), ctypes.byref(dm), None, flags, None
        )
        if result != _DISP_CHANGE_SUCCESSFUL:
            raise RuntimeError(
                f"Failed to stage monitor {entry['hardware_id']}: Windows error {result}"
            )

    for extra in extras:
        dm = _DEVMODE()
        dm.dmSize = ctypes.sizeof(_DEVMODE)
        _user32.EnumDisplaySettingsA(
            extra.device_name.encode(), _ENUM_CURRENT_SETTINGS, ctypes.byref(dm)
        )
        dm.dmPosition.x = extra.position_x
        dm.dmPosition.y = extra.position_y
        dm.dmFields = _DM_POSITION
        _user32.ChangeDisplaySettingsExA(
            extra.device_name.encode(), ctypes.byref(dm), None,
            _CDS_UPDATEREGISTRY | _CDS_NORESET, None,
        )

    _user32.ChangeDisplaySettingsExA(None, None, None, 0, None)
    return warnings
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_display.py -v
```

Expected: `12 passed`

- [ ] **Step 5: Commit**

```bash
git add src/screenswap/display.py tests/test_display.py
git commit -m "feat: display module"
```

---

## Task 4: CLI

**Files:**
- Create: `src/screenswap/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write failing CLI tests**

Create `tests/test_cli.py`:

```python
import pytest
from click.testing import CliRunner

from screenswap.cli import main

SAMPLE_LAYOUT = {
    "name": "productivity",
    "saved_at": "2026-04-25T10:00:00",
    "monitors": [
        {
            "hardware_id": "SAM711A",
            "width": 3440,
            "height": 1440,
            "position_x": 0,
            "position_y": 0,
            "is_primary": True,
            "refresh_rate": 165,
            "orientation": 0,
        }
    ],
}


@pytest.fixture
def runner():
    return CliRunner()


# --- save ---

def test_save_success(runner, mocker):
    mock_monitor = mocker.MagicMock(
        hardware_id="SAM711A", width=3440, height=1440,
        position_x=0, position_y=0, is_primary=True,
        refresh_rate=165, orientation=0,
    )
    mocker.patch("screenswap.cli.display.get_current_monitors", return_value=[mock_monitor])
    mocker.patch("screenswap.cli.storage.save_layout")
    result = runner.invoke(main, ["save", "productivity"])
    assert result.exit_code == 0
    assert "saved" in result.output


def test_save_calls_storage_with_correct_data(runner, mocker):
    mock_monitor = mocker.MagicMock(
        hardware_id="SAM711A", width=3440, height=1440,
        position_x=0, position_y=0, is_primary=True,
        refresh_rate=165, orientation=0,
    )
    mocker.patch("screenswap.cli.display.get_current_monitors", return_value=[mock_monitor])
    mock_save = mocker.patch("screenswap.cli.storage.save_layout")
    runner.invoke(main, ["save", "productivity"])
    mock_save.assert_called_once_with("productivity", [{
        "hardware_id": "SAM711A", "width": 3440, "height": 1440,
        "position_x": 0, "position_y": 0, "is_primary": True,
        "refresh_rate": 165, "orientation": 0,
    }])


# --- list ---

def test_list_empty(runner, mocker):
    mocker.patch("screenswap.cli.storage.list_layouts", return_value=[])
    result = runner.invoke(main, ["list"])
    assert result.exit_code == 0
    assert "No saved layouts" in result.output


def test_list_with_layouts(runner, mocker):
    mocker.patch("screenswap.cli.storage.list_layouts", return_value=["gaming", "productivity"])
    result = runner.invoke(main, ["list"])
    assert result.exit_code == 0
    assert "gaming" in result.output
    assert "productivity" in result.output


# --- load ---

def test_load_success(runner, mocker):
    mocker.patch("screenswap.cli.storage.load_layout", return_value=SAMPLE_LAYOUT)
    mocker.patch("screenswap.cli.display.apply_layout", return_value=[])
    result = runner.invoke(main, ["load", "productivity"])
    assert result.exit_code == 0
    assert "applied" in result.output


def test_load_prints_warnings(runner, mocker):
    mocker.patch("screenswap.cli.storage.load_layout", return_value=SAMPLE_LAYOUT)
    mocker.patch(
        "screenswap.cli.display.apply_layout",
        return_value=["Monitor EXTRA repositioned to avoid overlap. Consider running 'screenswap save <name>' to include it in this layout."],
    )
    result = runner.invoke(main, ["load", "productivity"])
    assert result.exit_code == 0
    assert "repositioned" in result.output
    assert "applied" in result.output


def test_load_unknown_layout(runner, mocker):
    mocker.patch("screenswap.cli.storage.load_layout", side_effect=FileNotFoundError("nope"))
    result = runner.invoke(main, ["load", "nope"])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_load_missing_monitor(runner, mocker):
    mocker.patch("screenswap.cli.storage.load_layout", return_value=SAMPLE_LAYOUT)
    mocker.patch(
        "screenswap.cli.display.apply_layout",
        side_effect=RuntimeError("Monitor SAM711A (3440x1440) not found. Is it connected?"),
    )
    result = runner.invoke(main, ["load", "productivity"])
    assert result.exit_code == 1
    assert "not found" in result.output


# --- delete ---

def test_delete_success(runner, mocker):
    mocker.patch("screenswap.cli.storage.delete_layout")
    result = runner.invoke(main, ["delete", "productivity"])
    assert result.exit_code == 0
    assert "deleted" in result.output


def test_delete_unknown(runner, mocker):
    mocker.patch("screenswap.cli.storage.delete_layout", side_effect=FileNotFoundError("nope"))
    result = runner.invoke(main, ["delete", "nope"])
    assert result.exit_code == 1
    assert "not found" in result.output
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_cli.py -v
```

Expected: `ModuleNotFoundError: No module named 'screenswap.cli'`

- [ ] **Step 3: Implement `cli.py`**

Create `src/screenswap/cli.py`:

```python
from __future__ import annotations

import sys

import click

from . import display, storage


@click.group()
def main() -> None:
    pass


@main.command()
@click.argument("name")
def save(name: str) -> None:
    """Save current monitor layout."""
    monitors = display.get_current_monitors()
    monitor_dicts = [
        {
            "hardware_id": m.hardware_id,
            "width": m.width,
            "height": m.height,
            "position_x": m.position_x,
            "position_y": m.position_y,
            "is_primary": m.is_primary,
            "refresh_rate": m.refresh_rate,
            "orientation": m.orientation,
        }
        for m in monitors
    ]
    storage.save_layout(name, monitor_dicts)
    click.echo(f"Layout '{name}' saved ({len(monitors)} monitor(s)).")


@main.command("list")
def list_layouts() -> None:
    """List saved layouts."""
    layouts = storage.list_layouts()
    if not layouts:
        click.echo("No saved layouts. Run 'screenswap save <name>' to create one.")
        return
    for name in layouts:
        click.echo(name)


@main.command()
@click.argument("name")
def load(name: str) -> None:
    """Apply a saved layout."""
    try:
        layout = storage.load_layout(name)
    except FileNotFoundError:
        click.echo(
            f"Layout '{name}' not found. Run 'screenswap list' to see saved layouts.",
            err=True,
        )
        sys.exit(1)

    try:
        warnings = display.apply_layout(layout["monitors"])
    except RuntimeError as e:
        click.echo(str(e), err=True)
        sys.exit(1)

    for warning in warnings:
        click.echo(warning)
    click.echo(f"Layout '{name}' applied.")


@main.command()
@click.argument("name")
def delete(name: str) -> None:
    """Delete a saved layout."""
    try:
        storage.delete_layout(name)
    except FileNotFoundError:
        click.echo(
            f"Layout '{name}' not found. Run 'screenswap list' to see saved layouts.",
            err=True,
        )
        sys.exit(1)
    click.echo(f"Layout '{name}' deleted.")
```

- [ ] **Step 4: Run all tests**

```bash
pytest -v
```

Expected: `21 passed`

- [ ] **Step 5: Smoke test the entry point**

```bash
screenswap --help
```

Expected output:
```
Usage: screenswap [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  delete  Delete a saved layout.
  list    List saved layouts.
  load    Apply a saved layout.
  save    Save current monitor layout.
```

- [ ] **Step 6: End-to-end manual test**

```bash
screenswap save productivity
screenswap list
screenswap load productivity
```

Expected:
```
Layout 'productivity' saved (2 monitor(s)).
productivity
Layout 'productivity' applied.
```

Verify monitors did not visually change (loaded same layout that was already active).

- [ ] **Step 7: Commit**

```bash
git add src/screenswap/cli.py tests/test_cli.py
git commit -m "feat: CLI commands"
```
