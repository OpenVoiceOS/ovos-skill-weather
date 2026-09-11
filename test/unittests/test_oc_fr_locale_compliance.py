import glob
import os
import re
import unittest
from unittest.mock import patch

from ovos_bus_client.message import Message
from ovos_utils.messagebus import FakeBus
from ovos_skill_weather import WeatherSkill

SKILL_ID = "ovos-skill-weather.openvoiceos"
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OC_FR_DIR = os.path.join(ROOT, "locale", "oc-FR")
EN_US_DIR = os.path.join(ROOT, "locale", "en-US")

BASE_NAME_RE = re.compile(r"^[a-z0-9_]+$")

# phrasings lifted verbatim from the retired oc-FR
# vocabulary/condition/do-i-need-an-umbrella.intent, now folded into
# weather_condition.intent (OVOS-INTENT-2 SS2: umbrella phrasings are not a
# separate registered intent in en-US either, they live inline in
# weather_condition.intent and resolve through rain_report.voc).
UMBRELLA_PHRASES = [
    "aurai de besonh deman un parapluèja",
    "licaldriá portar un parapluèja",
    "ai de besonh un parapluèja pel viatge",
    "ai de besonh prene un impermeable",
    "plourà deman",
]


def _en_us_filenames():
    names = set()
    for path in glob.glob(os.path.join(EN_US_DIR, "**", "*"), recursive=True):
        if os.path.isfile(path):
            names.add(os.path.basename(path))
    return names


class TestOcFrResourceBaseNames(unittest.TestCase):
    """OVOS-INTENT-2 SS2: 'A resource base name MUST consist only of
    lowercase ASCII letters, digits, and underscores, and MUST NOT contain
    whitespace; file extensions are likewise lowercase.'

    en-US already ships some non-compliant names of its own (e.g.
    number-days.voc); a locale is obliged to mirror those exactly for
    resource lookup to resolve, so a mismatch there is en-US's own defect,
    not this locale's to carry. This test only holds oc-FR to names that
    have no en-US file to mirror in the first place - the avoidable case.
    """

    def test_every_avoidable_oc_fr_base_name_is_compliant(self):
        en_us_names = _en_us_filenames()
        offenders = []
        for path in glob.glob(os.path.join(OC_FR_DIR, "**", "*"), recursive=True):
            if not os.path.isfile(path):
                continue
            filename = os.path.basename(path)
            if filename in en_us_names:
                continue  # forced: mirrors an en-US name, not oc-FR's bug
            base, ext = os.path.splitext(filename)
            if ext != ext.lower() or not BASE_NAME_RE.match(base):
                offenders.append(os.path.relpath(path, ROOT))
        self.assertEqual(
            [], offenders,
            f"non-compliant oc-FR resource base names with no en-US name "
            f"to mirror: {offenders}",
        )


class TestOcFrUmbrellaReachable(unittest.TestCase):
    """The umbrella phrasings folded into weather_condition.intent must
    still resolve through the skill's real dispatch (voc_match against
    rain_report.voc), the way en-US's inline umbrella phrasings do -
    not sit in an orphan, unregistered do-i-need-an-umbrella.intent.
    """

    @classmethod
    def setUpClass(cls):
        cls.skill = WeatherSkill()
        cls.skill._startup(FakeBus(), SKILL_ID)

    def test_umbrella_phrasings_resolve_to_rain(self):
        for phrase in UMBRELLA_PHRASES:
            with self.subTest(phrase=phrase):
                message = Message("test", {"utterance": phrase}, {"lang": "oc-FR"})
                with patch.object(self.skill, "_report_weather_condition") as report:
                    self.skill.handle_weather_condition(message)
                report.assert_called_once_with(message, "rain")

    def test_umbrella_phrasings_are_lines_in_weather_condition_intent(self):
        """Resolving to the right condition is necessary but not
        sufficient: the phrase must actually be a line of
        weather_condition.intent (the file @intent_handler registers),
        or nothing the padatious/padacioso parser trains on ever contains
        it and it can never be reached from real speech.
        """
        with open(os.path.join(OC_FR_DIR, "intents", "weather_condition.intent"),
                   encoding="utf-8") as f:
            lines = {line.strip() for line in f}
        for phrase in UMBRELLA_PHRASES:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, lines)

    def test_orphan_umbrella_intent_file_is_gone(self):
        self.assertFalse(
            os.path.exists(os.path.join(
                OC_FR_DIR, "vocabulary", "condition", "do-i-need-an-umbrella.intent")),
            "orphan do-i-need-an-umbrella.intent must be folded into "
            "weather_condition.intent and removed, mirroring PR #258",
        )


if __name__ == "__main__":
    unittest.main()
