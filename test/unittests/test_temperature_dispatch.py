"""``handle_temperature`` answers every temperature question, including
"is it hot" and "is it cold", and picks which temperature from the words
of the utterance."""
import unittest
from unittest.mock import patch

from ovos_bus_client.message import Message
from ovos_utils.fakebus import FakeBus
from ovos_skill_weather import WeatherSkill

SKILL_ID = "ovos-skill-weather.openvoiceos"

UTTERANCE_TO_TYPE = [
    ("what is the temperature", "current"),
    ("what is the temperature at 3 pm", "current"),
    ("what is the high temperature tomorrow", "high"),
    ("what's the maximum temp in paris", "high"),
    ("what is the low temperature tonight", "low"),
    ("what's the minimum temperature on monday", "low"),
    ("is it hot", "high"),
    ("will it be warm tomorrow", "high"),
    ("is it cold", "low"),
    ("will it be chilly tonight in paris", "low"),
    ("is it freezing outside", "low"),
    # a high or low word decides before a hot or cold word
    ("how cold will the high be tomorrow", "high"),
    ("how warm is the low tonight", "low"),
    # both feelings, or neither, ask for the temperature as it is
    ("how hot or cold is it right now", "current"),
    ("do i need a coat", "current"),
]


class TestTemperatureDispatch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = WeatherSkill()
        cls.skill._startup(FakeBus(), SKILL_ID)

    def test_every_phrasing_reports_the_temperature_it_asks_for(self):
        for utterance, expected in UTTERANCE_TO_TYPE:
            with self.subTest(utterance=utterance):
                message = Message("test", {"utterance": utterance})
                with patch.object(self.skill, "_report_temperature") as report:
                    self.skill.handle_temperature(message)
                report.assert_called_once_with(message, temperature_type=expected)


if __name__ == "__main__":
    unittest.main()
