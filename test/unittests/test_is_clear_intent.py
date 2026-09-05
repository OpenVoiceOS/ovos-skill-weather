import unittest
from os.path import dirname, join

from padacioso import IntentContainer


class TestIsClearVsIsCloudyIntent(unittest.TestCase):
    """``is_clear.intent`` and ``is_cloudy.intent`` (en-US) are separate,
    fixed-vocabulary intents rather than a shared ``{condition}`` slot, so
    the parser -- not a dispatch-time resolver -- is responsible for telling
    "cloudy" and "clear" apart.
    """

    @classmethod
    def setUpClass(cls):
        root = dirname(dirname(dirname(__file__)))
        cls.container = IntentContainer()
        for name in ("is_clear", "is_cloudy"):
            intent_file = join(root, "locale", "en-US", "intents", f"{name}.intent")
            with open(intent_file, encoding="utf-8") as f:
                samples = [line.strip() for line in f if line.strip()]
            cls.container.add_intent(name, samples)

    def test_cloudy_matches_is_cloudy(self):
        match = self.container.calc_intent("is it cloudy")
        self.assertEqual(match.get("name"), "is_cloudy")

    def test_how_cloudy_matches_is_cloudy(self):
        match = self.container.calc_intent("how cloudy is it today")
        self.assertEqual(match.get("name"), "is_cloudy")

    def test_clear_matches_is_clear(self):
        match = self.container.calc_intent("is it clear")
        self.assertEqual(match.get("name"), "is_clear")

    def test_sunny_matches_is_clear(self):
        match = self.container.calc_intent("is it sunny")
        self.assertEqual(match.get("name"), "is_clear")


if __name__ == "__main__":
    unittest.main()
