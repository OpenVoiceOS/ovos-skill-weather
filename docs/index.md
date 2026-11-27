# ovos-skill-weather documentation
<!-- agent-hint
covers: the reading order of the docs and one line for each page
source: docs/
generated: no
verify: diff <(ls docs/*.md | grep -v index.md | xargs -n1 basename | sort) <(grep -o '([a-z0-9-]*\.md)' docs/index.md | tr -d '()' | sort -u)
see: ../README.md
-->

The skill speaks the current weather and the forecast for your location or for a city that you name.

## Quickstart

```bash
uv pip install --prerelease=allow ovos-skill-weather
```

Say "what's the temperature". The skill answers with this fixed part. The forecast fills the slots:

```text
It's currently <temperature> degrees <unit>.
```

## Pages

| Page | What you get there |
| :--- | :--- |
| [Phrases for each intent](usage.md) | the example phrases for each of the eight intents |
| [How the skill speaks the day](days.md) | when the skill says "today" and when it says the weekday |
| [Units and settings](settings.md) | how the skill selects metric or imperial units |
| [The Open-Meteo source](openmeteo.md) | what the skill asks Open-Meteo for, and what it says on an error |
| [Run the tests](testing.md) | the unit tests, the end-to-end tests with the frozen clock, and the phrase check |
