import glob
import os
import unittest
from unittest.mock import patch

from ovos_bus_client.message import Message
from ovos_spec_tools.expansion import expand
from ovos_utils.messagebus import FakeBus
from ovos_skill_weather import WeatherSkill

SKILL_ID = "ovos-skill-weather.openvoiceos"
LOCALE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "locale")

# one "do I need an umbrella" phrasing per locale, written by that locale's
# translator. Each has to be produced by weather_condition.intent and
# dispatch to the rain report, the same route en-US takes for
# "do I need an umbrella tomorrow".
UMBRELLA_PHRASES = {
    "ca-ES": "necessito un paraigua pel viatge",
    "cs-CZ": "potřebuji zítra deštník",
    "da-DK": "har jeg brug for en paraply",
    "de-DE": "soll ich heute meinen Regenschirm mitnehmen",
    "es-ES": "necesito un paraguas",
    "eu-ES": "aterki bat behar al dut bihar",
    "fr-FR": "dois-je emporter un parapluie",
    "gl-ES": "preciso dun paraugas",
    "hu-HU": "vigyek ma esernyőt",
    "it-IT": "devo prendere l'ombrello",
    "nl-NL": "moet ik vandaag mijn paraplu meenemen",
    "pl-PL": "Czy potrzebuję jutro parasola",
    "pt-BR": "preciso de um guarda-chuva",
    "pt-PT": "preciso de um guarda-chuva amanhã",
    "ru-RU": "нужен ли мне завтра зонтик",
    "sv-FI": "Tarvitsenko huomenna sateenvarjon",
    "sv-SE": "behöver jag ett paraply",
    "tr-TR": "Yarın şemsiyeye ihtiyacım var mı",
}


def produced_by(lang, intent_name):
    path = os.path.join(LOCALE_DIR, lang, "intents", intent_name)
    with open(path, encoding="utf-8") as f:
        templates = [line.strip() for line in f if line.strip()]
    return {phrase.lower() for t in templates for phrase in expand(t)}


class TestUmbrellaPhrasings(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = WeatherSkill()
        cls.skill._startup(FakeBus(), SKILL_ID)

    def test_umbrella_phrasings_belong_to_weather_condition_intent(self):
        for lang, phrase in UMBRELLA_PHRASES.items():
            with self.subTest(lang=lang, phrase=phrase):
                self.assertIn(phrase.lower(), produced_by(lang, "weather_condition.intent"))

    def test_umbrella_phrasings_dispatch_to_rain(self):
        for lang, phrase in UMBRELLA_PHRASES.items():
            with self.subTest(lang=lang, phrase=phrase):
                message = Message("test", {"utterance": phrase}, {"lang": lang})
                with patch.object(self.skill, "_report_weather_condition") as report, \
                        patch.object(self.skill, "handle_weather") as fallback:
                    self.skill.handle_weather_condition(message)
                fallback.assert_not_called()
                report.assert_called_once_with(message, "rain")

    def test_no_orphan_umbrella_intent_files(self):
        """A ``do-i-need-an-umbrella`` file under vocabulary/ is registered by
        no handler; its phrasings only reach a user once folded into
        weather_condition.intent.
        """
        orphans = glob.glob(os.path.join(LOCALE_DIR, "*", "vocabulary", "**", "*umbrella*"), recursive=True)
        self.assertEqual(orphans, [])


if __name__ == "__main__":
    unittest.main()
