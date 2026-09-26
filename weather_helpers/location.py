"""Resolve a spoken place name that carries a case ending or is an exonym.

The `{location}` slot is the only path a place name takes into this skill
(`location.rx` was dead in every locale and is gone, #286), and the slot holds
the word exactly as it was said. In a case-marking language that word is
inflected, and in any language it may be that language's own name for a foreign
city. Measured against the live service (localize, T-5509 and T-5565):

    Helsingissä -> Helsinki            Tampereella -> not found
    Turussa     -> Turku               Rovaniemellä -> not found
    Budapesten  -> Budapest            Szegeden    -> not found
    İstanbul'da -> İstanbul            Ankarada    -> Etimesgut, a DISTRICT
                                       Lontoo      -> City of Westminster
                                       Peking, Tokio -> districts
                                       Meksiko     -> Villa de Cos
                                       Souli       -> a Greek village

Two failure shapes, and the second is worse: a miss makes the skill say it does
not know the place, while a district-level or unrelated answer makes it read a
forecast for somewhere else out loud, with no sign anything went wrong.

The answer here has two halves.

**Candidates.** One spoken form yields an ordered list of things to look up: the
form as said, then its exonym if this locale has one on record, then the form
with a case ending removed, and then that with a final-vowel restoration for the
Finnish and Hungarian stems that change under inflection (Rovaniemi ->
Rovaniemellä loses the i). The first candidate the service answers acceptably
wins. Nothing is guessed about a language's grammar beyond the suffix list.

**Acceptance.** A result is accepted only when the name it returns and the name
asked for share a prefix, compared with diacritics folded and case ignored.
"Helsingissä" against Helsinki shares six characters and is accepted;
"Ankarada" against Etimesgut shares none and is refused, so the next candidate
(Ankara) is tried and answers itself. This is what stops a district answer from
being spoken as the city, and it needs no list of districts.

An exonym has no prefix relation to its endonym (Peking and Beijing share one
character), so the exonym table is what carries those. It is data, not grammar:
`locale/<lang>/exonyms.json`, a flat map of the spoken form to the name the
service knows. The tables here hold only the forms measured above; a native
reviewer for the locale extends them (localize owns that file's content).
"""
import json
import unicodedata
from pathlib import Path
from typing import Dict, Iterator, List, Optional

# Case endings, longest first, for the languages whose place names reach the
# geocoder inflected. Only endings a place name actually takes are listed: a
# broader list would strip real final syllables off uninflected names.
CASE_ENDINGS: Dict[str, List[str]] = {
    # Finnish: the local cases, which is what "in/at <place>" uses.
    "fi": ["ssa", "ssä", "sta", "stä", "lla", "llä", "lta", "ltä",
           "seen", "hun", "han", "hin", "in", "on", "un", "yn", "än", "ön"],
    # Hungarian: the inessive/superessive family, plus the -ra/-re forms.
    "hu": ["ban", "ben", "ba", "be", "ról", "rõl", "ről", "ra", "re",
           "on", "en", "ön", "ön", "n"],
    # Turkish: the locative, written attached or after an apostrophe.
    "tr": ["'da", "'de", "'ta", "'te", "da", "de", "ta", "te"],
}

# Inflection changes a stem's last vowel, and it lengthens one. Finnish
# Rovaniemi becomes Rovaniemellä (i -> e) and Tampere becomes Tampereella
# (e -> ee), so a stripped stem is offered again with its final vowel replaced
# and with a doubled final vowel collapsed. These two transforms cover every
# form measured under T-5509; nothing else about the grammar is guessed.
FINAL_VOWELS: Dict[str, List[str]] = {
    "fi": ["i", "e", "a", "ä", "o", "y", "u", "ö"],
    "hu": ["i", "e", "a", "o"],
    "tr": ["i", "e", "a"],
}

# Every candidate that misses costs one request to the geolocation service, and
# that service rate-limits: measured 2026-09-26, it answered status 429 to every
# query for a while after a locale sweep had walked it. So the list is short on
# purpose, and ordered best-first. A rate limit is not a miss: get_geolocation
# raises ConnectionError, which propagates out of the loop on the first attempt
# rather than being retried with a different spelling.
MAX_CANDIDATES = 5

_EXONYM_CACHE: Dict[str, Dict[str, str]] = {}


def fold(text: str) -> str:
    """Lowercase and strip diacritics, so ä and a compare equal."""
    decomposed = unicodedata.normalize("NFD", text.casefold())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _lang_code(lang: Optional[str]) -> str:
    return (lang or "en").replace("_", "-").split("-")[0].lower()


def load_exonyms(locale_dir: Path, lang: Optional[str]) -> Dict[str, str]:
    """The locale's spoken-form-to-endonym map, or an empty one.

    The file is optional and locale content: a locale with no exonym problem
    ships none. A malformed file is ignored rather than raised, because a place
    lookup must not fail on it; the parity tests are what keep it well formed.
    """
    code = _lang_code(lang)
    if code in _EXONYM_CACHE:
        return _EXONYM_CACHE[code]
    table: Dict[str, str] = {}
    for candidate in sorted(locale_dir.glob("*/exonyms.json")):
        if _lang_code(candidate.parent.name) != code:
            continue
        try:
            loaded = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(loaded, dict):
            for spoken, endonym in loaded.items():
                if isinstance(spoken, str) and isinstance(endonym, str):
                    table[fold(spoken)] = endonym
    _EXONYM_CACHE[code] = table
    return table


def _stem_variants(stem: str, code: str) -> Iterator[str]:
    """The stem, then the stem with its final vowel undoubled or replaced."""
    yield stem
    vowels = FINAL_VOWELS.get(code, [])
    if not vowels or len(stem) < 2:
        return
    last, before = fold(stem[-1]), fold(stem[-2])
    if last == before and last in {fold(v) for v in vowels}:
        # Tampereella -> "Tamperee" -> Tampere
        yield stem[:-1]
    for vowel in vowels:
        if fold(vowel) == last:
            continue
        # Rovaniemellä -> "Rovanieme" -> Rovaniemi
        yield stem[:-1] + vowel


def strip_case_ending(spoken: str, lang: Optional[str]) -> Iterator[str]:
    """The spoken form with one case ending removed, longest ending first."""
    code = _lang_code(lang)
    folded = fold(spoken)
    for ending in CASE_ENDINGS.get(code, []):
        if not folded.endswith(fold(ending)):
            continue
        stem = spoken[: len(spoken) - len(ending)]
        # a stem shorter than three characters is not a place name; stripping
        # "de" off "Ede" would leave "E" and match anything.
        if len(fold(stem)) < 3:
            continue
        for form in _stem_variants(stem, code):
            yield form


def location_candidates(spoken: str, lang: Optional[str],
                        exonyms: Optional[Dict[str, str]] = None) -> List[str]:
    """Every form to try for one spoken place name, best first.

    The form as said comes first unless the locale records an exonym for it, so
    an uninflected name costs no extra lookup and nothing changes for a
    language with no case endings and no exonym table.
    """
    exonyms = exonyms or {}
    out: List[str] = []

    def add(value: str):
        value = value.strip()
        if value and not any(fold(value) == fold(seen) for seen in out):
            out.append(value)

    # A locale's own exonym comes first, ahead of the form as said: when the
    # locale records that "Souli" means Seoul, a service that answers with the
    # Greek village of that very name must not win on the prefix rule.
    if fold(spoken) in exonyms:
        add(exonyms[fold(spoken)])
    add(spoken)
    for stem in strip_case_ending(spoken, lang):
        add(stem)
        if fold(stem) in exonyms:
            add(exonyms[fold(stem)])
    return out[:MAX_CANDIDATES]


# How many characters the asked-for name and the answer must share. Three is
# what the measurements need: Turussa and Turku share exactly "tur", because
# Finnish consonant gradation changes the stem, and four would refuse a lookup
# that works today. Three still refuses every district answer measured
# (Ankarada/Etimesgut, Lontoo/City of Westminster, Meksiko/Villa de Cos,
# Peking/Chaoyang, Tokio/Shinjuku), and it accepts Tokio/Tokyo, which is the
# right city.
PREFIX_MATCH = 3


def answer_names_the_place(asked: str, returned: str) -> bool:
    """Does the service's answer name the place that was asked for?

    A district answer is the dangerous one: the lookup succeeds and the skill
    speaks a forecast for somewhere else. Comparing a folded prefix refuses it
    without a list of districts to maintain.
    """
    a, b = fold(asked), fold(returned)
    if not a or not b:
        return False
    if a.startswith(b) or b.startswith(a):
        return True
    shared = 0
    for x, y in zip(a, b):
        if x != y:
            break
        shared += 1
    return shared >= min(PREFIX_MATCH, len(a), len(b))
