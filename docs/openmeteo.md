# The Open-Meteo source
<!-- agent-hint
covers: the Open-Meteo request, the cache, the forecast range and the error answers
source: weather_helpers/openmeteo.py, __init__.py (_get_weather, _handle_api_error)
generated: no
verify: (p=$(grep -o 'keeps each result for [0-9]* minutes' docs/openmeteo.md | grep -o '[0-9]*'); c=$(( $(grep -o 'timed_lru_cache(seconds=[0-9 *]*' weather_helpers/openmeteo.py | cut -d= -f2) / 60 )); [ "$p" = "$c" ] || { echo "cache: page $p min, code $c min"; exit 1; }; p=$(grep -o 'https://api.open-meteo.com/v1/forecast' docs/openmeteo.md | head -1); grep -q "\"$p\"" weather_helpers/openmeteo.py || { echo "url: $p not in code"; exit 1; }; echo OK)
see: settings.md
-->

The skill gets each forecast from `https://api.open-meteo.com/v1/forecast`. Open-Meteo needs no API key and no account.

## The request

`get_report` in `weather_helpers/openmeteo.py` sends one GET request with these parameters:

| Parameter | Value |
| :--- | :--- |
| `latitude`, `longitude` | the coordinates of the location |
| `timezone` | the timezone code of the location |
| `temperature_unit` | `celsius` or `fahrenheit` |
| `windspeed_unit` | `ms` or `mph` |
| `precipitation_unit` | `mm` or `inch` |
| `current_weather` | `true` |
| `hourly`, `daily` | the lists of variables in `get_report` |

`settings.md` tells how the skill selects the units.

Open-Meteo sends hourly data from 00:00 local time. The skill removes the hours before the current hour. It also calculates a daily humidity as the mean of the 24 hourly values of each day.

## The cache

`get_report` keeps each result for 15 minutes (`timed_lru_cache`). A second request with the same configuration in that time does not call Open-Meteo.

## Forecast range

When an hourly request asks for more hours than the report holds, the skill says a line from `forty_eight_hours_available.dialog`. When a multi-day request asks for more days than the report holds, the skill says a line from `seven_days_available.dialog` and then gives the seven-day forecast.

## Errors

| Problem | Answer |
| :--- | :--- |
| any HTTP error status, 401 included | a line from `cant_get_forecast.dialog` |
| any other exception | a line from `cant_get_forecast.dialog` |
| the city is not found | a line from `location_not_found.dialog` |

`get_report` does not call `raise_for_status`. An error response goes to the report parser, which fails, so the skill never gets an `HTTPError`. The `mycroft.not.paired` branch in `_handle_api_error` does not run.

The skill needs the network. Its runtime requirements tell OVOS to load it only when the internet is available.

---
[← Prev](settings.md) · [Home](index.md) · [Next →](testing.md)
