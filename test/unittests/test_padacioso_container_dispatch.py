import glob
import os
import unittest

from padacioso import IntentContainer

INTENTS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "locale", "en-US", "intents"
)

# "is it hot", "will it be cold", "what's the weather forecast" and friends
# each have to win their own phrasings outright inside the SAME padacioso
# container the rest of the skill's intents share -- no ties, and no more
# overlap than what the pre-existing intents already claimed. Every row
# below is a literal, first-alternative expansion sampled directly from
# is_hot_or_cold.intent and weather.intent's own templates, so it is
# guaranteed to be a phrase each file actually claims to match.
EXPECTED_ROUTING = [
    ("do i need a coat today in paris", "is_hot_or_cold.intent"),
    ("is it cold", "is_hot_or_cold.intent"),
    ("is it cold enough today in paris", "is_hot_or_cold.intent"),
    ("is it cold in paris today", "is_hot_or_cold.intent"),
    ("is it cold on monday in paris", "is_hot_or_cold.intent"),
    ("is it cold outside", "is_hot_or_cold.intent"),
    ("is it cold today in paris", "is_hot_or_cold.intent"),
    ("is it going to be cold", "is_hot_or_cold.intent"),
    ("is it going to be cold today", "is_hot_or_cold.intent"),
    ("is there be a cold snap today in paris", "is_hot_or_cold.intent"),
    ("will it be cold", "is_hot_or_cold.intent"),
    ("will we have cold weather today in paris", "is_hot_or_cold.intent"),
    ("do i need shorts today in paris", "is_hot_or_cold.intent"),
    ("is it going to be hot", "is_hot_or_cold.intent"),
    ("is it going to be hot today", "is_hot_or_cold.intent"),
    ("is it hot", "is_hot_or_cold.intent"),
    ("is it hot enough today in paris", "is_hot_or_cold.intent"),
    ("is it hot in paris today", "is_hot_or_cold.intent"),
    ("is it hot on monday in paris", "is_hot_or_cold.intent"),
    ("is it hot outside", "is_hot_or_cold.intent"),
    ("is it hot today in paris", "is_hot_or_cold.intent"),
    ("is there be a heat wave today in paris", "is_hot_or_cold.intent"),
    ("will it be hot", "is_hot_or_cold.intent"),
    ("will we have hot weather today in paris", "is_hot_or_cold.intent"),
    ("give me the forecast in paris", "weather.intent"),
    ("weather in paris", "weather.intent"),
    ("what is the weather forecast for today in celsius", "weather.intent"),
    ("what is tomorrow's forecast in paris", "weather.intent"),
]

EXPECTED_FILES = {"is_hot_or_cold.intent", "weather.intent"}


class TestPadaciosoContainerDispatch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.container = IntentContainer()
        for path in sorted(glob.glob(os.path.join(INTENTS_DIR, "*.intent"))):
            name = os.path.basename(path)
            with open(path, encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
            cls.container.add_intent(name, lines)

    def test_expected_intent_files_exist(self):
        found = {os.path.basename(p) for p in glob.glob(os.path.join(INTENTS_DIR, "*.intent"))}
        self.assertTrue(EXPECTED_FILES.issubset(found), found)
        self.assertNotIn("is_hot_cold.intent", found)

    def test_phrases_route_without_ties(self):
        for phrase, expected in EXPECTED_ROUTING:
            with self.subTest(phrase=phrase):
                result = self.container.calc_intent(phrase)
                self.assertEqual(
                    result.get("name"),
                    expected,
                    f"{phrase!r} routed to {result.get('name')!r} instead",
                )


if __name__ == "__main__":
    unittest.main()
