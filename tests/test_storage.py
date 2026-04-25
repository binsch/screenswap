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
