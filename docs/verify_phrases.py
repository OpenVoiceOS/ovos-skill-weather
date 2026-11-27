"""Send each phrase quoted in docs/usage.md to a padacioso container of the en-US intents.

Each phrase must start the intent named in the heading of its section.
"""
import re
import sys
from pathlib import Path

from padacioso import IntentContainer
from ovos_spec_tools.resources import LocaleResources

LANG = "en-US"
res = LocaleResources("locale")
container = IntentContainer()
for path in sorted(Path("locale", LANG, "intents").glob("*.intent")):
    container.add_intent(path.stem, res.load_intent(path.stem, LANG))

phrases = []
expected = None
for line in Path("docs/usage.md").read_text().splitlines():
    if line.startswith("## "):
        found = re.search(r"`(\w+)`$", line)
        expected = found.group(1) if found else None
    elif quoted := re.match(r'- "([^"]+)"', line):
        phrases.append((expected, quoted.group(1)))

missed = 0
for expected, phrase in phrases:
    utterance = re.sub(r"[.?!]+$", "", phrase).lower()
    match = container.calc_intent(utterance)
    name = match.get("name") if match else None
    missed += name != expected
    print(f"{'ok  ' if name == expected else 'MISS'} {expected:18} {name or 'NO MATCH':18} {phrase}")
print(f"{len(phrases)} phrases, {missed} not routed to the intent of their section")
sys.exit(1 if missed or not phrases else 0)
