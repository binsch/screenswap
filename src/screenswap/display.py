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
_DISP_CHANGE_RESTART = 1

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

    # Stage non-primary monitors first, then primary — some drivers require this order
    for entry, live_mon in sorted(matched, key=lambda p: p[0]["is_primary"]):
        dm = _DEVMODE()
        dm.dmSize = ctypes.sizeof(_DEVMODE)
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
        if result == _DISP_CHANGE_RESTART:
            warnings.append(
                f"Monitor {entry['hardware_id']}: a system restart is required for the change to take effect."
            )
        elif result != _DISP_CHANGE_SUCCESSFUL:
            raise RuntimeError(
                f"Failed to stage monitor {entry['hardware_id']}: Windows error {result}"
            )

    for extra in extras:
        dm = _DEVMODE()
        dm.dmSize = ctypes.sizeof(_DEVMODE)
        dm.dmPosition.x = extra.position_x
        dm.dmPosition.y = extra.position_y
        dm.dmFields = _DM_POSITION
        result = _user32.ChangeDisplaySettingsExA(
            extra.device_name.encode(), ctypes.byref(dm), None,
            _CDS_UPDATEREGISTRY | _CDS_NORESET, None,
        )
        if result not in (_DISP_CHANGE_SUCCESSFUL, _DISP_CHANGE_RESTART):
            warnings.append(
                f"Monitor {extra.hardware_id} could not be repositioned: Windows error {result}"
            )

    _user32.ChangeDisplaySettingsExA(None, None, None, 0, None)
    return warnings
