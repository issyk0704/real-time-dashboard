from datetime import time

from sessions import KILLZONES, Window, sessions_config


def test_window_includes_start_and_excludes_end():
    window = Window("London", time(2, 0), time(5, 0))
    assert window.contains(time(2, 0))
    assert window.contains(time(4, 59))
    assert not window.contains(time(5, 0))
    assert not window.contains(time(1, 59))


def test_window_ending_at_midnight_runs_to_end_of_day():
    asia = Window("Asia", time(20, 0), time(0, 0))
    assert asia.contains(time(20, 0))
    assert asia.contains(time(23, 59))
    assert not asia.contains(time(0, 0))
    assert not asia.contains(time(19, 59))


def test_sessions_config_lists_windows_as_hh_mm():
    config = sessions_config()
    assert [killzone["name"] for killzone in config["killzones"]] == [window.name for window in KILLZONES]
    assert config["killzones"][0] == {"name": "Asia", "start": "20:00", "end": "00:00"}
    assert {"name": "Macro", "start": "09:50", "end": "10:10"} in config["macros"]
