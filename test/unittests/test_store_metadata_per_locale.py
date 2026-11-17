import json
import unittest
from pathlib import Path

LOCALE_DIR = Path(__file__).resolve().parents[2] / "locale"
SKILL_ID = "ovos-skill-weather.openvoiceos"

# T-5857: locale/it-IT/skill.json shipped its six tags as JSON nulls and a
# skill_id beginning with a tab, and the whole suite stayed green. Nothing read
# these files, so the store indexed one locale by nothing at all. These checks
# run over every locale so the next one cannot slip through the same gap.
TAG_SLOTS = 6


def locale_files():
    return sorted(LOCALE_DIR.glob("*/skill.json"))


class TestStoreMetadataPerLocale(unittest.TestCase):
    def test_there_are_locale_files_to_check(self):
        # A glob that silently matches nothing would make every test below pass.
        self.assertTrue(locale_files(), f"no skill.json under {LOCALE_DIR}")

    def test_skill_id_carries_no_surrounding_whitespace(self):
        for path in locale_files():
            with self.subTest(locale=path.parent.name):
                skill_id = json.loads(path.read_text(encoding="utf-8"))["skill_id"]
                self.assertEqual(
                    skill_id, skill_id.strip(),
                    f"{path.parent.name}: skill_id is padded with whitespace: {skill_id!r}")
                self.assertEqual(
                    skill_id, SKILL_ID,
                    f"{path.parent.name}: skill_id is {skill_id!r}, not {SKILL_ID!r}")

    def test_every_locale_ships_real_tag_text(self):
        for path in locale_files():
            with self.subTest(locale=path.parent.name):
                tags = json.loads(path.read_text(encoding="utf-8"))["tags"]
                self.assertIsInstance(tags, list, f"{path.parent.name}: tags is not a list")
                self.assertEqual(
                    len(tags), TAG_SLOTS,
                    f"{path.parent.name}: {len(tags)} tags, expected {TAG_SLOTS}")
                for i, tag in enumerate(tags):
                    self.assertIsInstance(
                        tag, str, f"{path.parent.name}: tag {i} is {tag!r}, not text")
                    self.assertTrue(
                        tag.strip(), f"{path.parent.name}: tag {i} is blank")

    def test_examples_are_non_empty_text(self):
        for path in locale_files():
            with self.subTest(locale=path.parent.name):
                examples = json.loads(path.read_text(encoding="utf-8"))["examples"]
                self.assertTrue(examples, f"{path.parent.name}: no examples")
                for i, ex in enumerate(examples):
                    self.assertIsInstance(
                        ex, str, f"{path.parent.name}: example {i} is {ex!r}, not text")
                    self.assertTrue(
                        ex.strip(), f"{path.parent.name}: example {i} is blank")


if __name__ == "__main__":
    unittest.main()
