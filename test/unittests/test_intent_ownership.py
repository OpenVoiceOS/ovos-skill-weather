"""Every weather phrasing has one owning intent file."""
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

import pytest
from ovos_spec_tools.expansion import expand

LOCALE = Path(__file__).resolve().parents[2] / "locale"
LANGS = sorted(p.name for p in LOCALE.iterdir() if (p / "intents").is_dir())
SLOT = "\x00"


def _fold(sentence):
    sentence = re.sub(r"\{[^}]*\}", f" {SLOT} ", sentence)
    sentence = unicodedata.normalize("NFC", sentence).lower()
    sentence = re.sub(rf"[^\w\s{SLOT}]", " ", sentence)
    return re.sub(r"\s+", " ", sentence).strip()


def _vocabularies(lang):
    vocs = {}
    for pattern in ("*.voc", "*.entity"):
        for path in (LOCALE / lang).rglob(pattern):
            vocs[path.stem] = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()
                               if line.strip() and not line.startswith("#")]
    return vocs


def _owners(lang):
    """Folded sentence -> names of the intent files that expand to it."""
    vocs = _vocabularies(lang)
    owners = defaultdict(set)
    for path in sorted((LOCALE / lang / "intents").glob("*.intent")):
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                for sentence in expand(line, vocs):
                    owners[_fold(sentence)].add(path.stem)
    return owners


OWNERS = {lang: _owners(lang) for lang in LANGS}


def _owners_of(lang, utterance):
    """Intents whose templates spell out ``utterance``, a {location} slot standing for any words."""
    folded = _fold(utterance)
    found = set()
    for sentence, names in OWNERS[lang].items():
        pattern = re.escape(sentence).replace(re.escape(SLOT), r".+")
        if re.fullmatch(pattern, folded):
            found |= names
    return found


@pytest.mark.parametrize("lang", LANGS)
def test_no_sentence_is_shared_between_intents(lang):
    shared = {sentence.replace(SLOT, "{}"): sorted(names)
              for sentence, names in OWNERS[lang].items() if len(names) > 1}
    assert not shared, shared


@pytest.mark.parametrize("lang, pattern", [
    ("es-ES", r"llov|nevar|torment"),
    ("es-CO", r"llov|nevar|torment"),
    ("ca-ES", r"nevarà|plourà|tempest"),
    ("oc-FR", r"nevarà|plourà|tempèst"),
])
def test_rain_snow_and_storm_phrasings_are_not_general_forecasts(lang, pattern):
    lines = (LOCALE / lang / "intents" / "weather.intent").read_text(encoding="utf-8").splitlines()
    assert [line for line in lines if re.search(pattern, line, re.I)] == []


@pytest.mark.parametrize("lang, utterance, owner", [
    ("oc-FR", "farà calor deman", "temperature"),
    ("oc-FR", "plourà deman a lisboa", "weather_condition"),
    ("oc-FR", "Farà bon deman a lisboa?", "weather"),
    ("ca-ES", "Farà bo demà a lisboa?", "weather"),
    ("ca-ES", "plourà demà", "weather_condition"),
    ("es-ES", "nevará mañana", "weather_condition"),
    ("es-CO", "Lloverá este fin de semana", "weather_condition"),
])
def test_a_phrasing_has_exactly_one_owner(lang, utterance, owner):
    assert _owners_of(lang, utterance) == {owner}


@pytest.mark.parametrize("lang", ["es-ES", "es-CO"])
def test_every_spanish_rain_sentence_reaches_a_rain_answer(lang):
    """handle_weather_condition answers a sentence only when a condition
    vocabulary matches it; otherwise it falls back to the general forecast."""
    words = [line.strip() for line in
             (LOCALE / lang / "vocabulary" / "weather_condition_intent" / "rain_report.voc")
             .read_text(encoding="utf-8").splitlines() if line.strip()]
    folded_words = [_fold(w) for w in words]
    unreachable = []
    for path in [LOCALE / lang / "intents" / "weather_condition.intent"]:
        for line in path.read_text(encoding="utf-8").splitlines():
            for sentence in expand(line.strip(), _vocabularies(lang)) if line.strip() else []:
                folded = _fold(sentence)
                if re.search(r"\bllov|\bllue", folded) and not any(
                        re.search(rf"\b{re.escape(w)}\b", folded) for w in folded_words):
                    unreachable.append(sentence)
    assert unreachable == []
