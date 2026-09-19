"""Every hot-or-cold phrasing must reach the branch it asks for.

`handle_is_it_hot_or_cold` picks the temperature it reports with
`voc_match(utterance, "hot")`, so a locale line that asks about heat in a word
absent from that locale's `hot.voc` is answered with the LOW temperature. The
line parses, the intent matches, the skill replies, and the reply is wrong --
no parity or expansion check can see it.

`voc_match` matches whole words, so an inflected form is a different word:
`varm` in the vocabulary does not match `varmt` in the sentence.
"""
import re
from pathlib import Path

from ovos_spec_tools.expansion import expand

LOCALES = Path(__file__).resolve().parents[2] / "locale"


def voc_words(locale: Path, name: str) -> list:
    p = locale / "vocabulary" / "temperature" / f"{name}.voc"
    if not p.is_file():
        return []
    return [l.strip() for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def matches(utterance: str, words: list) -> bool:
    # the rule ovos-workshop's voc_match applies: whole words, case-insensitive
    return any(re.match(r".*\b" + re.escape(w) + r"\b.*", utterance, re.IGNORECASE)
               for w in words)


def test_every_locale_can_reach_the_high_temperature():
    """Some phrasing in each locale must match its own hot.voc.

    A locale whose file asks about heat in words its `hot.voc` does not carry
    can never report the high temperature, whatever the user says. Only the
    hot branch is asserted: a cold phrasing that matches nothing falls to the
    low temperature, which is the answer it wanted anyway.
    """
    # These four cannot reach it either, and no phrasing in this repository
    # tells us which word they should carry: cs-CZ and sv-FI hold words from
    # another language entirely, and pl-PL and ru-RU hold an adjective where
    # their sentences use an adverb. Naming them keeps the check strict for
    # every other locale and fails the moment a fifth appears; each wants a
    # native speaker rather than a guess.
    WANTS_A_NATIVE_SPEAKER = {"cs-CZ", "pl-PL", "ru-RU", "sv-FI"}

    unreachable = []
    for locale in sorted(LOCALES.iterdir()):
        if locale.name in WANTS_A_NATIVE_SPEAKER:
            continue
        intent = locale / "intents" / "is_hot_or_cold.intent"
        hot = voc_words(locale, "hot")
        if not intent.is_file() or not hot:
            continue
        sentences = [s for line in intent.read_text(encoding="utf-8").splitlines()
                     if line.strip() for s in expand(line)]
        if not any(matches(s, hot) for s in sentences):
            unreachable.append(f"{locale.name}: hot.voc holds {hot}, and no "
                               f"line in its intent file uses any of them")
    assert not unreachable, (
        "these locales can never report the high temperature:\n  "
        + "\n  ".join(unreachable))


#: One heat phrasing per locale this file adds, with the word the handler has
#: to recognise. Each of these reported the LOW temperature before the
#: vocabulary carried the inflected form the sentence actually uses.
ADDED_HEAT_PHRASINGS = [
    ("da-DK", "Bliver det varmt på mandag i Berlin?"),
    ("es-ES", "¿Hará calor el lunes en Berlín?"),
    ("gl-ES", "Vai facer calor o luns en Berlín?"),
    ("pt-BR", "Vai fazer calor no domingo em Berlim?"),
]


def test_the_added_heat_phrasings_report_the_high_temperature():
    wrong = [f"{loc}: {sentence}" for loc, sentence in ADDED_HEAT_PHRASINGS
             if not matches(sentence, voc_words(LOCALES / loc, "hot"))]
    assert not wrong, (
        "these ask about heat and match no word in their locale's hot.voc, so "
        "`handle_is_it_hot_or_cold` answers with the low temperature:\n  "
        + "\n  ".join(wrong))
