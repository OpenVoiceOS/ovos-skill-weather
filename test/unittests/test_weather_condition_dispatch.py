import unittest
from unittest.mock import patch

from ovos_bus_client.message import Message
from ovos_utils.messagebus import FakeBus
from ovos_skill_weather import WeatherSkill

SKILL_ID = "ovos-skill-weather.openvoiceos"

# Every condition phrase this dispatch table has to route correctly,
# harvested from the six retired ``is_*.intent`` files as they existed
# before #230 collapsed them into the single ``weather_condition.intent``
# slot design, paired with the handler that owns each condition.
#
# #230 merged these into one intent with a free-text ``{condition}`` slot
# resolved at dispatch time. That slot was never filled with real words in
# the m2v training corpus used elsewhere in the ecosystem (only ``{location}``
# style entity placeholders survive into training text), so the model never
# learned to associate the condition text with a response at all: an m2v-8M
# classifier trained on the retired weather_condition training rows routed
# 0/8 held-out, out-of-distribution condition phrasings correctly, while an
# identical model trained on these six specific intents' own phrasings
# routed 8/8 correctly. This file locks in the per-condition handlers that
# replace the slot + ``_resolve_weather_condition`` dispatch.
CONDITION_HANDLERS = [
    ("is it raining today", "handle_is_it_raining", "rain"),
    ("is it snowing today", "handle_is_it_snowing", "snow"),
    ("is it clear today", "handle_is_it_clear", "clear"),
    ("is it cloudy today", "handle_is_it_cloudy", "clouds"),
    ("is it foggy today", "handle_is_it_foggy", "fog"),
    ("is it storming today", "handle_is_it_storming", "thunderstorm"),
]


class TestWeatherConditionDispatch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = WeatherSkill()
        cls.skill._startup(FakeBus(), SKILL_ID)

    def test_each_condition_handler_reports_its_own_condition(self):
        for utterance, handler_name, expected_condition in CONDITION_HANDLERS:
            with self.subTest(utterance=utterance):
                message = Message("intent", {"utterance": utterance})
                with patch.object(self.skill, "_report_weather_condition") as mock_report:
                    getattr(self.skill, handler_name)(message)
                mock_report.assert_called_once()
                args, kwargs = mock_report.call_args
                condition = kwargs.get("condition", args[1] if len(args) > 1 else None)
                self.assertEqual(condition, expected_condition)

    def test_weather_condition_intent_and_resolver_are_retired(self):
        self.assertFalse(hasattr(self.skill, "handle_weather_condition"))
        self.assertFalse(hasattr(self.skill, "_resolve_weather_condition"))
