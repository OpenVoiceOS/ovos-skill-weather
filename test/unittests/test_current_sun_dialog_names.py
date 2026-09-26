"""The current sunrise and sunset dialogs keep the ``current`` prefix.

``CurrentDialog.build_sunset_dialog`` wrote ``self.name = "_sunset_past"``
where its three siblings write ``+=``, so once the sun had set the dialog
name lost its ``current`` prefix and named a file that does not ship
(``_sunset_past_local.dialog``). The skill then spoke the literal name.

The four cells are built the same way, with the clock patched to one side
of the event, so the three that were right are the control for the one
that was not. The file the name points at must exist under
``locale/en-US``.
"""
import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from ovos_skill_weather.weather_helpers import dialog as dialog_module
from ovos_skill_weather.weather_helpers.dialog import CurrentDialog

LOCALE = Path(__file__).resolve().parents[2] / "locale" / "en-US" / "dialog" / "current"

SUNRISE = datetime.datetime(2024, 3, 15, 6, 30)
SUNSET = datetime.datetime(2024, 3, 15, 18, 30)


def _dialog():
    config = SimpleNamespace(lang="en-US", country="United States")
    intent_data = SimpleNamespace(location=None, geolocation=None, config=config)
    weather = SimpleNamespace(sunrise=SUNRISE, sunset=SUNSET)
    return CurrentDialog(intent_data, weather)


@pytest.mark.parametrize("event, now, expected", [
    ("sunrise", datetime.datetime(2024, 3, 15, 5, 0), "current_sunrise_future_local"),
    ("sunrise", datetime.datetime(2024, 3, 15, 12, 0), "current_sunrise_past_local"),
    ("sunset", datetime.datetime(2024, 3, 15, 12, 0), "current_sunset_future_local"),
    ("sunset", datetime.datetime(2024, 3, 15, 22, 0), "current_sunset_past_local"),
])
def test_the_sun_dialog_name_keeps_the_current_prefix(event, now, expected):
    built = _dialog()
    with patch.object(dialog_module, "now_local", return_value=now):
        getattr(built, f"build_{event}_dialog")()
    assert built.name == expected
    assert (LOCALE / f"{expected}.dialog").is_file(), (
        f"{expected}: the name must be a dialog file that ships")
    assert "time" in built.data


def test_the_control_a_name_without_the_prefix_names_no_file():
    """The other direction: the defective name points at nothing."""
    assert not (LOCALE / "_sunset_past_local.dialog").exists()
