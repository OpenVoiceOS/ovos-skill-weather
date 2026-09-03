import unittest
from os.path import dirname, join

from padacioso import IntentContainer


class TestWeatherConditionIntent(unittest.TestCase):
    """``weather_condition.intent`` (en-US) must capture the "cloudy" vs
    "clear" distinction in its ``{condition}`` slot rather than routing
    them to different intents, so the dispatch layer -- not the parser --
    is responsible for telling the two apart.
    """

    @classmethod
    def setUpClass(cls):
        root = dirname(dirname(dirname(__file__)))
        intent_file = join(root, "locale", "en-US", "intents", "weather_condition.intent")
        with open(intent_file, encoding="utf-8") as f:
            samples = [line.strip() for line in f if line.strip()]
        cls.container = IntentContainer()
        cls.container.add_intent("weather_condition", samples)

    def test_cloudy_matches_with_cloudy_condition(self):
        match = self.container.calc_intent("is it cloudy")
        self.assertEqual(match.get("name"), "weather_condition")
        self.assertEqual(match.get("entities", {}).get("condition"), "cloudy")

    def test_how_cloudy_matches_with_cloudy_condition(self):
        match = self.container.calc_intent("how cloudy is it today")
        self.assertEqual(match.get("name"), "weather_condition")
        self.assertEqual(match.get("entities", {}).get("condition"), "cloudy")

    def test_clear_matches_with_clear_condition(self):
        match = self.container.calc_intent("is it clear")
        self.assertEqual(match.get("name"), "weather_condition")
        self.assertEqual(match.get("entities", {}).get("condition"), "clear")

    def test_sunny_matches_with_sunny_condition(self):
        match = self.container.calc_intent("is it sunny")
        self.assertEqual(match.get("name"), "weather_condition")
        self.assertEqual(match.get("entities", {}).get("condition"), "sunny")


if __name__ == "__main__":
    unittest.main()
