"""Pin the spoken times and days that the ovos-date-parser writers give.

Each row sends one utterance through the m2v pipeline with the clock frozen
at Wednesday 2026-03-04 14:35 Europe/Lisbon and Open-Meteo stubbed with a
fixed report: sunrise 07:05, sunset 18:40 on every day. The test checks one
slot of the ``speak`` message metadata. The expected values are written by
hand from the locale grammar, not read back from ovos-date-parser. Every row
is machine-written and needs_manual until a native speaker confirms it. A row
whose current output differs from the grammar is a strict xfail in
``KNOWN_DEFECTS``.

Cases: sunrise and sunset today (time), sunrise tomorrow (day, Thursday) and
the weather on Friday 2026-03-06 (day). Day names compare without case.
"""
import datetime
from unittest import mock

import pytest
import pytz
from ovos_bus_client.message import Message
from ovos_bus_client.session import Session
from ovoscope import CaptureSession, get_m2v_minicroft

SKILL_ID = "ovos-skill-weather.openvoiceos"
TZ = "Europe/Lisbon"
LISBON = pytz.timezone(TZ)
FROZEN = LISBON.localize(datetime.datetime(2026, 3, 4, 14, 35))
HELPERS = "ovos_skill_weather.weather_helpers"

# (case, utterance, dialog, slot, expected)
ROWS = {
    "pt-PT": [
        ("sunrise", "a que horas nasce o sol hoje", "daily_sunrise", "time", "sete e cinco"),
        ("sunset", "a que horas se põe o sol hoje", "daily_sunset", "time", "sete menos vinte"),
        ("sunrise_tomorrow", "a que horas nasce o sol amanhã", "daily_sunrise", "day", "quinta-feira"),
        ("weekday", "como vai estar o tempo na sexta-feira", "daily", "day", "sexta-feira"),
    ],
    "pt-BR": [
        ("sunrise", "a que horas nasce o sol hoje", "daily_sunrise", "time", "sete e cinco"),
        ("sunset", "a que horas o sol se põe hoje", "daily_sunset", "time", "seis e quarenta"),
        ("sunrise_tomorrow", "a que horas nasce o sol amanhã", "daily_sunrise", "day", "quinta-feira"),
        ("weekday", "como vai estar o tempo na sexta-feira", "daily", "day", "sexta-feira"),
    ],
    "es-CO": [
        ("sunrise", "a qué hora amanece hoy", "daily_sunrise", "time", "las siete y cinco"),
        ("sunset", "a qué hora se pone el sol hoy", "daily_sunset", "time", "las siete menos veinte"),
        ("sunrise_tomorrow", "a qué hora amanece mañana", "daily_sunrise", "day", "jueves"),
        ("weekday", "cómo estará el clima el viernes", "daily", "day", "viernes"),
    ],
    "fr-FR": [
        ("sunrise", "à quelle heure se lève le soleil aujourd'hui", "daily_sunrise", "time", "sept heures cinq"),
        ("sunset", "à quelle heure se couche le soleil aujourd'hui", "daily_sunset", "time", "sept heures moins vingt"),
        ("sunrise_tomorrow", "à quelle heure se lève le soleil demain", "daily_sunrise", "day", "jeudi"),
        ("weekday", "quel temps fera-t-il vendredi", "daily", "day", "vendredi"),
    ],
    "it-IT": [
        ("sunrise", "a che ora sorge il sole oggi", "daily_sunrise", "time", "sette e cinque"),
        ("sunset", "a che ora tramonta il sole oggi", "daily_sunset", "time", "sei e quaranta"),
        ("sunrise_tomorrow", "quando c'è l'alba domani", "daily_sunrise", "day", "giovedì"),
        ("weekday", "che tempo farà venerdì", "daily", "day", "venerdì"),
    ],
    "de-DE": [
        ("sunrise", "wann ist heute Sonnenaufgang", "daily_sunrise", "time", "sieben uhr fünf"),
        ("sunset", "wann ist heute Sonnenuntergang", "daily_sunset", "time", "sechs uhr vierzig"),
        ("sunrise_tomorrow", "wann ist morgen Sonnenaufgang", "daily_sunrise", "day", "Donnerstag"),
        ("weekday", "wie wird das Wetter am Freitag", "daily", "day", "Freitag"),
    ],
    "nl-NL": [
        ("sunrise", "hoe laat gaat de zon vandaag op", "daily_sunrise", "time", "vijf over zeven"),
        ("sunset", "hoe laat gaat de zon vandaag onder", "daily_sunset", "time", "twintig voor zeven"),
        ("sunrise_tomorrow", "hoe laat gaat de zon morgen op", "daily_sunrise", "day", "donderdag"),
        ("weekday", "hoe is het weer vrijdag", "daily", "day", "vrijdag"),
    ],
    "da-DK": [
        ("sunrise", "hvornår står solen op", "daily_sunrise", "time", "syv nul fem"),
        ("sunset", "hvad tid går solen ned", "daily_sunset", "time", "seks fyrre"),
        ("sunrise_tomorrow", "hvornår står solen op i morgen", "daily_sunrise", "day", "torsdag"),
        ("weekday", "hvordan bliver vejret på fredag", "daily", "day", "fredag"),
    ],
    "en-US": [
        ("sunrise", "when is sunrise today", "daily_sunrise", "time", "seven oh five"),
        ("sunset", "when is sunset today", "daily_sunset", "time", "six forty"),
        ("sunrise_tomorrow", "when is sunrise tomorrow", "daily_sunrise", "day", "thursday"),
        ("weekday", "what's the forecast for friday", "daily", "day", "friday"),
    ],
}

# (lang, case) -> the defect, with the form a speaker says.
KNOWN_DEFECTS = {
    ("it-IT", "sunrise"): "it-IT nice_time says 07:05 as 'sette e zero cinque'; "
                          "Italian says 'sette e cinque'",
    ("da-DK", "sunrise_tomorrow"): "da-DK 'i morgen' fills the location slot and the "
                                   "geolocation lookup fails; the answer names 'torsdag'",
    ("da-DK", "sunset"): "da-DK 'hvad tid går solen ned' reads as a past date and the skill "
                         "refuses it as historical weather; the answer says 'seks fyrre'",
}


def _report():
    """An Open-Meteo forecast response for 7 days from 2026-03-04 local time."""
    start = datetime.datetime(2026, 3, 4)
    hours = [(start + datetime.timedelta(hours=h)).isoformat(timespec="minutes") for h in range(7 * 24)]
    days = [(start + datetime.timedelta(days=d)).date() for d in range(7)]
    hourly = {"time": hours, "temperature_2m": [15.0] * len(hours),
              "relativehumidity_2m": [70] * len(hours), "windspeed_10m": [10.0] * len(hours),
              "winddirection_10m": [270] * len(hours), "weathercode": [1] * len(hours),
              "shortwave_radiation": [100.0] * len(hours), "precipitation": [0.0] * len(hours),
              "precipitation_probability": [0] * len(hours), "is_day": [1] * len(hours)}
    daily = {"time": [d.isoformat() for d in days],
             "sunrise": [f"{d.isoformat()}T07:05" for d in days],
             "sunset": [f"{d.isoformat()}T18:40" for d in days],
             "temperature_2m_max": [18.0] * 7, "temperature_2m_min": [9.0] * 7,
             "weathercode": [1] * 7, "uv_index_max": [3.0] * 7,
             "precipitation_sum": [0.0] * 7, "precipitation_probability_max": [0] * 7,
             "windspeed_10m_max": [12.0] * 7, "winddirection_10m_dominant": [270] * 7}
    return {"timezone": TZ, "current_weather": {"time": "2026-03-04T14:00"},
            "hourly": hourly, "daily": daily,
            "hourly_units": {"temperature_2m": "°C", "windspeed_10m": "km/h"},
            "daily_units": {"temperature_2m_max": "°C", "windspeed_10m_max": "km/h"}}


def _frozen_now(tz=None):
    return FROZEN.astimezone(tz or LISBON)


@pytest.fixture(scope="module")
def minicroft_factory():
    response = mock.Mock()
    response.json.side_effect = _report
    cache = {}
    with mock.patch(f"{HELPERS}.openmeteo.requests.get", return_value=response), \
            mock.patch(f"{HELPERS}.intent.now_local", _frozen_now), \
            mock.patch(f"{HELPERS}.util.now_local", _frozen_now), \
            mock.patch(f"{HELPERS}.dialog.now_local", _frozen_now), \
            mock.patch(f"{HELPERS}.weather.convert_to_local_datetime",
                       lambda iso, tz: pytz.timezone(tz).localize(datetime.datetime.fromisoformat(iso))):
        def _get(lang):
            if lang not in cache:
                for mc in cache.values():
                    mc.stop()
                cache.clear()
                mc = get_m2v_minicroft([SKILL_ID], lang=lang)
                mc.intents.pipeline_plugins["ovos-m2v-pipeline"]._ensure_model(background_ok=False)
                cache[lang] = mc
            return cache[lang]

        yield _get
        for mc in cache.values():
            mc.stop()


def _spoken(mc, lang, utterance):
    session = Session(f"spoken-{lang}-{utterance}", time_format="half", system_unit="metric",
                      location={"lat": 38.7223, "lon": -9.1393, "tz": TZ})
    session.lang = lang
    message = Message("recognizer_loop:utterance",
                      {"utterances": [utterance], "lang": lang},
                      {"session": session.serialize(), "source": "A", "destination": "B"})
    capture = CaptureSession(mc)
    capture.capture(message, timeout=30)
    return [m for m in capture.finish() if m.msg_type in ("speak", "ovos.utterance.speak")]


PARAMS = []
for _lang, _rows in ROWS.items():
    for _row in _rows:
        marks = []
        if (_lang, _row[0]) in KNOWN_DEFECTS:
            marks.append(pytest.mark.xfail(strict=True, reason=KNOWN_DEFECTS[(_lang, _row[0])]))
        PARAMS.append(pytest.param(_lang, *_row, id=f"{_lang}-{_row[0]}", marks=marks))


@pytest.mark.timeout(600)
@pytest.mark.parametrize("lang,case,utterance,dialog,slot,expected", PARAMS)
def test_spoken_slot(minicroft_factory, lang, case, utterance, dialog, slot, expected):
    speaks = _spoken(minicroft_factory(lang), lang, utterance)
    values = [m.data["meta"]["data"][slot] for m in speaks
              if m.data.get("meta", {}).get("dialog", "").startswith(dialog)
              and slot in m.data["meta"].get("data", {})]
    assert values, f"{utterance!r}: spoke {[m.data.get('meta') for m in speaks]!r}"
    value = values[0]
    if slot == "day":
        value, expected = value.casefold(), expected.casefold()
    assert value == expected
