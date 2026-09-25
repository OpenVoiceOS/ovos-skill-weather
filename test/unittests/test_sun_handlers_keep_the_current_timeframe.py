"""Asking "when is the sunset?" must reach the current dialog, not the daily one.

`handle_sunset` and `handle_sunrise` set `intent_data.timeframe = DAILY`
before the dialog is chosen. They have to fetch the daily forecast, because
the sun times live there and nowhere else -- `WeatherReport.current` is
`hourly[0]` and the hourly block carries no `sunrise` or `sunset` -- but that
also made `get_dialog_for_timeframe` return `DailyDialog` every time. So the
eight `current_sun*.dialog` files that ship were unreachable from the handler,
`CurrentDialog.build_sunset_dialog` ran only from its own unit test, and a user
asking after sunset heard the daily wording instead of
`current_sunset_past_local`.

These cells drive the real handler on a real skill instance. Only two things
are stubbed: `_get_weather`, so no HTTP request is made, and `speak_dialog`,
so the dialog name can be read back. `_get_intent_data`,
`get_weather_for_intent`, `get_dialog_for_timeframe` and the dialog builders
all run for real, which is where the defect was.

The stubbed report is built by `WeatherReport` from a raw OpenMeteo-shaped
dict, not hand-assembled from mocks. That matters: `current` then genuinely
has `sunset is None` and `daily[0]` genuinely has a time, so a fix that simply
deleted the DAILY line would raise `TypeError` here instead of passing. A
mock with `sunset` set on everything would have hidden that.
"""
import datetime
import unittest
from zoneinfo import ZoneInfo
from pathlib import Path
from unittest.mock import patch

from ovos_utils.messagebus import FakeBus

from ovos_skill_weather import WeatherSkill
from ovos_skill_weather.weather_helpers import dialog as dialog_module
from ovos_skill_weather.weather_helpers.weather import WeatherReport

SKILL_ID = "ovos-skill-weather.openvoiceos"
ROOT = Path(__file__).resolve().parents[2]
CURRENT_DIALOGS = ROOT / "locale" / "en-US" / "dialog" / "current"
DAILY_DIALOGS = ROOT / "locale" / "en-US" / "dialog" / "daily"

TZ = "Europe/Lisbon"
ZONE = ZoneInfo(TZ)
DAY = "2024-03-15"
SUNRISE = f"{DAY}T06:30"
SUNSET = f"{DAY}T18:30"


def _raw_report():
    """An OpenMeteo-shaped report: sun times on the daily block only.

    The hourly block deliberately carries no sunrise or sunset, because the
    real one does not. `shortwave_radiation` is present because
    `Weather.__init__` derives the uv index from it when `uv_index_max` is
    absent, and `uv_index_max` is on the daily block for the same reason.
    """
    hours = [f"{DAY}T{h:02d}:00" for h in range(24)]
    return {
        "timezone": TZ,
        "hourly_units": {"temperature_2m": "°C"},
        "hourly": {
            "time": hours,
            "temperature_2m": [12.0] * 24,
            "weathercode": [0] * 24,
            "shortwave_radiation": [100.0] * 24,
        },
        "daily_units": {"temperature_2m_max": "°C"},
        "daily": {
            "time": [DAY],
            "temperature_2m_max": [18.0],
            "temperature_2m_min": [8.0],
            "weathercode": [0],
            "uv_index_max": [3.0],
            "sunrise": [SUNRISE],
            "sunset": [SUNSET],
        },
    }


class TestSunHandlersKeepTheCurrentTimeframe(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.report = WeatherReport(_raw_report())

    def setUp(self):
        self.skill = WeatherSkill()
        self.skill._startup(FakeBus(), SKILL_ID)
        self.spoken = []

    def _fire(self, handler_name, now):
        """Run the handler and return the dialog name it asked to speak."""
        from ovos_bus_client.message import Message

        def _capture(name, data=None, **kwargs):
            self.spoken.append((name, data))

        with patch.object(self.skill, "_get_weather", return_value=self.report), \
             patch.object(self.skill, "speak_dialog", _capture), \
             patch.object(dialog_module, "now_local", return_value=now), \
             patch.object(self.skill, "_display_sunrise_sunset", lambda *a, **k: None):
            getattr(self.skill, handler_name)(Message("test", {"utterance": "when is the sunset"}))
        self.assertTrue(self.spoken, f"{handler_name} spoke nothing")
        return self.spoken[-1][0]

    def test_the_report_puts_the_sun_times_only_on_the_daily_block(self):
        """The premise of the fix, asserted rather than assumed.

        If `current` ever gains the sun times, the handler no longer needs the
        daily forecast and this test should be revisited rather than deleted.
        """
        self.assertIsNone(self.report.current.sunset)
        self.assertIsNone(self.report.current.sunrise)
        self.assertIsNotNone(self.report.daily[0].sunset)
        self.assertIsNotNone(self.report.daily[0].sunrise)

    def test_after_sunset_the_user_hears_the_current_past_dialog(self):
        name = self._fire("handle_sunset", datetime.datetime(2024, 3, 15, 22, 0, tzinfo=ZONE))
        self.assertEqual(name, "current_sunset_past_local")
        self.assertTrue((CURRENT_DIALOGS / f"{name}.dialog").is_file(),
                        f"{name} names no dialog file that ships")

    def test_before_sunset_the_user_hears_the_current_future_dialog(self):
        name = self._fire("handle_sunset", datetime.datetime(2024, 3, 15, 12, 0, tzinfo=ZONE))
        self.assertEqual(name, "current_sunset_future_local")
        self.assertTrue((CURRENT_DIALOGS / f"{name}.dialog").is_file(),
                        f"{name} names no dialog file that ships")

    def test_after_sunrise_the_user_hears_the_current_past_dialog(self):
        name = self._fire("handle_sunrise", datetime.datetime(2024, 3, 15, 12, 0, tzinfo=ZONE))
        self.assertEqual(name, "current_sunrise_past_local")
        self.assertTrue((CURRENT_DIALOGS / f"{name}.dialog").is_file(),
                        f"{name} names no dialog file that ships")

    def test_before_sunrise_the_user_hears_the_current_future_dialog(self):
        name = self._fire("handle_sunrise", datetime.datetime(2024, 3, 15, 5, 0, tzinfo=ZONE))
        self.assertEqual(name, "current_sunrise_future_local")
        self.assertTrue((CURRENT_DIALOGS / f"{name}.dialog").is_file(),
                        f"{name} names no dialog file that ships")

    def test_the_daily_dialogs_still_ship_and_are_still_named_by_a_named_day(self):
        """The control for the four cells above.

        They assert the current dialog is reached when no day is named. If the
        handler had simply stopped using the daily forecast, a request that
        DOES name a day would break, and nothing above would say so. Here the
        intent carries a day, so the daily dialog must still win.
        """
        from ovos_bus_client.message import Message

        def _capture(name, data=None, **kwargs):
            self.spoken.append((name, data))

        with patch.object(self.skill, "_get_weather", return_value=self.report), \
             patch.object(self.skill, "speak_dialog", _capture), \
             patch.object(self.skill, "_display_sunrise_sunset", lambda *a, **k: None):
            msg = Message("test", {"utterance": "when is the sunset on friday",
                                   "day": "friday"})
            self.skill.handle_sunset(msg)
        self.assertTrue(self.spoken, "handle_sunset spoke nothing for a named day")
        name = self.spoken[-1][0]
        self.assertEqual(name, "daily_sunset_local")
        self.assertTrue((DAILY_DIALOGS / f"{name}.dialog").is_file())
