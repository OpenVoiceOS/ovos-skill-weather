# Phrases for each intent
<!-- agent-hint
covers: example phrases for each intent of the en-US locale
source: locale/en-US/intents/*.intent
generated: no
verify: python docs/verify_phrases.py
see: days.md, settings.md
-->

Each phrase on this page starts the intent in its section. `docs/verify_phrases.py` sends each quoted phrase through a padacioso container built from `locale/en-US/intents` and fails when a phrase starts no intent.

The `.intent` files list more forms. At runtime the intent pipeline can also route phrasings that are not in the files.

## Current weather and forecast: `weather`

- "What is the weather?"
- "What is the weather in Houston?"
- "What is the forecast tomorrow?"
- "What's tomorrow's forecast?"
- "Show me the weather forecast in Lisbon"

A phrase with a number of days ("the next three days") or "this weekend" gives a forecast for more than one day.

## Temperature: `temperature`

- "What's the temperature?"
- "What's the high temperature tomorrow?"
- "Will it be cold on Tuesday?"
- "Is it hot outside?"
- "How hot or cold is it outside?"

"Hot" asks for the high and "cold" asks for the low.

## A weather condition: `weather_condition`

- "Is it going to snow?"
- "Is it going to snow in Baltimore?"
- "Is it raining?"
- "Will it rain?"
- "Is it foggy?"

The skill answers yes or no for the condition that you name.

## Wind: `is_wind`

- "How windy is it?"
- "Is it windy today?"
- "Will it be windy tonight?"

## Humidity: `humidity`

- "How humid is it?"
- "Is it muggy outside?"
- "What's the humidity level?"

## Next rain: `next_rain`

- "When will it rain next?"
- "When is the next rainfall?"
- "Is rain coming soon?"

## Sunrise: `sunrise`

- "What's the sunrise time?"
- "What time does the sun rise tomorrow?"

## Sunset: `sunset`

- "When is the sunset?"
- "What time does the sun set today?"

The `.blacklist` files of sunrise and sunset stop a sunrise word from starting the sunset intent, and the other way round.

---
[Home](index.md) · [Next →](days.md)
