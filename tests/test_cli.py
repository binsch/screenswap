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
