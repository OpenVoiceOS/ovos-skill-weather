"""The umbrella and raincoat phrasings belong to ``weather_condition.intent``.

en-US carries them inside that intent; every other locale kept them in a
``do-i-need-an-umbrella.intent`` file under ``vocabulary/condition/`` that no
handler ever registered, so the phrasings matched nothing at all. They live in
the locale's ``weather_condition.intent`` now, and each row below is a line
lifted verbatim from the file that carried it.
"""
import glob
import os
import unittest

from padacioso import IntentContainer

LOCALE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "locale")

UMBRELLA_PHRASES = {
    "ca-ES": "demà necessitaré un paraigua",
    "cs-CZ": "Potřebuji deštník na dojíždění do práce",
    "da-DK": "skulle jeg medbringe en paraply",
    "de-DE": "Ist es wahrscheinlich, dass es heute regnet",
    "en-US": "do I need an umbrella",
    "es-ES": "¿debo llevar un chubasquero",
    "eu-ES": "arratsalderako euria espero da",
    "fr-FR": "Ai-je besoin d'un parapluie demain",
    "gl-ES": "dan chuvia na previsión do tempo",
    "hu-HU": "esős lesz az idő",
    "it-IT": "devo mettere un ombrello in borsa",
    "nl-NL": "Moet ik een paraplu meenemen naar het evenement",
    "pl-PL": "Czy będą dzisiaj opady deszczu",
    "pt-BR": "devo levar um casaco de chuva",
    "pt-PT": "a previsão do tempo é de chuva",
    "ru-RU": "будет ли дождь",
    "sv-FI": "Pitäisikö minun ottaa sateenvarjo mukaan puistoon",
    "sv-SE": "Behöver jag en regnjacka i morgon",
    "tr-TR": "Bugün yağmur ihtimali var mı",
}


def container_for(lang: str) -> IntentContainer:
    container = IntentContainer()
    pattern = os.path.join(LOCALE_DIR, lang, "intents", "*.intent")
    for path in sorted(glob.glob(pattern)):
        with open(path, encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        container.add_intent(os.path.basename(path), lines)
    return container


class TestUmbrellaPhrasingsRoute(unittest.TestCase):
    def test_umbrella_phrasings_match_weather_condition(self):
        for lang, phrase in UMBRELLA_PHRASES.items():
            with self.subTest(lang=lang, phrase=phrase):
                result = container_for(lang).calc_intent(phrase)
                self.assertEqual(
                    result.get("name"),
                    "weather_condition.intent",
                    f"{lang} {phrase!r} routed to {result.get('name')!r}",
                )

    def test_no_locale_keeps_an_unregistered_umbrella_intent_file(self):
        stray = sorted(
            p for p in glob.glob(os.path.join(LOCALE_DIR, "**", "*"), recursive=True)
            if "umbrella" in os.path.basename(p).lower()
        )
        self.assertEqual(stray, [], "no handler registers these files")


if __name__ == "__main__":
    unittest.main()
