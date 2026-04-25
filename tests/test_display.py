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
