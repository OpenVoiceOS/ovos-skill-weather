"""The regex resources stay gone, and the slot carries the place instead.

ovos-workshop deprecates regex intents: `register_adapt_regex` warns that they
are adapt-engine only and go away in 10.0.0. This skill shipped a
`locale/<lang>/regex/location.rx` in all 22 locales, and nothing consumed them:
every intent is a file intent registered with `@intent_handler("<name>.intent")`,
and an adapt regex entity only reaches an adapt intent.

The third case is the one that carries weight. The first two only say the files
and the packaging glob are absent, which a tree that never had them would satisfy;
the third says the path that has to serve the place is really there, in every
locale and every intent.
"""
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LOCALE = REPO / "locale"


class TestNoRegexResources(unittest.TestCase):
    def test_no_regex_resource_files(self):
        found = sorted(str(p.relative_to(REPO)) for p in REPO.rglob("*.rx")
                       if ".venv" not in p.parts and "build" not in p.parts)
        self.assertEqual([], found, f"regex resources are deprecated, found: {found}")

    def test_no_regex_directory_and_no_packaging_glob(self):
        dirs = sorted(str(p.relative_to(REPO)) for p in REPO.rglob("regex")
                      if p.is_dir() and ".venv" not in p.parts)
        self.assertEqual([], dirs, f"regex resource directories remain: {dirs}")
        self.assertNotIn('"regex/**/*"', (REPO / "pyproject.toml").read_text(encoding="utf-8"),
                         "the package-data glob still ships a regex directory")

    def test_every_locale_intent_carries_the_location_slot(self):
        locales = sorted(p.name for p in LOCALE.iterdir() if p.is_dir())
        self.assertTrue(locales, "no locales found")
        missing = []
        for lang in locales:
            intents = sorted((LOCALE / lang / "intents").glob("*.intent"))
            if not intents:
                missing.append(f"{lang} ships no intents")
                continue
            for path in intents:
                if "{location}" not in path.read_text(encoding="utf-8"):
                    missing.append(f"{lang}/{path.name} carries no {{location}}")
        self.assertEqual([], missing,
                         "the slot is the only place path now: " + "; ".join(missing))


if __name__ == "__main__":
    unittest.main()
