# How the skill speaks the day
<!-- agent-hint
covers: the day word in daily answers: today, the weekday, the letter case
source: weather_helpers/util.py (get_speakable_day_of_week), weather_helpers/dialog.py
generated: no
verify: python -m pytest test/end2end/test_spoken_day_name.py -q
see: testing.md
-->

A daily answer has a `{day}` slot. With the clock at Wednesday 4 March 2026, the en-US skill fills it like this:

```text
"when is sunrise today"          -> day = today
"when is sunrise tomorrow"       -> day = thursday
"what's the forecast for friday" -> day = friday
```

`test/end2end/test_spoken_day_name.py` checks these rows and the same rows in other locales.

## The rule

`get_speakable_day_of_week` in `weather_helpers/util.py` selects the word:

1. When the forecast day is today, or the day before today, the skill uses the relative word from `ovos_date_parser.nice_date` ("today").
2. For every other day, the skill uses the weekday from `ovos_date_parser.nice_weekday`. A forecast for tomorrow says the weekday, not "tomorrow".
3. The first letter of the weekday follows the letter case of `nice_date` for the language. de-DE gives "Donnerstag". en-US, pt-PT and fr-FR give a lowercase first letter.

The multi-day screen on a GUI shows the first three letters of `nice_weekday`.

## Where the day goes

The dialog files put `{day}` before or after the rest of the sentence. For example, `locale/en-US/dialog/daily/daily_sunrise_local.dialog` has these lines:

```text
sunrise will be at {time} {day}
the sun will rise at {time} {day}
{day} the sun will rise at {time}
```

The skill selects one line at random for each answer.

---
[← Prev](usage.md) · [Home](index.md) · [Next →](settings.md)
