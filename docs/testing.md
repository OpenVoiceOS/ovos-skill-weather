# Run the tests
<!-- agent-hint
covers: unit tests, end-to-end tests with the frozen clock and the stubbed forecast, golden utterances, the docs checks
source: test/, .github/workflows/coverage.yml, .github/workflows/ovoscope.yml
generated: no
verify: python docs/verify_phrases.py
see: days.md
-->

Run the unit tests and the end-to-end tests from the repository root:

```bash
uv venv && uv pip install --python .venv/bin/python --prerelease=allow -e '.[test]'
.venv/bin/python -m pytest test/unittests
.venv/bin/python -m pytest test/end2end
```

CI runs `test/unittests` in `coverage.yml` and `test/end2end/` in `ovoscope.yml`.

## End-to-end tests with a frozen clock

A weather answer changes with the clock and with the live forecast. The end-to-end tests that check spoken text remove both:

1. They freeze `now_local` at Wednesday 4 March 2026, 14:35, Europe/Lisbon. The patch goes on `weather_helpers.intent`, `weather_helpers.util` and `weather_helpers.dialog`.
2. They replace `requests.get` in `weather_helpers.openmeteo` with a fixed seven-day report.
3. They send each utterance through the m2v intent pipeline of ovoscope and read the `speak` messages.

`test/end2end/test_spoken_day_name.py` and `test/end2end/test_spoken_writers.py` use this method. Run one file:

```bash
.venv/bin/python -m pytest test/end2end/test_spoken_day_name.py -q
```

`test/end2end/test_intents_en_us.py` checks only the routing. It stubs the geolocation and makes `get_report` raise `ConnectionError`, so the skill speaks the error answer with no network.

## Golden utterances

`test/end2end/golden_utterances_<lang>.jsonl` holds the utterances that must start each intent, and `negative_utterances_<lang>.jsonl` holds the utterances that must not start this skill. `test_golden_utterances.py` reads both.

## Docs checks

`docs/verify_phrases.py` sends each phrase in `usage.md` through a padacioso container of the en-US `.intent` files. It exits 1 when a phrase does not start the intent of its section:

```bash
python docs/verify_phrases.py
```

The `verify` line in the agent hint of `README.md` compares the link table of the README with the files in `docs/`.

---
[← Prev](openmeteo.md) · [Home](index.md)
