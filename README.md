[![gitlocalized ](https://gitlocalize.com/repo/9611/whole_project/badge.svg)](https://gitlocalize.com/repo/9662?utm_source=badge) [![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/OpenVoiceOS/ovos-skill-weather)

# <img src='https://rawgithub.com/FortAwesome/Font-Awesome/master/svgs/solid/sun.svg' card_color='#FEE255' width='50' height='50' style='vertical-align:bottom'/> Weather

An [OVOS](https://github.com/OpenVoiceOS) skill that reports weather conditions and forecasts.

## About

The skill reports current conditions, forecasts, and expected precipitation. By default, it uses your
device's configured location. You can also ask about other cities around the world.

Current conditions and forecasts come from [Open-Meteo](https://open-meteo.com).

The skill shows temperature in Celsius or Fahrenheit, based on your configuration or skill settings.
You can also ask for a specific unit that differs from your configuration.

The skill needs no API key and no user account.

## Install

Install the skill with pip:

```bash
pip install ovos-skill-weather
```

An [OVOS](https://github.com/OpenVoiceOS) instance loads it automatically through the
[`opm.skill`](https://github.com/OpenVoiceOS/OVOS-plugin-manager) entry point.

## Usage

### Current conditions

* "What is the weather?"
* "What is the weather in Houston?"

### Daily forecasts

* "What is the forecast tomorrow?"
* "What is the forecast in London tomorrow?"
* "What is the weather going to be like Tuesday?"
* "What is the weather for the next three days?"
* "What is the weather this weekend?"

### Temperatures

* "What's the temperature?"
* "What's the temperature in Paris tomorrow in Celsius?"
* "What's the high temperature tomorrow?"
* "Will it be cold on Tuesday?"

### Specific conditions

* "When will it rain next?"
* "How windy is it?"
* "What's the humidity?"
* "Is it going to snow?"
* "Is it going to snow in Baltimore?"
* "When is the sunset?"

## Related projects

* [OpenVoiceOS/ovos-workshop](https://github.com/OpenVoiceOS/ovos-workshop) — the skill framework this skill builds on.
* [OpenVoiceOS/ovos-date-parser](https://github.com/OpenVoiceOS/ovos-date-parser) — parses the dates and times used in forecast requests.
* [OpenVoiceOS/ovos-number-parser](https://github.com/OpenVoiceOS/ovos-number-parser) — parses the numbers used in temperature and forecast requests.
* [OpenVoiceOS/ovos-utterance-normalizer](https://github.com/OpenVoiceOS/ovos-utterance-normalizer) — normalizes utterances before intent matching.

## Credits

OpenVoiceOS (@OpenVoiceOS)
Mycroft AI (@MycroftAI)

## Category

**Daily**

## Tags

#weather
#forecast
#rain
#humidity
#snow
#temperature
