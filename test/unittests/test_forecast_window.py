"""The day or hour a question asks about, and the number of days a
multi-day forecast covers, read in the utterance's own language."""
import datetime
from unittest.mock import PropertyMock, patch
from zoneinfo import ZoneInfo

import pytest
from ovos_bus_client.message import Message
from ovos_utils.fakebus import FakeBus

from ovos_skill_weather import WeatherSkill
from ovos_skill_weather.weather_helpers import intent, util
from ovos_skill_weather.weather_helpers.weather import CURRENT

LISBON = ZoneInfo("Europe/Lisbon")
#: a Tuesday afternoon
NOW = datetime.datetime(2017, 6, 27, 13, 4, tzinfo=LISBON)


@pytest.fixture
def frozen_now(monkeypatch):
    class Frozen(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW.astimezone(tz)

    monkeypatch.setattr(util, "datetime", Frozen)
    # a question that names no place reads the time in the device's zone
    monkeypatch.setattr(util, "now_local", lambda tz=None: NOW)


@pytest.mark.parametrize("lang, utterance, expected", [
    # a weekend is a forecast from its Saturday
    ("en-US", "what's the weather this weekend", datetime.datetime(2017, 7, 1)),
    # two days named together start on the first of them
    ("en-US", "what's the weather on Saturday and Sunday", datetime.datetime(2017, 7, 1)),
    # a part of the day is the middle of its band, and a night is cut at
    # midnight before its middle is taken
    ("en-US", "will it be cold tonight", datetime.datetime(2017, 6, 27, 22, 30)),
    ("en-US", "what is the temperature friday morning", datetime.datetime(2017, 6, 30, 9)),
    # a counted number of days keeps no clock, so it is a daily forecast
    ("en-US", "what will the weather be in 3 days", datetime.datetime(2017, 6, 30)),
])
def test_the_time_asked_about(frozen_now, lang, utterance, expected):
    when = util.get_utterance_datetime(utterance, "Europe/Lisbon", lang)
    assert when == expected.replace(tzinfo=LISBON)


@pytest.mark.parametrize("lang, utterance", [
    ("eu-ES", "dago eguzkitsu gaur"),
    ("tr-TR", "bugün hava nasıl"),
    ("kab", "tella lḥala ifaz ass-a"),
])
def test_a_question_with_no_place_is_read_in_the_device_zone(frozen_now, lang, utterance):
    # with no place named there is no zone to pass; the skill subtracts the
    # answer from an aware time, so an answer with no zone crashed the handler
    when = util.get_utterance_datetime(utterance, None, lang)
    assert when == NOW.replace(hour=0, minute=0)
    assert when.tzinfo is not None


@pytest.mark.parametrize("utterance", [
    "can you tell me the weather right now",
    "around here at what hour should the rain start",
])
def test_now_is_the_current_weather(frozen_now, utterance):
    # no time to look ahead to: the skill reports the weather as it is
    assert util.get_utterance_datetime(utterance, "Europe/Lisbon", "en-US") is None


@pytest.fixture(scope="module")
def skill():
    skill = WeatherSkill()
    skill._startup(FakeBus(), "ovos-skill-weather.openvoiceos")
    return skill


def days_asked(skill, lang, utterance):
    reported = []
    with patch.object(WeatherSkill, "lang", new_callable=PropertyMock, return_value=lang), \
            patch.object(skill, "_report_multi_day_forecast", lambda m, days: reported.append(days)), \
            patch.object(skill, "_report_week_summary", lambda m: reported.append("week")):
        multi_day = skill._is_multi_day_forecast_request(utterance)
        skill._dispatch_multi_day_forecast(Message("test", {"utterance": utterance}))
    return multi_day, reported


@pytest.mark.parametrize("lang, utterance, days", [
    ("en-US", "give me a 3 day forecast", 3),
    ("en-US", "what will a five day forecast say", 5),
    ("pt-PT", "qual é a previsão para os próximos cinco dias", 5),
    # the old check matched only the English word "day"
    ("cs-CZ", "Jaká je předpověď počasí na dva dní", 2),
])
def test_a_counted_number_of_days_is_a_multi_day_forecast(skill, lang, utterance, days):
    assert days_asked(skill, lang, utterance) == (True, [days])


@pytest.mark.parametrize("lang, utterance", [
    # "day" with no count, or with only an article, names no number of days
    ("en-US", "a day by the sea, what is the forecast"),
    ("pt-BR", "Hoje vai fazer um dia de sol?"),
    ("en-US", "what about the day after tomorrow"),
])
def test_a_day_word_without_a_count_is_the_week(skill, lang, utterance):
    assert days_asked(skill, lang, utterance) == (False, ["week"])


@pytest.mark.parametrize("zone, wall_clock, utterance", [
    ("Europe/Lisbon", (20, 35), "what's the weather this evening"),
    ("America/New_York", (15, 35), "what's the weather this afternoon"),
])
def test_a_part_of_the_day_that_holds_now_is_the_current_weather(
        skill, monkeypatch, zone, wall_clock, utterance):
    # the skill reads the clock more than once while it handles one question,
    # and every read is a little later than the one before
    reads = iter(range(1000))
    start = datetime.datetime(2017, 6, 27, *wall_clock, tzinfo=ZoneInfo(zone))

    def ticking_clock(tz=None):
        return start + datetime.timedelta(milliseconds=250 * next(reads))

    monkeypatch.setattr(util, "now_local", ticking_clock)
    monkeypatch.setattr(intent, "now_local", ticking_clock)
    intent_data = skill._get_intent_data(Message("test", {"utterance": utterance}))
    assert intent_data.timeframe == CURRENT
