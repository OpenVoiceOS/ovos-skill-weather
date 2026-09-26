import unittest
from unittest.mock import patch

from ovos_bus_client.message import Message
from ovos_utils.messagebus import FakeBus
from ovos_skill_weather import WeatherSkill

SKILL_ID = "ovos-skill-weather.openvoiceos"

# phrasings lifted verbatim from each locale's retired is_*.intent files,
# paired with the condition key the old per-condition handler used to
# report. These prove weather_condition.intent + _resolve_weather_condition
# reach the same condition per locale that the six retired is_*.intent
# handlers used to, now that the free {condition} slot is gone and
# resolution is a whole-utterance voc_match instead.
LOCALE_PHRASES = {
    "es-ES": [
        ("va a llover", "rain"),
        ("va a nevar hoy en {location}", "snow"),
        ("está nublado", "clouds"),
        ("habrá una tormenta", "thunderstorm"),
        ("hay niebla", "fog"),
        ("está el cielo despejado hoy", "clear"),
    ],
    "de-DE": [
        ("regnet es heute", "rain"),
        ("schneit heute", "snow"),
        ("gibt es Wolken heute", "clouds"),
        ("gibt es ein Gewitter", "thunderstorm"),
        ("gibt es gerade Nebel", "fog"),
        ("ist der Himmel klar", "clear"),
    ],
    "nl-NL": [
        ("regent het vandaag", "rain"),
        ("gaat het vandaag sneeuwen", "snow"),
        ("is het bewolkt vandaag", "clouds"),
        ("is er een storm vandaag", "thunderstorm"),
        ("is er mist buiten", "fog"),
        ("is de lucht helder vandaag", "clear"),
    ],
}

# locales that never got past "cloudy": they only ever shipped
# is_cloudy.intent, with no weather_condition.intent, no is_clear/is_fog/
# is_rain/is_snow/is_stormy to migrate. weather_condition.intent for these
# carries only the cloudy phrasings, and only clouds_report.voc is populated.
# The Swedish locales resolve fog through
# vocabulary/weather_condition_intent/fog_report.voc. They also shipped a
# second file of the same base name, vocabulary/temperature/fog.voc, holding
# two of the same five words; it is deleted, and these phrases -- lifted
# verbatim from each locale's own weather_condition.intent -- are what proves
# the deletion changed no routing.
SWEDISH_FOG_PHRASES = {
    "sv-SE": "är det dimmigt",
    "sv-FI": "är det idag disigt",
}

CLOUDY_ONLY_LOCALE_PHRASES = {
    "cs-CZ": "je zamračeno",
    "hu-HU": "felhős van",
    "it-IT": "è nuvoloso",
    "pl-PL": "jest pochmurno",
    "pt-PT": "está nublado",
    "ru-RU": "облачно",
    "sv-SE": "är det molnigt",
}


class TestWeatherConditionLocaleParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = WeatherSkill()
        cls.skill._startup(FakeBus(), SKILL_ID)

    def test_locale_phrasings_resolve_to_their_historic_condition(self):
        for lang, phrases in LOCALE_PHRASES.items():
            for phrase, expected in phrases:
                with self.subTest(lang=lang, phrase=phrase):
                    message = Message("test", {"utterance": phrase}, {"lang": lang})
                    with patch.object(self.skill, "_report_weather_condition") as report:
                        self.skill.handle_weather_condition(message)
                    report.assert_called_once_with(message, expected)

    def test_cloudy_only_locales_still_route_to_clouds(self):
        """These locales never shipped is_clear/is_fog/is_rain/is_snow/
        is_stormy, only is_cloudy.intent - the migration must not leave
        them without any weather_condition.intent at all, or "is it
        cloudy" stops matching anything.
        """
        for lang, phrase in CLOUDY_ONLY_LOCALE_PHRASES.items():
            with self.subTest(lang=lang, phrase=phrase):
                message = Message("test", {"utterance": phrase}, {"lang": lang})
                with patch.object(self.skill, "_report_weather_condition") as report:
                    self.skill.handle_weather_condition(message)
                report.assert_called_once_with(message, "clouds")


    def test_swedish_fog_still_routes_without_the_duplicate_voc(self):
        """locale/sv-*/vocabulary/temperature/fog.voc is gone.

        condition/fog.voc and weather_condition_intent/fog_report.voc both
        survive with a superset of its words (dimma, dimmigt, plus dimmig, dis
        and disigt), and the dispatcher matches on the fog_report filename, so
        nothing read the deleted file. This is the check that says so.
        """
        for lang, phrase in SWEDISH_FOG_PHRASES.items():
            with self.subTest(lang=lang, phrase=phrase):
                message = Message("test", {"utterance": phrase}, {"lang": lang})
                with patch.object(self.skill, "_report_weather_condition") as report:
                    self.skill.handle_weather_condition(message)
                report.assert_called_once_with(message, "fog")


if __name__ == "__main__":
    unittest.main()
