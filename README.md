# <img src='https://rawgithub.com/FortAwesome/Font-Awesome/master/svgs/solid/sun.svg' card_color='#FEE255' width='50' height='50' style='vertical-align:bottom'/> Weather
<!-- agent-hint
covers: what the skill does, install, a quickstart and the docs link table
source: pyproject.toml
generated: no
verify: diff <(ls docs/*.md | xargs -n1 basename | sort) <(grep -o '(docs/[a-z0-9-]*\.md)' README.md | sed 's%(docs/%%; s%)%%' | sort -u)
see: docs/index.md
-->

An OVOS skill that speaks the current weather, forecasts, temperatures, wind, humidity, rain, sunrise and sunset. The data comes from [Open-Meteo](https://open-meteo.com). The skill needs no API key and no user account.

## Install

```bash
uv pip install --prerelease=allow ovos-skill-weather
```

OVOS loads the skill through the `opm.skill` entry point `ovos-skill-weather.openvoiceos`.

## Quickstart

```text
"when is the sunset" -> the sun will set at <time> today
"when is the sunset" -> the sun set at <time> today   (after the sunset)
```

The skill selects one of three sentences for this answer. The forecast fills `<time>`.

## Documentation

| Page | Contents |
| :--- | :--- |
| [Docs index](docs/index.md) | the reading order |
| [Phrases for each intent](docs/usage.md) | example phrases and the intent that each one starts |
| [How the skill speaks the day](docs/days.md) | today, the weekday, and the letter case |
| [Units and settings](docs/settings.md) | metric or imperial, the units setting, a unit in the phrase |
| [The Open-Meteo source](docs/openmeteo.md) | the request, the cache and the errors |
| [Run the tests](docs/testing.md) | unit tests, end-to-end tests with the frozen clock, the phrase check |

## License

[Apache-2.0](./LICENSE). Credits: OpenVoiceOS, Mycroft AI.
