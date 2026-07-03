"""End-to-end intent-routing tests for ovos-skill-weather (en-US).

Each case feeds an utterance through a MiniCroft stack and asserts it routes
to the expected ``.intent`` handler. Coverage spans current conditions, the
precipitation forecast, temperature queries with a ``{location}`` slot, and the
multi-day forecast variants.

Run: pytest test/end2end/ -v
"""
import time
from unittest import TestCase

from ovos_bus_client.message import Message
from ovos_bus_client.session import Session
from ovoscope import get_minicroft

SKILL_ID = "ovos-skill-weather.openvoiceos"
LANG = "en-US"

# Exact expansions score conf 1.0 (the -high band); the {location} slot
# variants land lower, so register all three padacioso bands.
PIPELINE = [
    "ovos-padacioso-pipeline-plugin-high",
    "ovos-padacioso-pipeline-plugin-medium",
    "ovos-padacioso-pipeline-plugin-low",
]


class _IntentRoutingMixin:
    """Shared MiniCroft setup for padacioso intent routing."""

    @classmethod
    def setUpClass(cls):
        cls.minicroft = get_minicroft([SKILL_ID])

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "minicroft", None):
            cls.minicroft.stop()

    def _assert_intent(self, utterance: str, intent_file: str):
        intent_msg_type = f"{SKILL_ID}:{intent_file}"
        matched = []
        handler = lambda msg: matched.append(msg)
        self.minicroft.bus.on(intent_msg_type, handler)
        try:
            session = Session(f"e2e-en_us-{intent_file}-{hash(utterance)}")
            session.lang = LANG
            session.pipeline = PIPELINE
            self.minicroft.bus.emit(Message(
                "recognizer_loop:utterance",
                {"utterances": [utterance], "lang": LANG},
                {"session": session.serialize()},
            ))
            deadline = time.monotonic() + 15
            while not matched and time.monotonic() < deadline:
                time.sleep(0.2)
        finally:
            self.minicroft.bus.remove(intent_msg_type, handler)
        self.assertTrue(
            matched,
            f"{utterance!r} did not route to {intent_file}",
        )


class TestCurrentWeather(_IntentRoutingMixin, TestCase):
    """current_weather.intent"""

    def test_whats_the_weather(self):
        self._assert_intent("what's the weather", "current_weather.intent")

    def test_how_is_the_weather(self):
        self._assert_intent("how is the weather", "current_weather.intent")


class TestNextRain(_IntentRoutingMixin, TestCase):
    """next_rain.intent"""

    def test_when_will_it_rain_next(self):
        self._assert_intent("when will it rain next", "next_rain.intent")

    def test_when_is_the_next_rain(self):
        self._assert_intent("when is the next rain", "next_rain.intent")


class TestCurrentTemperature(_IntentRoutingMixin, TestCase):
    """current_temperature.intent"""

    def test_temperature_in_madrid(self):
        self._assert_intent("what's the temperature in madrid", "current_temperature.intent")

    def test_current_temperature_update(self):
        self._assert_intent("current temperature update", "current_temperature.intent")


class TestIsRain(_IntentRoutingMixin, TestCase):
    """is_rain.intent"""

    def test_will_it_rain_tomorrow(self):
        self._assert_intent("will it rain tomorrow", "is_rain.intent")


class TestNumberDaysForecast(_IntentRoutingMixin, TestCase):
    """N_days_forecast.intent"""

    def test_three_day_forecast(self):
        self._assert_intent("what's the 3 day forecast", "N_days_forecast.intent")

    def test_seven_day_forecast(self):
        self._assert_intent("what's the 7 day forecast", "N_days_forecast.intent")
