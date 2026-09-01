import unittest
from os.path import dirname, join

from padacioso import IntentContainer


class TestIsClearIntent(unittest.TestCase):
    """``is_clear.intent`` (en-US) must not claim cloudiness questions.

    "is it cloudy" is a question about the clouds condition, not about a
    clear sky, and must not tie with (or steal) the ``is_cloudy`` intent.
    """

    @classmethod
    def setUpClass(cls):
        root = dirname(dirname(dirname(__file__)))
        intent_file = join(root, "locale", "en-US", "intents", "is_clear.intent")
        with open(intent_file, encoding="utf-8") as f:
            samples = [line.strip() for line in f if line.strip()]
        cls.container = IntentContainer()
        cls.container.add_intent("is_clear", samples)

    def test_cloudy_does_not_match_is_clear(self):
        match = self.container.calc_intent("is it cloudy")
        self.assertNotEqual(match.get("name"), "is_clear")

    def test_how_cloudy_does_not_match_is_clear(self):
        match = self.container.calc_intent("how cloudy is it today")
        self.assertNotEqual(match.get("name"), "is_clear")

    def test_clear_still_matches_is_clear(self):
        match = self.container.calc_intent("is it clear")
        self.assertEqual(match.get("name"), "is_clear")

    def test_sunny_still_matches_is_clear(self):
        match = self.container.calc_intent("is it sunny")
        self.assertEqual(match.get("name"), "is_clear")


if __name__ == "__main__":
    unittest.main()
