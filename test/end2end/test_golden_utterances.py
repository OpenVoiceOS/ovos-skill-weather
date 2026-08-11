"""Golden-utterance end-to-end coverage for ovos-skill-weather (en-US).

The golden corpus (``golden_utterances.jsonl``) is a vendored slice of the
shared ovoscope golden-utterance dataset, keyed by
``skill_id == "ovos-skill-weather.openvoiceos"``. One shared ``MiniCroft``
(module-scoped fixture) is booted for the whole suite; every row is its own
parametrized test item.

The skill is network-bound (Open-Meteo + geolocation). Following the same
mechanism as ``test_intents_en_us.py``, the two network boundaries are
patched for the duration of the module so routing is exercised offline and
deterministically:

* ``get_geolocation`` returns a fixed location, and
* ``get_report`` raises ``ConnectionError`` so the handler takes its
  already-tested generic error branch and still routes + speaks.

Naming note: the corpus encodes adapt intents by their bare name (eg.
``"weather"``, ``"is_cloudy"``) and padacioso intents with the ``.intent``
file suffix (eg. ``"current_weather.intent"``). Both forms are used verbatim
as the routed intent id, matching how the existing baseline suite asserts
intent routing (``_matches_intent`` in ``test_intents_en_us.py``), so this
suite reuses the same tolerant matcher rather than inventing a second one.
"""
import json
import re
from pathlib import Path
from unittest.mock import patch

import pytest
from ovos_bus_client.message import Message
from ovos_bus_client.session import Session
from ovoscope import CaptureSession, get_minicroft

SKILL_ID = "ovos-skill-weather.openvoiceos"
LANG = "en-US"

_PIPELINE = [
    "ovos-padacioso-pipeline-plugin-high",
    "ovos-adapt-pipeline-plugin-high",
    "ovos-padacioso-pipeline-plugin-medium",
    "ovos-adapt-pipeline-plugin-medium",
    "ovos-adapt-pipeline-plugin-low",
]

GOLDEN_PATH = Path(__file__).parent / "golden_utterances.jsonl"

_FAKE_GEOLOCATION = {
    "city": "London",
    "region": "England",
    "country": "United Kingdom",
    "latitude": 51.5074,
    "longitude": -0.1278,
    "timezone": "Europe/London",
}


def _raise_no_network(*_args, **_kwargs):
    raise ConnectionError("network disabled in e2e routing tests")


# utterances lifted verbatim from OTHER skills' golden-utterance slices,
# picked for lexical overlap with weather's "tell me"/"forecast"/date
# vocabulary.
NEGATIVE_UTTERANCES = [
    ("set an alarm for tomorrow at 8 am", "ovos-skill-alerts.openvoiceos"),
    ("remind me to call mom tomorrow", "ovos-skill-alerts.openvoiceos"),
    ("what time is it", "ovos-skill-date-time.openvoiceos"),
    ("what is today's date", "ovos-skill-date-time.openvoiceos"),
    ("what day is it tomorrow", "ovos-skill-date-time.openvoiceos"),
    ("tell me a joke", "ovos-skill-icanhazdadjokes.openvoiceos"),
    ("tell me the news", "ovos-skill-news.openvoiceos"),
]


def _matches_intent(msg_type: str, skill_id: str, intent_label: str) -> bool:
    """Same tolerant matcher as ``test_intents_en_us.py``: compare the
    ``:``-suffix basename, extension-stripped and case/punct-insensitive,
    so the assertion doesn't pin the wire format of any one pipeline
    plugin."""
    prefix = f"{skill_id}:"
    if not msg_type.startswith(prefix):
        return False
    observed = msg_type[len(prefix):]
    observed_base = observed.rsplit(".", 1)[0] if observed.endswith(".intent") else observed
    expected_base = intent_label.rsplit(".", 1)[0] if intent_label.endswith(".intent") else intent_label
    norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())
    return norm(observed_base) == norm(expected_base)


# Rows that do not currently route correctly, with the root-caused reason.
# Every reason below was confirmed by isolated investigation (bypassing the
# bus, calling ``padacioso.IntentContainer``/the adapt ``IntentBuilder``
# directly) AND by re-running the whole suite against the CI-pinned
# padacioso==2.2.3a1 before being accepted as a real, out-of-scope defect
# rather than a corpus mistake or a stale/version-drifted claim. All xfails
# are ``strict=True``: a row that starts passing must fail the build. See
# the PR description for the full investigation.
#
# "adapt-collision" and "content-gap" (the other two categories originally
# tracked here) were both fixed in a follow-up PR that extended the en-US
# ``.intent`` templates (day+time-of-day temperature phrasing, "for <day> at
# <time>"/"in {location}" forecast phrasing, umbrella/rain-jacket phrasing)
# so the specific padacioso templates now win the pipeline before the
# skill's generic ``weather`` adapt intent gets a chance to fire. See that
# PR's description for the per-row table.
#
# The former "adapt-no-keyword" category (10 rows: "celsius", "celsius
# celsius", "celsius Lawrence kansas", "celsius today", "celsius days",
# "today", "today today", "today days", "today Lawrence kansas", "today
# give me") was a corpus defect, not a skill defect: those utterances were
# unfilled/duplicated template fragments with no intent-bearing content.
# They have been fixed or removed at the corpus source, so this table is
# empty -- no row in the current corpus is expected to fail.
_XFAIL_REASONS = {}


def _load_golden_rows():
    rows = []
    with open(GOLDEN_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("needs_manual"):
                continue
            rows.append(row)
    return rows


def _as_param(row):
    reason = _XFAIL_REASONS.get(row["utterance"])
    if reason is None:
        return pytest.param(row, id=row["utterance"])
    return pytest.param(
        row,
        id=row["utterance"],
        # strict: every reason below was confirmed to reproduce
        # deterministically both locally (fresh venv, ovoscope==1.6.5a1) and
        # in this PR's own CI run under the actually-resolved
        # padacioso==2.2.3a1. A row that starts routing correctly again (the
        # underlying defect gets fixed) must fail the build so the fix
        # doesn't go unnoticed -- that's the whole point of tracking these
        # as xfail instead of skipping them.
        marks=pytest.mark.xfail(reason=reason, strict=True),
    )


GOLDEN_ROWS = [_as_param(r) for r in _load_golden_rows()]


@pytest.fixture(scope="module")
def minicroft():
    patchers = [
        patch(
            "ovos_skill_weather.weather_helpers.intent.get_geolocation",
            return_value=dict(_FAKE_GEOLOCATION),
        ),
        patch("ovos_skill_weather.get_report", side_effect=_raise_no_network),
    ]
    for p in patchers:
        p.start()
    mc = get_minicroft([SKILL_ID])
    yield mc
    mc.stop()
    for p in patchers:
        p.stop()


def _golden_id(row):
    return row["utterance"]


@pytest.mark.timeout(60)
@pytest.mark.parametrize("row", GOLDEN_ROWS)
def test_golden_utterance(minicroft, row):
    session = Session(f"golden-{_golden_id(row)}")
    session.lang = LANG
    session.pipeline = list(_PIPELINE)
    session.blacklisted_intents = []
    utterance = Message(
        "recognizer_loop:utterance",
        {"utterances": [row["utterance"]], "lang": LANG},
        {"session": session.serialize(), "source": "A", "destination": "B"},
    )
    capture = CaptureSession(minicroft)
    capture.capture(utterance, timeout=30)
    messages = capture.finish()
    types = [m.msg_type for m in messages]
    assert any(_matches_intent(t, SKILL_ID, row["intent_label"]) for t in types), (
        f"{row['utterance']!r}: expected {SKILL_ID}:{row['intent_label']}, got {types!r}"
    )
    assert any("speak" in t for t in types)


@pytest.mark.timeout(60)
@pytest.mark.parametrize("negative", NEGATIVE_UTTERANCES, ids=lambda n: n[0])
def test_negative_confusable_not_claimed(minicroft, negative):
    text, source_skill = negative
    session = Session(f"negative-{text}")
    session.lang = LANG
    session.pipeline = list(_PIPELINE)
    session.blacklisted_intents = []
    utterance = Message(
        "recognizer_loop:utterance",
        {"utterances": [text], "lang": LANG},
        {"session": session.serialize(), "source": "A", "destination": "B"},
    )
    capture = CaptureSession(minicroft)
    capture.capture(utterance, timeout=30)
    messages = capture.finish()
    claimed = any(m.msg_type.startswith(f"{SKILL_ID}:") for m in messages)
    assert not claimed, f"{text!r} (from {source_skill}) was incorrectly claimed by {SKILL_ID}"
