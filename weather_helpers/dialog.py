# Copyright 2021, Mycroft AI Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Abstraction of dialog building for the weather skill.

There are A LOT of dialog files in this skill.  All the permutations of timeframe,
weather condition and location add up fast.  To help with discoverability, a naming
convention was applied to the dialog files:
    <timeframe>_<weather info>_<qualifier>_<locale>.dialog

    Example:
         daily_temperature_high_local.dialog

    * Timeframe: the date or time applicable to the forecast.  This skill supports
        current, hourly and daily weather.
    * Weather info: a description of what type of weather the dialog refers to.
        Examples include "temperature", "weather" and "sunrise".
    * Qualifier: further qualifies what type of weather is being reported.  For
        example, temperature can be qualified by "high" or "low".
    * Locale: indicates if the dialog is for local weather or weather in a remote
        location.

The skill class will use the "name" and "data" attributes to pass to the TTS process.
"""
from os.path import dirname
# TODO - get rid of relative imports as soon as skills can be properly packaged with arbitrary module structures
from typing import List, Optional

from ovos_date_parser import nice_time
from ovos_utils.time import now_local
from ovos_workshop.resource_files import SkillResources
from ovos_workshop.skills.ovos import join_word_list
from .intent import WeatherIntent
from .util import get_speakable_day_of_week, get_time_period
from .weather import (
    CURRENT,
    DAILY,
    HOURLY,
    Weather,
    WeatherReport
)

# TODO: MISSING DIALOGS
#   - current.clear.alternative.local
#   - current.clouds.alternative.local
#   - daily.snow.alternative.local
#   - all hourly.<condition>.alternative.local/location
#   - all hourly.<condition>.not.expected.local/location
class WeatherDialog:
    """Abstract base class for the weather dialog builders."""

    def __init__(self, intent_data: WeatherIntent):
        self.intent_data = intent_data
        self.name = None
        self.data = None
        self.resources = SkillResources(dirname(dirname(__file__)),
                                        self.lang)

    @property
    def config(self):
        return self.intent_data.config

    @property
    def lang(self):
        return self.config.lang

    def translate(self, dialog, data=None):
        data = data or dict()
        return self.resources.render_dialog(dialog, data=data)

    def _add_location(self):
        """Add location information to the dialog."""
        if self.intent_data.location is None:
            self.name += "_local"
        else:
            self.name += "_location"
            if self.intent_data.config.country == self.intent_data.geolocation["country"]:
                spoken_location = ", ".join(
                    [
                        self.intent_data.geolocation["city"],
                        self.intent_data.geolocation["region"],
                    ]
                )
            else:
                spoken_location = ", ".join(
                    [
                        self.intent_data.geolocation["city"],
                        self.intent_data.geolocation["country"],
                    ]
                )
            self.data.update(location=spoken_location)


class CurrentDialog(WeatherDialog):
    """Weather dialog builder for current weather."""

    def __init__(self, intent_data: WeatherIntent, weather: Weather):
        super().__init__(intent_data)
        self.weather = weather
        self.name = CURRENT

    def build_weather_dialog(self):
        """Build the components necessary to speak current weather."""
        self.name += "_weather"
        self.data = dict(
            condition=self.translate(self.weather.condition.description),
            temperature=self.weather.temperature,
            temperature_unit=self.translate(self.config.temperature_unit),
        )
        self._add_location()

    def build_temperature_dialog(self, temperature_type: str):
        """Build the components necessary to speak the current temperature.

        :param temperature_type: indicates if temperature is current, high or low
        """
        self.name += "_temperature"
        if temperature_type == "high":
            self.name += "_high"
            self.data = dict(temperature=self.weather.temperature_high)
        elif temperature_type == "low":
            self.name += "_low"
            self.data = dict(temperature=self.weather.temperature_low)
        else:
            self.data = dict(temperature=self.weather.temperature)
        self.data.update(
            temperature_unit=self.translate(self.config.temperature_unit)
        )
        self._add_location()

    def build_condition_dialog(self, intent_match: bool):
        """Select the relevant dialog file for condition based reports.

        A condition can for example be "snow" or "rain".

        :param intent_match: true if intent matches a vocabulary for the condition
        """
        self.data = dict(condition=self.translate(
            self.weather.condition.description)
        )
        if intent_match:
            self.name += "_condition_expected"
        else:
            # TODO nothing to format
            self.name += "_condition_not_expected".format(
                self.weather.condition.category.lower()
            )
        self._add_location()

    def build_sunrise_dialog(self):
        """Build the components necessary to speak the sunrise time."""
        if self.intent_data.location is None:
            now = now_local()
        else:
            now = now_local(tz=self.intent_data.geolocation["timezone"])
        if now < self.weather.sunrise:
            self.name += "_sunrise_future"
        else:
            self.name += "_sunrise_past"
        self.data = dict(time=nice_time(self.weather.sunrise, lang=self.lang))
        self._add_location()

    def build_sunset_dialog(self):
        """Build the components necessary to speak the sunset time."""
        if self.intent_data.location is None:
            now = now_local()
        else:
            now = now_local(tz=self.intent_data.geolocation["timezone"])
        if now < self.weather.sunset:
            self.name += "_sunset_future"
        else:
            self.name += "_sunset_past"
        self.data = dict(time=nice_time(self.weather.sunset, lang=self.lang))
        self._add_location()

    def build_wind_dialog(self):
        """Build the components necessary to speak the wind conditions."""
        wind_strength = self.weather.determine_wind_strength(self.config.speed_unit)
        self.data = dict(
            speed=self.weather.wind_speed,
            speed_unit=self.translate(self.config.speed_unit),
            direction=self.translate(self.weather.wind_direction.lower()),
        )
        self.name += "_wind_" + wind_strength
        self._add_location()

    def build_humidity_dialog(self):
        """Build the components necessary to speak the percentage humidity."""
        self.data = dict(
            percent=self.translate("percentage_number",
                                   {"number": self.weather.humidity})
        )
        self.name += "_humidity"
        self._add_location()


class HourlyDialog(WeatherDialog):
    """Weather dialog builder for hourly weather."""

    def __init__(self, intent_data: WeatherIntent, weather: Weather):
        super().__init__(intent_data)
        self.weather = weather
        self.name = HOURLY

    def build_weather_dialog(self):
        """Build the components necessary to speak the forecast for a hour."""
        self.name += "_weather"
        self.data = dict(
            condition=self.translate(self.weather.condition.description),
            time=nice_time(self.weather.date_time, lang=self.lang),
            temperature=self.weather.temperature,
        )
        self._add_location()

    def build_temperature_dialog(self, _=None):
        """Build the components necessary to speak the hourly temperature."""
        self.name += "_temperature"
        self.data = dict(
            temperature=self.weather.temperature,
            time=self.translate(get_time_period(self.weather.date_time)),
            temperature_unit=self.translate(self.config.temperature_unit),
        )
        self._add_location()

    def build_condition_dialog(self, intent_match: bool):
        """Select the relevant dialog file for condition based reports.

        A condition can for example be "snow" or "rain".

        :param intent_match: true if intent matches a vocabulary for the condition
        """
        self.data = dict(
            condition=self.translate(self.weather.condition.description),
            time=nice_time(self.weather.date_time, lang=self.lang),
        )
        if intent_match:
            self.name += "_condition_expected"
        else:
            # TODO nothing to format
            self.name += "_condition_not_expected".format(
                self.weather.condition.category.lower()
            )
        self._add_location()

    def build_wind_dialog(self):
        """Build the components necessary to speak the wind conditions."""
        wind_strength = self.weather.determine_wind_strength(self.config.speed_unit)
        self.data = dict(
            speed=self.weather.wind_speed,
            speed_unit=self.translate(self.config.speed_unit),
            direction=self.translate(self.weather.wind_direction.lower()),
            time=nice_time(self.weather.date_time, lang=self.lang),
        )
        self.name += "_wind_" + wind_strength
        self._add_location()

    def build_next_precipitation_dialog(self):
        """Build the components necessary to speak the next chance of rain."""
        if self.weather is None:
            self.name += "_precipitation_next_none"
            self.data = dict()
        else:
            self.name += "_precipitation_next"
            self.data = dict(
                percent=self.translate("percentage_number",
                                       {"number": self.weather.chance_of_precipitation}),
                precipitation=self.translate(self.weather.condition.description),
                day=get_speakable_day_of_week(self.weather.date_time, self.lang),
                time=self.translate(get_time_period(self.weather.date_time)),
            )
        self._add_location()


class DailyDialog(WeatherDialog):
    """Weather dialog builder for daily weather."""

    def __init__(self, intent_data: WeatherIntent, weather: Weather):
        super().__init__(intent_data)
        self.weather = weather
        self.name = DAILY

    def build_weather_dialog(self):
        """Build the components necessary to speak the forecast for a day."""
        self.name += "_weather"
        self.data = dict(
            condition=self.translate(self.weather.condition.description),
            day=get_speakable_day_of_week(self.weather.date_time, self.lang),
            high_temperature=self.weather.temperature_high,
            low_temperature=self.weather.temperature_low,
        )
        self._add_location()

    def build_temperature_dialog(self, temperature_type: str = "both"):
        """Build the components necessary to speak the daily temperature.

        :param temperature_type: indicates if temperature is day, high or low
        """
        self.name += "_temperature"
        if temperature_type == "high":
            self.name += "_high"
            self.data = dict(temperature=self.weather.temperature_high)
        elif temperature_type == "low":
            self.name += "_low"
            self.data = dict(temperature=self.weather.temperature_low)
        else:
            self.name += "_high_low"
            self.data = dict(high_temperature=self.weather.temperature_high,
                             low_temperature=self.weather.temperature_low)
        self.data.update(
            day=get_speakable_day_of_week(self.weather.date_time, self.lang),
            temperature_unit=self.translate(self.config.temperature_unit),
        )
        self._add_location()

    def build_condition_dialog(self, intent_match: bool):
        """Select the relevant dialog file for condition based reports.

        A condition can for example be "snow" or "rain".

        :param intent_match: true if intent matches a vocabulary for the condition
        """
        self.data = dict(
            condition=self.translate(self.weather.condition.description),
            day=get_speakable_day_of_week(self.weather.date_time, self.lang),
        )
        if intent_match:
            self.name += "_condition_expected"
        else:
            # TODO nothing to format
            self.name += "_condition_not_expected".format(
                self.weather.condition.category.lower()
            )
        self._add_location()

    def build_sunrise_dialog(self):
        """Build the components necessary to speak the sunrise time."""
        self.name += "_sunrise"
        self.data = dict(time=nice_time(self.weather.sunrise, lang=self.lang))
        self.data.update(day=get_speakable_day_of_week(self.weather.date_time, self.lang))
        self._add_location()

    def build_sunset_dialog(self):
        """Build the components necessary to speak the sunset time."""
        self.name += "_sunset"
        self.data = dict(time=nice_time(self.weather.sunset, lang=self.lang))
        self.data.update(day=get_speakable_day_of_week(self.weather.date_time, self.lang))
        self._add_location()

    def build_wind_dialog(self):
        """Build the components necessary to speak the wind conditions."""
        wind_strength = self.weather.determine_wind_strength(self.config.speed_unit)
        self.data = dict(
            day=get_speakable_day_of_week(self.weather.date_time, self.lang),
            speed=self.weather.wind_speed_max,
            speed_unit=self.translate(self.config.speed_unit),
            direction=self.translate(self.weather.wind_direction.lower()),
        )
        self.name += "_wind_" + wind_strength
        self._add_location()

    def build_humidity_dialog(self):
        """Build the components necessary to speak the percentage humidity."""
        self.data = dict(
            percent=self.translate("percentage_number",
                                   {"number": self.weather.humidity}),
            day=get_speakable_day_of_week(self.weather.date_time, self.lang)
        )
        self.name += "_humidity"
        self._add_location()

    def build_next_precipitation_dialog(self):
        """Build the components necessary to speak the next chance of rain."""
        if self.weather is None:
            self.name += "_precipitation_next_none"
            self.data = dict()
        else:
            self.name += "_precipitation_next"
            self.data = dict(
                percent=self.translate("percentage_number",
                                       {"number": self.weather.chance_of_precipitation}),
                precipitation=self.translate(self.weather.condition.description),
                day=get_speakable_day_of_week(self.weather.date_time, self.lang),
            )
        self._add_location()


class WeeklyDialog(WeatherDialog):
    """Weather dialog builder for weekly weather."""

    def __init__(
            self,
            intent_data: WeatherIntent,
            forecast: List[Weather],
    ):
        super().__init__(intent_data)
        self.forecast = forecast
        self.name = "weekly"

    def build_temperature_dialog(self):
        """Build the components necessary to temperature ranges for a week."""
        low_temperatures = [daily.temperature_low for daily in self.forecast]
        high_temperatures = [daily.temperature_high for daily in self.forecast]
        self.name += "_temperature"
        self.data = dict(
            low_min=min(low_temperatures),
            low_max=max(low_temperatures),
            high_min=min(high_temperatures),
            high_max=max(high_temperatures),
        )

    def build_condition_dialog(self, condition: str):
        """Build the components necessary to speak the days of week for a condition."""
        self.name += "_condition"
        self.data = dict(condition=self.translate(condition))
        days_with_condition = []
        for daily in self.forecast:
            if daily.condition.category == condition:
                day = get_speakable_day_of_week(daily.date_time, lang=self.lang)
                days_with_condition.append(day)
        self.data.update(days=join_word_list(days_with_condition, connector="and", sep=",", lang=self.lang))


def get_dialog_for_timeframe(intent_data: WeatherIntent,
                             weather: WeatherReport):
    """Use the intent data to determine which dialog builder to use.

    :param timeframe: current, hourly, daily
    :param dialog_args: Arguments to pass to the dialog builder
    :return: The correct dialog builder for the timeframe
    """
    if intent_data.timeframe == DAILY:
        dialog = DailyDialog(intent_data, weather)
    elif intent_data.timeframe == HOURLY:
        dialog = HourlyDialog(intent_data, weather)
    else:
        dialog = CurrentDialog(intent_data, weather)

    return dialog
