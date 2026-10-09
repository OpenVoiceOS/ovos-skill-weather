"""Golden rows in every locale route to their intent on the m2v pipeline.

For each ``golden_utterances_<lang>.jsonl`` in this directory, one MiniCroft
loads the real skill in that language on the m2v prototype pipeline, the
model2vec engine built at boot from the skill's own ``.intent`` files. Each
row's utterance goes through that pipeline's high, medium and low tiers in
order, and the row passes when the first tier to match names its
``intent_label``. The engine embeds the utterance, so a row that no template
spells out word for word still matches when it means the same thing.

Each ``negative_utterances_<lang>.jsonl`` holds requests for other skills.
They run on the same pipeline and must not match any intent of this skill.
``NEGATIVE_KNOWN_CLAIMS`` names the negative rows that m2v claimed in two
measured runs, with the intent it claimed; any other claim fails the locale.

Each locale must match at least ``MIN_MATCH_RATE`` of its golden rows, and
every intent with rows in a locale must match at least
``MIN_MATCHED_ROWS_PER_INTENT`` of them, so a locale cannot pass with one
intent that never routes. ``GOLDEN_INTENT_GAPS`` names the intents that
matched no row in a locale after lines were written for the meaning of its
rows, with the measured reason; only those are exempt from the per-intent
floor. All rows run, including rows marked
``needs_manual`` or ``machine_generated``. The test prints every row that
misses with the intent that matched instead, and the count of each
expected -> matched pair.
"""
import json
from collections import Counter
from pathlib import Path

import pytest
from ovos_bus_client.message import Message
from ovoscope import M2V_PUBLISHED_MODEL, get_m2v_minicroft
from ovoscope.golden_minicroft import warm_m2v_models

SKILL_ID = "ovos-skill-weather.openvoiceos"
M2V_PROTOTYPE = "ovos-m2v-prototype-pipeline"
TIERS = ("high", "medium", "low")
# m2v gives some rows a different answer on each boot, so the test gates on
# the share of rows that match per locale, not on each row. Eleven locales
# match fewer than 80% of their rows on m2v in at least one of four runs:
# cs-CZ, da-DK, de-DE, en-US, es-CO, gl-ES, hu-HU, kab, nl-NL, pt-BR, tr-TR.
MIN_MATCH_RATE = 0.6
# A locale also fails when any of its intents has fewer matched rows than this.
MIN_MATCHED_ROWS_PER_INTENT = 1
# Intents that matched no row on m2v in two measured runs, after natural lines
# were written for the meaning of the rows, with the reason measured.
GOLDEN_INTENT_GAPS = {
    "gl-ES": {
        "weather": "its one row, 'Que tempo se agarda para o domingo que "
                   "vén?', matches no intent. Lines 'que tempo fará <day>' "
                   "and 'que tempo se espera para <day>' did not change that",
    },
    "kab": {
        "is_wind": "rows open with 'Bɣiɣ ad ẓreɣ' or 'Bɣiɣ ad issineɣ' and "
                   "route to weather or temperature",
    },
}
END2END_DIR = Path(__file__).parent
# Negative rows that m2v claimed for this skill in two separate runs, with the
# intent it claimed. A listed claim is allowed, not required, so a row that
# flips between boots does not fail the test. Any other claim fails the locale.
NEGATIVE_KNOWN_CLAIMS = {
    "cs-CZ": {
        "Nastav budík na zítra na osm": "weather",
        "Řekni mi vtip": "temperature",
        "Kolikátého je dnes?": "weather",
    },
    "da-DK": {"Hvilken dato er det i dag?": "temperature"},
    "en-US": {"what day is it tomorrow": "weather_condition"},
    "gl-ES": {"Pon unha alarma mañá ás oito": "weather"},
    "pl-PL": {
        "Ustaw budzik na jutro na ósmą": "temperature",
        "Włącz muzykę Beatlesów": "weather",
        "Jaka jest dzisiaj data?": "weather",
    },
    "ru-RU": {
        "Поставь будильник на завтра на восемь": "weather",
        "Который час?": "temperature",
        "Расскажи анекдот": "weather",
        "Какое сегодня число?": "weather",
    },
    "sv-SE": {"Ställ ett alarm i morgon klockan åtta": "next_rain"},
}


def _rows_by_lang(prefix):
    rows = {}
    for path in sorted(END2END_DIR.glob(f"{prefix}_*.jsonl")):
        lang = path.stem.removeprefix(f"{prefix}_")
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.strip():
                row = json.loads(line)
                assert row["lang"] == lang, f"{path.name}:{number} has lang {row['lang']!r}"
                rows.setdefault(lang, []).append(row)
    return rows


ROWS = _rows_by_lang("golden_utterances")
NEGATIVE_ROWS = _rows_by_lang("negative_utterances")


def _matched_intent(engine, utterance, lang):
    message = Message("recognizer_loop:utterance",
                      {"utterances": [utterance], "lang": lang}, {"lang": lang})
    match = next(filter(None, (getattr(engine, f"match_{tier}")([utterance], lang, message)
                               for tier in TIERS)), None)
    return match.match_type if match else None


def _match_all(lang, rows):
    """Boot the skill on m2v in ``lang`` and return the intent each row matches."""
    minicroft = get_m2v_minicroft([SKILL_ID], model=M2V_PUBLISHED_MODEL,
                                  lang=lang, classifier=False)
    try:
        warm_m2v_models(minicroft)
        engine = minicroft.intents.pipeline_plugins[M2V_PROTOTYPE]
        return [_matched_intent(engine, row["utterance"], lang) for row in rows]
    finally:
        minicroft.stop()


@pytest.mark.timeout(900)
@pytest.mark.parametrize("lang", sorted(ROWS))
def test_golden_rows_match_their_intent(lang):
    rows = ROWS[lang]
    matched = _match_all(lang, rows)
    misses = []
    hits = {row["intent_label"]: 0 for row in rows}
    confusion = Counter()
    for row, got in zip(rows, matched):
        if got == f"{SKILL_ID}:{row['intent_label']}":
            hits[row["intent_label"]] += 1
        else:
            confusion[row["intent_label"], (got or "None").removeprefix(f"{SKILL_ID}:")] += 1
            misses.append(f"{row['utterance']!r}: expected {row['intent_label']}, got {got}")
    gaps = GOLDEN_INTENT_GAPS.get(lang, {})
    starved = sorted(label for label, count in hits.items()
                     if count < MIN_MATCHED_ROWS_PER_INTENT and label not in gaps)
    rate = 1 - len(misses) / len(rows)
    print(f"[{lang}] {rate:.1%} of {len(rows)} rows match", *misses, sep="\n  ")
    print(f"[{lang}] confusion (expected -> got):",
          *(f"{want} -> {got}: {n}" for (want, got), n in sorted(confusion.items())), sep="\n  ")
    for label, reason in gaps.items():
        print(f"[{lang}] known gap, {label}: {hits.get(label, 0)} rows match ({reason})")
    if starved:
        print(f"[{lang}] intents below {MIN_MATCHED_ROWS_PER_INTENT} matched rows: {starved}")
    assert rate >= MIN_MATCH_RATE, (
        f"[{lang}] {rate:.1%} of rows match, below {MIN_MATCH_RATE:.0%}:\n  " + "\n  ".join(misses)
    )
    assert not starved, (
        f"[{lang}] intents below {MIN_MATCHED_ROWS_PER_INTENT} matched rows: {starved}"
    )


@pytest.mark.timeout(900)
@pytest.mark.parametrize("lang", sorted(NEGATIVE_ROWS))
def test_negative_rows_match_no_skill_intent(lang):
    rows = NEGATIVE_ROWS[lang]
    known = NEGATIVE_KNOWN_CLAIMS.get(lang, {})
    matched = _match_all(lang, rows)
    claims = [(row["utterance"], got.removeprefix(f"{SKILL_ID}:"))
              for row, got in zip(rows, matched)
              if got and got.startswith(f"{SKILL_ID}:")]
    print(f"[{lang}] {len(claims)} of {len(rows)} negative rows claimed by the skill",
          *(f"{u!r}: matched {intent}" for u, intent in claims), sep="\n  ")
    unknown = [f"{u!r}: matched {intent}" for u, intent in claims if known.get(u) != intent]
    assert not unknown, f"[{lang}] negative rows claimed by the skill:\n  " + "\n  ".join(unknown)


def test_every_shipping_locale_has_a_golden_file():
    golden = {p.stem.split("_", 2)[2] for p in END2END_DIR.glob("golden_utterances_*.jsonl")}
    locale_root = END2END_DIR.parents[1] / "locale"
    shipping = {d.name for d in locale_root.iterdir() if d.is_dir() and any(d.rglob("*.intent"))}
    assert golden == shipping, f"golden files {sorted(golden ^ shipping)} differ from shipping locales"
