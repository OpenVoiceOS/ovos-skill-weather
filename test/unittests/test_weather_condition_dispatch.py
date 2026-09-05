import unittest
from unittest.mock import patch

from ovos_bus_client.message import Message
from ovos_utils.messagebus import FakeBus
from ovos_skill_weather import WeatherSkill

SKILL_ID = "ovos-skill-weather.openvoiceos"

# every condition phrase harvested from the six retired ``is_*.intent``
# files (including the pre-existing is_clear.intent quirks that are
# reclassified to their true semantic group as part of the merge), paired
# with the condition key ``handle_weather_condition`` must dispatch to.
CONDITION_PHRASES = [
    ("raining", "rain"),
    ("rainy", "rain"),
    ("rain", "rain"),
    ("drizzle", "rain"),
    ("drizzling", "rain"),
    ("shower", "rain"),
    ("showers", "rain"),
    ("precipitation", "rain"),
    ("umbrella", "rain"),
    ("raincoat", "rain"),
    ("rain jacket", "rain"),
    ("snowing", "snow"),
    ("snowy", "snow"),
    ("snow", "snow"),
    ("sleet", "snow"),
    ("sleeting", "snow"),
    ("flurries", "snow"),
    ("snowfall", "snow"),
    ("icy", "snow"),
    ("clear", "clear"),
    ("sunny", "clear"),
    ("sunshine", "clear"),
    ("clear skies", "clear"),
    ("blue skies", "clear"),
    ("cloudy", "clouds"),
    ("clouds", "clouds"),
    ("cloud", "clouds"),
    ("cloudier", "clouds"),
    ("the sky overcast", "clouds"),
    ("the sky gloomy", "clouds"),
    ("the sky gray", "clouds"),
    ("any cloud cover", "clouds"),
    ("fog", "fog"),
    ("foggy", "fog"),
    ("mist", "fog"),
    ("misty", "fog"),
    ("hazy", "fog"),
    ("haze", "fog"),
    ("storming", "thunderstorm"),
    ("stormy", "thunderstorm"),
    ("storm", "thunderstorm"),
    ("storms", "thunderstorm"),
    ("thunderstorm", "thunderstorm"),
    ("thunder", "thunderstorm"),
    ("thundering", "thunderstorm"),
    ("severe weather event", "thunderstorm"),
    ("storm alerts", "thunderstorm"),
    ("severe weather warnings", "thunderstorm"),
    ("bad weather", "thunderstorm"),
]


class TestWeatherConditionDispatch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = WeatherSkill()
        cls.skill._startup(FakeBus(), SKILL_ID)

    def test_dispatch_table_covers_every_harvested_condition(self):
        for phrase, expected in CONDITION_PHRASES:
            with self.subTest(phrase=phrase):
                self.assertEqual(self.skill._resolve_weather_condition(phrase), expected)

    def test_unrecognized_condition_falls_back_to_current_weather(self):
        self.assertIsNone(self.skill._resolve_weather_condition("banana"))

    def test_handler_reports_the_resolved_condition(self):
        message = Message(
            "test", {"condition": "raining", "utterance": "is it raining"}
        )
        with patch.object(self.skill, "_report_weather_condition") as report:
            self.skill.handle_weather_condition(message)
        report.assert_called_once_with(message, "rain")

    def test_handler_falls_back_when_condition_unrecognized(self):
        message = Message(
            "test", {"condition": "banana", "utterance": "is it banana"}
        )
        with patch.object(self.skill, "_report_weather_condition") as report, \
                patch.object(self.skill, "handle_current_weather") as fallback:
            self.skill.handle_weather_condition(message)
        report.assert_not_called()
        fallback.assert_called_once_with(message)

    def test_hot_and_cold_stay_out_of_the_condition_vocab_groups(self):
        """"hot"/"cold" are ``handle_is_it_hot_or_cold``'s own turf; the
        condition groups here must never claim them, or a bare "hot"/"cold"
        utterance could get misclassified as a weather condition.
        """
        self.assertIsNone(self.skill._resolve_weather_condition("hot"))
        self.assertIsNone(self.skill._resolve_weather_condition("cold"))
        self.assertIsNone(self.skill._resolve_weather_condition("hot or cold"))


if __name__ == "__main__":
    unittest.main()
