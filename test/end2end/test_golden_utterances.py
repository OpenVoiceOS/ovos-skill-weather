"""Golden rows route to their intent on the m2v prototype pipeline, and
negative rows reach no intent of this skill."""
import json
from pathlib import Path

import pytest
from ovos_bus_client.message import Message
from ovoscope.routing import TALLY, get_prototype_minicroft

SKILL_ID = "ovos-skill-weather.openvoiceos"
END2END_DIR = Path(__file__).parent


def _rows(prefix):
    rows = []
    for path in sorted(END2END_DIR.glob(f"{prefix}*.jsonl")):
        rows += [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
                 if line.strip()]
    return rows


GOLDEN = _rows("golden_utterances_")
NEGATIVE = _rows("negative_utterances_")
_booted = {}

# Known routing gaps, keyed by (lang, utterance), each with its issue number.
# A strict xfail asserts directly, because TALLY skips a misrouted row.
KNOWN_GAPS = {
    ("pt-BR", "Como tá o tempo lá fora?"): 348,
    ("pt-BR", "Vai nevar amanhã em Gramado?"): 348,
    ("pt-BR", "Vai fazer sol no sábado?"): 348,
    ("es-ES", "¿Necesito el chubasquero mañana?"): 349,
    ("es-CO", "¿Llevo sombrilla hoy?"): 350,
    ("es-CO", "¿Va a hacer sol el sábado?"): 350,
    ("fr-FR", "Quelle sera la minimale cette nuit ?"): 351,
    ("nl-NL", "Komt er vanmiddag onweer?"): 352,
    ("nl-NL", "Wanneer valt de volgende bui in Utrecht?"): 352,
    ("da-DK", "Skinner solen på lørdag?"): 353,
}


@pytest.fixture(scope="module")
def engine_for():
    def engine(lang):
        if lang not in _booted:
            for minicroft in _booted.values():
                minicroft.stop()
            _booted.clear()
            _booted[lang] = get_prototype_minicroft([SKILL_ID], lang=lang)
        return _booted[lang].intents.pipeline_plugins["ovos-m2v-prototype-pipeline"]
    yield engine
    for minicroft in _booted.values():
        minicroft.stop()


def _routed(engine, row):
    message = Message("recognizer_loop:utterance",
                      {"utterances": [row["utterance"]], "lang": row["lang"]}, {"lang": row["lang"]})
    match = engine.match_low([row["utterance"]], row["lang"], message)
    return [match.match_type] if match else []


def _row_id(row):
    return f"{row['lang']}:{row['utterance']}"


def _golden_param(row):
    issue = KNOWN_GAPS.get((row["lang"], row["utterance"]))
    if issue is None:
        return pytest.param(row, id=_row_id(row))
    mark = pytest.mark.xfail(reason=f"routing gap, issue #{issue}", strict=True)
    return pytest.param(row, id=_row_id(row), marks=mark)


@pytest.mark.parametrize("row", [_golden_param(r) for r in GOLDEN])
def test_golden_row_routes_to_its_intent(engine_for, row):
    fired = _routed(engine_for(row["lang"]), row)
    if (row["lang"], row["utterance"]) in KNOWN_GAPS:
        assert f"{SKILL_ID}:{row['intent_label']}" in fired
        return
    TALLY.assert_routed(row["utterance"], f"{SKILL_ID}:{row['intent_label']}", fired)


@pytest.mark.parametrize("row", NEGATIVE, ids=_row_id)
def test_negative_row_reaches_no_intent_of_the_skill(engine_for, row):
    fired = _routed(engine_for(row["lang"]), row)
    TALLY.assert_not_routed(row["utterance"],
                            [t for t in fired if t.startswith(f"{SKILL_ID}:")], fired)


def test_every_shipping_locale_has_a_golden_file():
    golden = {p.stem.split("_", 2)[2] for p in END2END_DIR.glob("golden_utterances_*.jsonl")}
    locale_root = END2END_DIR.parents[1] / "locale"
    shipping = {d.name for d in locale_root.iterdir() if d.is_dir() and any(d.rglob("*.intent"))}
    assert golden == shipping, f"golden files {sorted(golden ^ shipping)} differ from shipping locales"


def test_da_population_question_is_not_weather_condition(engine_for):
    # ovos-m2v-pipeline#360: weather_condition.required keeps it out
    row = {"utterance": "hvor mange bor der i københavn", "lang": "da-DK"}
    assert f"{SKILL_ID}:weather_condition" not in _routed(engine_for("da-DK"), row)
