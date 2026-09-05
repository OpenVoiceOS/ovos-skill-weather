"""End-to-end intent routing tests for the en-US locale.

The weather skill is network-bound: its handlers query a live weather API
(Open-Meteo) and a geolocation API. These tests assert intent ROUTING and a
spoken response on the message bus only -- no live network is required.

To keep the suite deterministic and offline, the two network boundaries are
patched for the duration of the tests:

* ``get_geolocation`` returns a fixed location (so datetime/timezone resolution,
  which happens outside the handler's network try-block, never touches the
  network and never raises), and
* ``get_report`` raises ``ConnectionError`` (so ``_get_weather`` falls into its
  generic error branch, speaks the "can't get forecast" dialog and returns
  ``None``).

The skill still routes through the full intent chain in that error branch and
speaks, so routing is fully exercised without depending on -- or hanging on --
live API responses. A ``pytest-timeout`` safety net fails any future hang fast
instead of stalling the whole job.

Every intent here is a padacioso ``.intent`` file; the skill carries no
adapt ``IntentBuilder`` registrations.
"""
import re
import unittest
from unittest.mock import patch

import pytest
from ovos_bus_client.message import Message
from ovos_bus_client.session import Session
from ovoscope import CaptureSession, get_minicroft

SKILL_ID = "ovos-skill-weather.openvoiceos"
LANG = "en-US"


def _matches_intent(msg_type: str, skill_id: str, intent_file: str) -> bool:
    """Check whether ``msg_type`` is the matched-intent event for
    ``intent_file`` (eg. ``current_weather.intent``), tolerant of which
    pipeline tier matched it.

    Compare case-insensitively against the basename with the ``.intent``
    extension stripped from both sides, rather than pinning one wire format.
    """
    prefix = f"{skill_id}:"
    if not msg_type.startswith(prefix):
        return False
    observed = msg_type[len(prefix):]
    observed_base = observed.rsplit(".", 1)[0] if observed.endswith(".intent") else observed
    expected_base = intent_file.rsplit(".", 1)[0]
    norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())
    return norm(observed_base) == norm(expected_base)

# Per-test hard ceiling: any live-network regression or hang fails the test
# instead of stalling until the CI job is cancelled.
pytestmark = pytest.mark.timeout(300)

# Static geolocation so timezone/datetime resolution (done outside the handler's
# network try-block) stays offline and never raises.
_FAKE_GEOLOCATION = {
    "city": "London",
    "region": "England",
    "country": "United Kingdom",
    "latitude": 51.5074,
    "longitude": -0.1278,
    "timezone": "Europe/London",
}


def _raise_no_network(*_args, **_kwargs):
    raise ConnectionError("network disabled in e2e routing tests")


class TestWeatherIntentsEnUS(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.minicroft = get_minicroft([SKILL_ID])
        # Patch the two network boundaries so handlers run offline and
        # deterministically: geolocation returns a fixed dict (never raises,
        # never hits the network), and the weather report call fails fast so the
        # skill takes its already-tested error branch and still routes + speaks.
        cls._patchers = [
            patch(
                "ovos_skill_weather.weather_helpers.intent.get_geolocation",
                return_value=dict(_FAKE_GEOLOCATION),
            ),
            patch("ovos_skill_weather.get_report", side_effect=_raise_no_network),
        ]
        for p in cls._patchers:
            p.start()

    @classmethod
    def tearDownClass(cls):
        for p in getattr(cls, "_patchers", []):
            p.stop()
        if getattr(cls, "minicroft", None):
            cls.minicroft.stop()

    def _run(self, text):
        session = Session("test-session")
        session.lang = LANG
        session.pipeline = [
            "ovos-adapt-pipeline-plugin-high",
            "ovos-padacioso-pipeline-plugin-high",
            "ovos-adapt-pipeline-plugin-medium",
            "ovos-padacioso-pipeline-plugin-medium",
            "ovos-adapt-pipeline-plugin-low",
        ]
        utterance = Message(
            "recognizer_loop:utterance",
            {"utterances": [text], "lang": LANG},
            {"session": session.serialize(), "source": "A", "destination": "B"},
        )
        capture = CaptureSession(self.minicroft)
        capture.capture(utterance, timeout=30)
        return capture.finish()

    def _assert_intent(self, text, intent):
        self._assert_intent_any(text, [intent])

    def _assert_intent_any(self, text, intents):
        messages = self._run(text)
        types = [m.msg_type for m in messages]
        self.assertTrue(
            any(_matches_intent(t, SKILL_ID, intent) for t in types for intent in intents),
            f"no message routed to {SKILL_ID}:{intents} ({types})",
        )
        self.assertTrue(any("speak" in t for t in types))

    # -- padacioso intents (.intent files) --------------------------------

    def test_tell_me_the_weather(self):
        self._assert_intent("can you tell me the weather", "current_weather.intent")

    def test_hourly_forecast(self):
        self._assert_intent("what's the forecast at 1 pm", "hourly_forecast.intent")

    def test_weather_alerts_tomorrow(self):
        self._assert_intent("any weather alerts for tomorrow", "daily_forecast.intent")

    def test_what_is_the_temperature(self):
        self._assert_intent("what is the temperature", "current_temperature.intent")

    def test_current_humidity(self):
        self._assert_intent("current humidity", "humidity.intent")

    def test_sunrise_time(self):
        self._assert_intent("sunrise time", "sunrise.intent")

    def test_sunset_time(self):
        self._assert_intent("sunset time", "sunset.intent")

    def test_do_i_need_an_umbrella(self):
        self._assert_intent("do I need an umbrella tomorrow", "is_rain.intent")

    def test_roads_snowy(self):
        self._assert_intent("are roads expected to be snowy", "is_snow.intent")

    def test_clear_skies(self):
        self._assert_intent("can I expect clear skies", "is_clear.intent")

    def test_is_it_cloudy(self):
        self._assert_intent("will it be cloudy today", "is_cloudy.intent")

    def test_is_it_cloudy_tomorrow_in_location(self):
        self._assert_intent("will it be cloudy tomorrow in Paris", "is_cloudy.intent")

    def test_is_it_cloudy_does_not_tie_with_is_clear(self):
        """``is_clear`` and ``is_cloudy`` are separate padacioso intents;
        "overcast", "gloomy", "gray" and "any cloud cover" live only in
        ``is_cloudy.intent`` (their true semantic group) so this phrase
        does not tie against ``is_clear.intent``.
        """
        self._assert_intent("is it cloudy", "is_cloudy.intent")

    def test_is_it_hot(self):
        self._assert_intent("is it hot", "is_hot.intent")

    def test_is_it_hot_or_cold_with_location(self):
        self._assert_intent("is it hot today in Lawrence kansas", "is_hot.intent")

    def test_will_it_be_cold(self):
        self._assert_intent("will it be cold tomorrow", "is_cold.intent")

    def test_general_weather(self):
        self._assert_intent(
            "what is the weather forecast for today in celsius", "weather.intent"
        )

    def test_weather(self):
        # bare "weather" is claimed by current_weather.intent, not
        # weather.intent: the latter's location-bearing templates require
        # either "forecast" or "in {location}" so the two files never tie
        # on this phrase.
        self._assert_intent("weather", "current_weather.intent")

    def test_forecast(self):
        self._assert_intent("forecast", "weather.intent")
