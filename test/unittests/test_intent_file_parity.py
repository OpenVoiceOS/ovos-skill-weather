"""Every intent the en-US locale defines exists in every shipped locale.

A locale without an intent file cannot answer that intent at all, and the
golden runner cannot see it: an intent with no file has no prototype, so its
rows simply miss. ``GOLDEN_INTENT_GAPS`` exempts an intent from the golden
floor, never from this check.
"""
from pathlib import Path

LOCALES = Path(__file__).resolve().parents[2] / "locale"


def sample_lines(path: Path) -> list:
    return [l for l in path.read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.lstrip().startswith("#")]


def test_every_locale_has_every_en_us_intent_with_a_sample_line():
    reference = sorted(p.name for p in (LOCALES / "en-US" / "intents").glob("*.intent"))
    assert reference, "en-US defines no .intent files"
    problems = []
    for locale in sorted(d for d in LOCALES.iterdir() if d.is_dir()):
        for name in reference:
            path = locale / "intents" / name
            if not path.is_file():
                problems.append(f"{locale.name}: {name} is missing")
            elif not sample_lines(path):
                problems.append(f"{locale.name}: {name} has no sample line")
    assert not problems, "\n  ".join(["intent files differ from en-US:"] + problems)
