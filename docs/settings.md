# Units and settings
<!-- agent-hint
covers: how the skill selects metric or imperial units, the units setting, a unit in the phrase, the location
source: weather_helpers/config.py, __init__.py (_get_weather_config, _get_intent_data), settingsmeta.json
generated: no
verify: (p=$(grep -o '^| `[a-z]*` | use the' docs/settings.md | cut -d'`' -f2); c=$(python3 -c "import json; print(json.load(open('settingsmeta.json'))['skillMetadata']['sections'][0]['fields'][1]['value'])"); [ "$p" = "$c" ] || { echo "default units: page $p, code $c"; exit 1; }; p=$(grep -o '`[a-z]*` gives a 24-hour' docs/settings.md | cut -d'`' -f2); c=$(grep -o 'time_format == "[a-z]*"' __init__.py | cut -d'"' -f2); [ "$p" = "$c" ] || { echo "clock: page $p, code $c"; exit 1; }; echo OK)
see: openmeteo.md
-->

The skill uses the unit system of the session. A `unit` slot in the intent match can change it for one answer.

## The unit system

`WeatherConfig.scale` reads the `units` setting first. It uses the `system_unit` of the session only when that setting is `default`. `scale` accepts `metric` or `imperial`. Any other value gives `metric`.

| Scale | Temperature | Wind speed | Precipitation |
| :--- | :--- | :--- | :--- |
| `metric` | celsius | meter per second | millimeter |
| `imperial` | fahrenheit | miles per hour | inch |

When the intent match has a `unit` slot, a "fahrenheit" word in the slot selects `imperial` for that answer. A "celsius" word in the slot has no effect, because no locale has a `celsius.voc` file (issue [#342](https://github.com/OpenVoiceOS/ovos-skill-weather/issues/342)). The `fahrenheit.voc` file in `locale/<lang>/vocabulary/unit` holds the words. In en-US, only the `weather.intent` lines that end in `in {unit}` have the slot.

## The units setting

`settingsmeta.json` defines one setting, `units`:

| Value | Effect |
| :--- | :--- |
| `default` | use the `system_unit` of the session |
| `celsius` | replaces the `system_unit` of the session with `celsius` |
| `fahrenheit` | replaces the `system_unit` of the session with `fahrenheit` |

`scale` accepts only `metric` and `imperial`, so the `celsius` and `fahrenheit` values both give `metric`.

## Location

The skill uses the location of the session: the coordinates and the timezone. Name a city in the phrase ("what is the weather in Houston") to get the weather for that city. When the skill cannot find the city, it says a line from `location_not_found.dialog`, for example "I can't find a city named Houston. Please try again".

## Time format

The `time_format` of the session selects the clock for sunrise and sunset times. `full` gives a 24-hour time. Other values give a 12-hour time with a.m. or p.m.

---
[← Prev](days.md) · [Home](index.md) · [Next →](openmeteo.md)
