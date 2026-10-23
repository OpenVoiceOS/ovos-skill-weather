import unittest
from os.path import dirname, join

from padacioso import IntentContainer

from ovos_utils.messagebus import FakeBus
from ovos_skill_weather import WeatherSkill

SKILL_ID = "ovos-skill-weather.openvoiceos"


class TestWeatherConditionIntent(unittest.TestCase):
    """``weather_condition.intent`` (en-US) matches the "cloudy" vs "clear"
    phrasings directly (no free ``{condition}`` slot, which used to
    over-match and required a ``voc_blacklist`` crutch to stay out of
    "is it hot/cold" territory). Condition resolution now happens by
    ``voc_match``-ing the whole utterance against each condition's own
    vocabulary group, not by parsing a captured slot.
    """

    @classmethod
    def setUpClass(cls):
        root = dirname(dirname(dirname(__file__)))
        intent_file = join(root, "locale", "en-US", "intents", "weather_condition.intent")
        with open(intent_file, encoding="utf-8") as f:
            samples = [line.strip() for line in f if line.strip()]
        cls.container = IntentContainer()
        cls.container.add_intent("weather_condition", samples)

        cls.skill = WeatherSkill()
        cls.skill._startup(FakeBus(), SKILL_ID)

    def test_cloudy_matches_and_resolves_to_clouds(self):
        match = self.container.calc_intent("is it cloudy")
        self.assertEqual(match.get("name"), "weather_condition")
        self.assertEqual(self.skill._resolve_weather_condition("is it cloudy"), "clouds")

    def test_how_cloudy_matches_and_resolves_to_clouds(self):
        match = self.container.calc_intent("how cloudy is it today")
        self.assertEqual(match.get("name"), "weather_condition")
        self.assertEqual(
            self.skill._resolve_weather_condition("how cloudy is it today"), "clouds"
        )

    def test_clear_matches_and_resolves_to_clear(self):
        match = self.container.calc_intent("is it clear")
        self.assertEqual(match.get("name"), "weather_condition")
        self.assertEqual(self.skill._resolve_weather_condition("is it clear"), "clear")

    def test_sunny_matches_and_resolves_to_clear(self):
        match = self.container.calc_intent("will it be sunny today")
        self.assertEqual(match.get("name"), "weather_condition")
        self.assertEqual(
            self.skill._resolve_weather_condition("will it be sunny today"), "clear"
        )

    def test_hot_and_cold_do_not_match_weather_condition(self):
        """With the free slot gone, "is it hot or cold today" simply doesn't
        match ``weather_condition.intent`` at all -- there's no shared
        vocabulary word between it and any condition phrasing above, so the
        ``voc_blacklist`` crutch the slot-based version needed is no longer
        necessary.
        """
        match = self.container.calc_intent("is it hot or cold today")
        self.assertNotEqual(match.get("name"), "weather_condition")


if __name__ == "__main__":
    unittest.main()
