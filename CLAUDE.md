# screenswap

Windows monitor layout manager. Saves and restores display configurations (resolution, position, refresh rate, orientation, primary monitor) by name.

## Commands

```bash
python -m pytest          # run tests (use this, not `pytest` — not on PATH)
screenswap save <name>    # save current layout
screenswap load <name>    # apply a saved layout
screenswap list
screenswap delete <name>
```

## Architecture

Three modules, one responsibility each:

- `src/screenswap/storage.py` — JSON read/write to `~/.screenswap/<name>.json`. Pure Python, no Windows API.
- `src/screenswap/display.py` — Windows display API via `ctypes` (stdlib). Reads live monitor config; applies saved layouts.
- `src/screenswap/cli.py` — `click` group wiring the above together.

## Key technical decisions

**ctypes over pywin32**: No external dependency for the Windows API layer. Structs are defined explicitly so field names and offsets are known.

**DEVMODE built fresh in `apply_layout`**: Do NOT call `EnumDisplaySettingsA` before `ChangeDisplaySettingsExA` in the staging loop. `EnumDisplaySettingsA` overwrites `dm.dmSize` with the driver's own value, causing `ChangeDisplaySettingsExA` to return `DISP_CHANGE_FAILED (-1)`. Build the DEVMODE from scratch with only the fields needed.

**Non-primary monitors staged first**: Some drivers require non-primary monitors to be staged before the primary (`CDS_SET_PRIMARY`). The matched list is sorted by `is_primary` ascending before staging.

**Monitor identity**: Matched by `hardware_id` (extracted from `DeviceID` e.g. `MONITOR\SAM711A\{...}` → `SAM711A`). Falls back to `width × height`. `DeviceString` is unreliable (often `"Generic PnP Monitor"`).

**Extra monitor handling**: If more monitors are connected than in the saved layout, extras are repositioned to the right of the rightmost saved monitor before applying, to avoid Windows rejecting the config due to overlapping areas.

## Layout file format

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
    }
  ]
}
```

Layouts live in `~/.screenswap/` — never in the repo.

## Testing

Tests use `pytest-mock`. Display module tests cover pure helpers only (`_extract_hardware_id`, `_match_monitors`, `_rightmost_x`). CLI tests use `click.testing.CliRunner` with mocked `display` and `storage`. Windows API functions are tested end-to-end manually.

Error-path CLI tests use `CliRunner(mix_stderr=False)` and assert on `result.stderr`.

## Windows API staging pattern

```python
# For each monitor (non-primary first):
ChangeDisplaySettingsExA(device, devmode, NULL, CDS_NORESET | CDS_UPDATEREGISTRY [| CDS_SET_PRIMARY], NULL)

# Commit all staged changes atomically:
ChangeDisplaySettingsExA(NULL, NULL, NULL, 0, NULL)
```

`DISP_CHANGE_RESTART (1)` = accepted, restart required → warn user, don't raise.
`DISP_CHANGE_FAILED (-1)` = driver rejected → raise RuntimeError.
