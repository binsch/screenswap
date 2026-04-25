# screenswap — Design Spec

**Date:** 2026-04-25

## Overview

`screenswap` is a pip-installable Python CLI tool for saving and restoring Windows monitor layouts. Users configure their screens via Windows display settings, save the layout by name, and restore it later with a single command. Designed to be open-source and work across arbitrary multi-monitor setups.

---

## CLI Interface

```
screenswap save <name>      # capture current Windows display state and save
screenswap load <name>      # apply a saved layout
screenswap list             # show all saved layout names
screenswap delete <name>    # remove a saved layout
```

All errors go to stderr with a non-zero exit code. No interactive prompts — compatible with scripts and desktop shortcuts.

---

## Project Structure

```
screenswap/
├── pyproject.toml
├── .gitignore
├── README.md
└── src/
    └── screenswap/
        ├── __init__.py
        ├── cli.py        # click entry point
        ├── display.py    # Windows display API via pywin32
        └── storage.py    # JSON layout serialization to ~/.screenswap/
```

---

## Layout Storage

Layouts are saved to `~/.screenswap/<name>.json`. This directory is outside the repo — contributors' personal layouts never end up in version control.

### JSON Format

```json
{
  "name": "productivity",
  "saved_at": "2026-04-25T10:00:00",
  "monitors": [
    {
      "hardware_id": "SAM711A",
      "width": 3440,
      "height": 1440,
      "position_x": 0,
      "position_y": 0,
      "is_primary": true,
      "refresh_rate": 165,
      "orientation": 0
    },
    {
      "hardware_id": "GSM5BD3",
      "width": 2560,
      "height": 1440,
      "position_x": -2560,
      "position_y": 0,
      "is_primary": false,
      "refresh_rate": 165,
      "orientation": 0
    }
  ]
}
```

`hardware_id` is extracted from the `DeviceID` field returned by `EnumDisplayDevices` (e.g., `MONITOR\SAM711A\{...}` → `SAM711A`). This is stable across reboots and replugs, and is unique per monitor model. It does not rely on `DeviceString`, which commonly reports as `"Generic PnP Monitor"` and is unreliable.

---

## Monitor Identity Matching

On `load`, each saved monitor entry is matched to a live monitor using:

1. **`hardware_id`** — primary match, stable hardware identifier
2. **`width × height`** — fallback if hardware ID is not found (e.g., two identical monitors)

If any saved monitor cannot be matched, the entire load is aborted (no partial apply) with a clear error:

> `Monitor SAM711A (3440x1440) not found. Is it connected?`

---

## Extra Monitor Handling

If more monitors are connected than are present in the saved layout:

1. Unrecognised monitors are repositioned to a collision-free area (to the right of the rightmost monitor in the layout) before the layout is applied.
2. A message is printed:
   > `Monitor XYZ repositioned to avoid overlap. Consider running 'screenswap save <name>' to include it in this layout.`

This prevents Windows from rejecting the configuration due to overlapping monitor areas, while keeping the user informed.

---

## Windows API

Uses `pywin32` (`win32api`). Key calls:

- `EnumDisplayDevices(None, i, ...)` — enumerate adapters
- `EnumDisplayDevices(adapter_name, 0, ...)` — get monitor hardware ID
- `EnumDisplaySettingsEx(adapter_name, ENUM_CURRENT_SETTINGS, ...)` — read current DEVMODE (resolution, position, refresh rate, orientation)
- `ChangeDisplaySettingsEx(adapter_name, devmode, CDS_NORESET | CDS_UPDATEREGISTRY)` — stage each monitor change
- `ChangeDisplaySettingsEx(None, None, 0)` — commit all staged changes atomically

---

## Dependencies

- Python 3.8+
- `pywin32` — Windows display API
- `click` — CLI

---

## Packaging

Distributed as a pip package. Entry point in `pyproject.toml`:

```toml
[project.scripts]
screenswap = "screenswap.cli:main"
```

After `pip install screenswap`, the `screenswap` command is available system-wide. Can also be invoked via a Windows desktop shortcut pointing to a `.bat` wrapper.

---

## Error Handling Summary

| Situation | Behavior |
|---|---|
| `load` with unknown layout name | Error: `Layout "X" not found. Run 'screenswap list' to see saved layouts.` |
| Monitor in layout not connected | Error: `Monitor SAM711A (3440x1440) not found. Is it connected?` |
| Extra monitors connected | Reposition to safe area + advisory message |
| `ChangeDisplaySettingsEx` fails | Error with Windows error code and plain-English hint |
| `save` with existing name | Silent overwrite |

---

## Out of Scope (v1)

- Cross-platform support (Windows only)
- Per-layout taskbar configuration
- GUI
- Profiles with multiple named monitors of the same model
