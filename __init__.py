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
"""Mycroft skill for communicating weather information

This skill uses the Open Weather Map One Call API to retrieve weather data
from around the globe (https://openweathermap.org/api/one-call-api).  It
proxies its calls to the API through Mycroft's officially supported API,
Selene.  The Selene API is also used to get geographical information about the
city name provided in the request.
"""
from datetime import datetime
from time import sleep
from typing import List

from ovos_number_parser import extract_number
from ovos_date_parser import (
    nice_time,
    nice_weekday,
    get_date_strings
)
from ovos_bus_client.message import Message
from ovos_bus_client.session import SessionManager
from ovos_utils import classproperty
from ovos_workshop.intents import IntentBuilder
from ovos_utils.log import LOG
from ovos_utils.process_utils import RuntimeRequirements
from ovos_workshop.decorators import intent_handler, skill_api_method
from ovos_workshop.skills import OVOSSkill
from requests import HTTPError

from .weather_helpers import (
    CURRENT,
    DAILY,
    HOURLY,
    WeatherDialog,
    CurrentDialog,
    DailyDialog,
    HourlyDialog,
    Weather,
    get_dialog_for_timeframe,
    LocationNotFoundError,
    WeatherConfig,
    WeatherIntent,
    WeatherReport,
    WeeklyDialog,
    get_report
)

TWELVE_HOUR = "half"


class WeatherSkill(OVOSSkill):
    """Main skill code for the weather skill."""

    @classproperty
    def runtime_requirements(self):
        """this skill needs internet"""
        return RuntimeRequirements(internet_before_load=True,
                                   network_before_load=True,
                                   gui_before_load=False,
                                   requires_internet=True,
                                   requires_network=True,
                                   requires_gui=False,
                                   no_internet_fallback=False,
                                   no_network_fallback=False,
                                   no_gui_fallback=True)

    def initialize(self):
        # TODO - skill api
        self.bus.on("skill-ovos-weather.openvoiceos.weather.request",
                    self.get_current_weather_homescreen)

    @property
    def use_24h(self) -> bool:
        return self.time_format == "full"

    @intent_handler("current_weather.intent")
    def handle_current_weather(self, message):
        """
        Handle current weather requests such as:

            what's it like outside?
            "What's the weather like?"

        Args:
            message: Message Bus event information from the intent parser
        """
        intent = self._get_intent_data(message)
        self._report_current_weather(intent)

    @intent_handler("hourly_forecast.intent")
    def handle_hourly_weather(self, message):
        """
        Handle weather requests for a specific time such as:

            What's the forecast for friday 9 pm?

        Args:
            message: Message Bus event information from the intent parser
        """
        intent = self._get_intent_data(message)
        self._report_hourly_weather(intent)

    @intent_handler("daily_forecast.intent")
    def handle_daily_weather(self, message):
        """
        Handle weather requests for a specific day such as:

            How's the weather tomorrow
            "what's tomorrow's forecast in Seattle?"

        Args:
            message: Message Bus event information from the intent parser
        """
        intent = self._get_intent_data(message)
        self._report_one_day_forecast(intent)

    @intent_handler(
        IntentBuilder("weather")
        .optionally("query")
        .one_of("weather", "forecast")
        .optionally("relative-time")
        .optionally("relative-day")
        .optionally("today")
        .optionally("location")
        .optionally("unit"))
    def handle_weather(self, message: Message):
        """
        Handle weather requests of various timeframes.
        The intents gets routed accordingly

        Examples:
            "What's the weather like?" (current)
            "How's the weather tomorrow?" (daily)
            "What's the forecast for friday 9 pm?" (hourly)
            "what's tomorrow's forecast in Seattle?"

        Args:
            message: Message Bus event information from the intent parser
        """
        intent = self._get_intent_data(message)
        if intent.timeframe == DAILY:
            self._report_one_day_forecast(intent)
        elif intent.timeframe == HOURLY:
            self._report_hourly_weather(intent)
        else:
            self._report_current_weather(intent)


    @intent_handler("N_days_forecast.intent")
    def handle_number_days_forecast(self, message: Message):
        """Handle multiple day forecast without specified location.

        Examples:
            "What is the 3 day forecast?"

        Args:
            message: Message Bus event information from the intent parser
        """
        utt = message.data["utterance"]
        days = None
        if self.voc_match(utt, "week"):
            days = 7
        elif self.voc_match(utt, "couple"):
            days = 2
        elif self.voc_match(utt, "few"):
            days = 3
        else:
            try:
                days = int(extract_number(message.data["utterance"], lang=self.lang))
            except:
                pass

        if not days:
            self._report_week_summary(message)
        else:
            self._report_multi_day_forecast(message, days)

    @intent_handler("weekend_forecast.intent")
    def handle_weekend_forecast(self, message: Message):
        """Handle requests for the weekend forecast.

        Args:
            message: Message Bus event information from the intent parser
        """
        self._report_weekend_forecast(message)


    @intent_handler("current_temperature.intent")
    def handle_current_temperature(self, message: Message):
        """Handle requests for current temperature.

        Examples:
            "What is the temperature in Celsius?"
            "What is the temperature in Baltimore now?"

        Args:
            message: Message Bus event information from the intent parser
        """
        self._report_temperature(message, temperature_type="current")

    @intent_handler("hourly_temperature.intent")
    def handle_hourly_temperature(self, message: Message):
        """Handle requests for current temperature at a relative time.

        Examples:
            "What is the temperature tonight?"
            "What is the temperature tomorrow morning?"

        Args:
            message: Message Bus event information from the intent parser
        """
        self._report_temperature(message)

    @intent_handler("high_temperature.intent")
    def handle_high_temperature(self, message: Message):
        """Handle a request for the high temperature.

        Examples:
            "What is the high temperature tomorrow?"
            "What is the high temperature in London on Tuesday?"

        Args:
            message: Message Bus event information from the intent parser
        """
        self._report_temperature(message, temperature_type="high")

    @intent_handler("low_temperature.intent")
    def handle_low_temperature(self, message: Message):
        """Handle a request for the high temperature.

        Examples:
            "What is the high temperature tomorrow?"
            "What is the high temperature in London on Tuesday?"

        Args:
            message: Message Bus event information from the intent parser
        """
        self._report_temperature(message, temperature_type="low")

    @intent_handler(
        IntentBuilder("is_hot_cold")
        .one_of("confirm-query-current", "confirm-query")
        .one_of("hot", "cold")
        .optionally("query")
        .optionally("location")
        .optionally("relative-day")
        .optionally("today")
    )
    def handle_is_it_hot_or_cold(self, message: Message):
        """Handler for temperature requests such as: is it going to be hot today?

        Args:
            message: Message Bus event information from the intent parser
        """
        utterance = message.data["utterance"]
        temperature_type = "high" if self.voc_match(utterance, "hot") else "low"
        self._report_temperature(message, temperature_type)

    @intent_handler("is_wind.intent")
    def handle_is_it_windy(self, message: Message):
        """Handler for weather requests such as: is it windy today?

        Args:
            message: Message Bus event information from the intent parser
        """
        self._report_wind(message)

    @intent_handler("is_snow.intent")
    def handle_is_it_snowing(self, message: Message):
        """Handler for weather requests such as: is it snowing today?

        Args:
            message: Message Bus event information from the intent parser
        """
        self._report_weather_condition(message, "snow")

    @intent_handler("is_clear.intent")
    def handle_is_it_clear(self, message: Message):
        """Handler for weather requests such as: is the sky clear today?

        Args:
            message: Message Bus event information from the intent parser
        """
        self._report_weather_condition(message, condition="clear")

    @intent_handler(
        IntentBuilder("is_cloudy")
        .require("confirm-query")
        .require("clouds")
        .optionally("location")
        .optionally("relative-time")
    )
    def handle_is_it_cloudy(self, message: Message):
        """Handler for weather requests such as: is it cloudy today?

        Args:
            message: Message Bus event information from the intent parser
        """
        self._report_weather_condition(message, "clouds")

    @intent_handler("is_fog.intent")
    def handle_is_it_foggy(self, message: Message):
        """Handler for weather requests such as: is it foggy today?

        Args:
            message: Message Bus event information from the intent parser
        """
        self._report_weather_condition(message, "fog")

    @intent_handler("is_rain.intent")
    def handle_is_it_raining(self, message: Message):
        """Handler for weather requests such as: is it raining today?

        Args:
            message: Message Bus event information from the intent parser
        """
        self._report_weather_condition(message, "rain")


    @intent_handler("is_stormy.intent")
    def handle_is_it_storming(self, message: Message):
        """Handler for weather requests such as:  is it storming today?

        Args:
            message: Message Bus event information from the intent parser
        """
        self._report_weather_condition(message, "thunderstorm")

    @intent_handler("next_rain.intent")
    def handle_next_precipitation(self, message: Message):
        """Handler for weather requests such as: when will it rain next?

        Args:
            message: Message Bus event information from the intent parser
        """
        intent_data = self._get_intent_data(message)
        weather = self._get_weather(intent_data)
        if weather is not None:
            forecast, timeframe = weather.get_next_precipitation(intent_data)
            intent_data.timeframe = timeframe
            dialog = get_dialog_for_timeframe(intent_data, forecast)
            dialog.build_next_precipitation_dialog()
            self._speak_weather(dialog)

    @intent_handler("humidity.intent")
    def handle_humidity(self, message: Message):
        """Handler for weather requests such as: how humid is it?

        Args:
            message: Message Bus event information from the intent parser
        """
        intent_data = self._get_intent_data(message)
        weather = self._get_weather(intent_data)
        if weather is not None:
            intent_weather = weather.get_weather_for_intent(intent_data)
            dialog = get_dialog_for_timeframe(intent_data, intent_weather)
            dialog.build_humidity_dialog()
            self._speak_weather(dialog)

    @intent_handler("sunrise.intent")
    def handle_sunrise(self, message: Message):
        """Handler for weather requests such as: when is the sunrise?

        Args:
            message: Message Bus event information from the intent parser
        """
        intent_data = self._get_intent_data(message)
        intent_data.timeframe = DAILY
        weather = self._get_weather(intent_data)
        if weather is not None:
            intent_weather = weather.get_weather_for_intent(intent_data)
            dialog = get_dialog_for_timeframe(intent_data, intent_weather)
            dialog.build_sunrise_dialog()
            self._display_sunrise_sunset(intent_weather, intent_data.display_location)
            self._speak_weather(dialog)

    @intent_handler("sunset.intent")
    def handle_sunset(self, message: Message):
        """Handler for weather requests such as: when is the sunset?

        Args:
            message: Message Bus event information from the intent parser
        """
        intent_data = self._get_intent_data(message)
        intent_data.timeframe = DAILY
        weather = self._get_weather(intent_data)
        if weather is not None:
            intent_weather = weather.get_weather_for_intent(intent_data)
            dialog = get_dialog_for_timeframe(intent_data, intent_weather)
            dialog.build_sunset_dialog()
            self._display_sunrise_sunset(intent_weather, intent_data.display_location)
            self._speak_weather(dialog)

    def _display_sunrise_sunset(self, forecast: Weather, weather_location: str):
        """Display the sunrise and sunset.

        Args:
            forecast: daily forecasts to display
            weather_location: the geographical location of the weather
        """
        self.gui.clear()
        self.gui["currentTimezone"] = self._format_dt(forecast.date_time)
        self.gui["weatherLocation"] = weather_location
        self.gui["sunrise"] = self._format_time(forecast.sunrise)
        self.gui["sunset"] = self._format_time(forecast.sunset)
        self.gui.show_page("SunriseSunset")

    def _report_current_weather(self, intent_data: WeatherIntent):
        """Handles all requests for current weather conditions.

        Args:
            message: Message Bus event information from the intent parser
        """
        weather = self._get_weather(intent_data)
        if weather is not None:
            self._display_current_conditions(weather, intent_data.display_location)
            dialog = CurrentDialog(intent_data,  weather.current)
            dialog.build_weather_dialog()
            self._speak_weather(dialog)
            dialog = CurrentDialog(intent_data, weather.current)
            dialog.build_humidity_dialog()
            self._speak_weather(dialog)
            if self.gui.connected:
                sleep(7)
                self._display_hourly_forecast(weather.hourly, intent_data.display_location)
                sleep(7)
                four_day_forecast = weather.daily[1:5]
                self._display_multi_day_forecast(four_day_forecast, intent_data)
            else:
                sleep(5)
            # reset mk1 faceplate
            self.enclosure.eyes_blink("b")
            self.enclosure.mouth_reset()
            self.enclosure.activate_mouth_events()

    def _display_current_conditions(self, weather: WeatherReport, weather_location: str):
        """Display current weather conditions on a screen.

        This is the first screen that shows.  Others will follow.

        Args:
            weather: current weather conditions from Open Weather Maps
            weather_location: the geographical location of the reported weather
        """
        # display in GUI
        self.gui["weatherCode"] = weather.current.condition.animated_code
        self.gui["currentTimezone"] = self._format_dt(weather.current.date_time.now(),
                                                      incl_time=True)
        self.gui["currentTemperature"] = weather.current.temperature
        self.gui["weatherCondition"] = weather.current.condition.image
        self.gui["weatherLocation"] = weather_location
        self.gui["highTemperature"] = weather.daily[0].temperature_high
        self.gui["lowTemperature"] = weather.daily[0].temperature_low
        self.gui["chanceOfPrecipitation"] = weather.current.chance_of_precipitation
        self.gui["windSpeed"] = weather.current.wind_speed
        self.gui["humidity"] = weather.current.humidity
        self.gui.show_page("CurrentWeather", override_idle=20)
        
        # display in mk1
        self.enclosure.deactivate_mouth_events()
        self.enclosure.weather_display(
            weather.current.condition.code, weather.current.temperature
        )

    def _report_hourly_weather(self, intent_data: WeatherIntent):
        """Handles requests for a one hour forecast.

        Args:
            message: Message Bus event information from the intent parser
        """
        weather = self._get_weather(intent_data)
        if weather is not None:
            try:
                forecast = weather.get_forecast_for_multiple_hours(intent_data)
            except IndexError:
                self.speak_dialog("forty-eight-hours-available")
            else:
                dialog = HourlyDialog(intent_data, forecast[0])
                dialog.build_weather_dialog()
                self._display_hourly_forecast(forecast, intent_data.display_location)
                self._speak_weather(dialog)

    def _display_hourly_forecast(self, weather: List[Weather], weather_location: str):
        """Display hourly forecast on a device that supports the GUI.

        On the Mark II this screen is the final for current weather.  It can
        also be shown when the hourly forecast is requested.

        :param weather: hourly weather conditions from Open Weather Maps
        """
        hourly_forecast = []
        for hour_count, hourly in enumerate(weather):
            if not hour_count:
                continue
            if hour_count > 4:
                break
            if self.time_format == TWELVE_HOUR:
                # The datetime builtin returns hour in two character format.  Convert
                # to a integer and back again to remove the leading zero when present.
                hour = int(hourly.date_time.strftime("%I"))
                am_pm = hourly.date_time.strftime(" %p")
                formatted_time = str(hour) + am_pm
            else:
                formatted_time = hourly.date_time.strftime("%H:00")
            hourly_forecast.append(
                dict(
                    time=formatted_time,
                    precipitation=hourly.chance_of_precipitation,
                    temperature=hourly.temperature,
                    weatherCondition=hourly.condition.animated_code,
                )
            )
        self.gui["currentTimezone"] = self._format_dt(weather[0].date_time)
        self.gui["weatherCode"] = weather[0].condition.animated_code
        self.gui["weatherLocation"] = weather_location
        self.gui["hourlyForecast"] = dict(hours=hourly_forecast)
        self.gui.show_page("HourlyForecast")

    def _report_one_day_forecast(self, intent_data: WeatherIntent):
        """Handles all requests for a single day forecast.

        Args:
            message: Message Bus event information from the intent parser
        """
        weather = self._get_weather(intent_data)
        if weather is not None:
            forecast = weather.get_forecast_for_date(intent_data)
            dialogs = self._build_forecast_dialogs([forecast], intent_data)
            if self.gui.connected:
                self._display_one_day(forecast, intent_data)
            for dialog in dialogs:
                self._speak_weather(dialog, wait=True)

    def _display_one_day(self, forecast: Weather, intent_data: WeatherIntent):
        """Display the forecast for a single day

        :param forecast: daily forecasts to display
        """
        # display in the GUI
        self.gui.clear()
        self.gui["weatherLocation"] = intent_data.display_location
        self.gui["weatherCode"] = forecast.condition.animated_code
        self.gui["weatherDate"] = self._format_dt(forecast.date_time)
        self.gui["highTemperature"] = forecast.temperature_high
        self.gui["lowTemperature"] = forecast.temperature_low
        self.gui["chanceOfPrecipitation"] = str(forecast.chance_of_precipitation)
        self.gui["windSpeed"] = forecast.wind_speed_max
        self.gui["humidity"] = forecast.humidity
        self.gui.show_page("SingleDay")
        # and display in the mk1 faceplate
        self.enclosure.deactivate_mouth_events()
        self.enclosure.weather_display(
            forecast.condition.code,
            (forecast.temperature_high + forecast.temperature_low) / 2
        )
        sleep(5)
        self.enclosure.eyes_blink("b")
        self.enclosure.mouth_reset()
        self.enclosure.activate_mouth_events()

    def _report_multi_day_forecast(self, message: Message, days: int):
        """Handles all requests for multiple day forecasts.

        :param message: Message Bus event information from the intent parser
        """
        weather_config = self._get_weather_config(message)
        intent_data = WeatherIntent(message, weather_config)
        weather = self._get_weather(intent_data)
        if weather is not None:
            try:
                forecast = weather.get_forecast_for_multiple_days(days)
            except IndexError:
                self.speak_dialog("seven-days-available")
                forecast = weather.get_forecast_for_multiple_days(7)
            dialogs = self._build_forecast_dialogs(forecast, intent_data)
            self._display_multi_day_forecast(forecast, intent_data)
            for dialog in dialogs:
                self._speak_weather(dialog, wait=True)

    def _report_weekend_forecast(self, message: Message):
        """Handles requests for a weekend forecast.

        Args:
            message: Message Bus event information from the intent parser
        """
        intent_data = self._get_intent_data(message)
        weather = self._get_weather(intent_data)
        if weather is not None:
            forecast = weather.get_weekend_forecast()
            dialogs = self._build_forecast_dialogs(forecast, intent_data)
            self._display_multi_day_forecast(forecast, intent_data)
            for dialog in dialogs:
                self._speak_weather(dialog, wait=True)

    def _build_forecast_dialogs(self, forecast: List[Weather], intent_data: WeatherIntent) -> List[DailyDialog]:
        """
        Build the dialogs for each of the forecast days being reported to the user.

        :param forecast: daily forecasts to report
        :param intent_data: information about the intent that was triggered
        :return: one DailyDialog instance for each day being reported.
        """
        dialogs = list()
        for forecast_day in forecast:
            dialog = DailyDialog(intent_data, forecast_day)
            dialog.build_weather_dialog()
            dialogs.append(dialog)

        return dialogs

    def _report_week_summary(self, message: Message):
        """Summarize the week's weather rather than giving daily details.

        When the user requests the weather for the week, rather than give a daily
        forecast for seven days, summarize the weather conditions for the week.

        Args:
            message: Message Bus event information from the intent parser
        """
        weather_config = self._get_weather_config(message)
        intent_data = WeatherIntent(message, weather_config)
        weather = self._get_weather(intent_data)
        if weather is not None:
            forecast = weather.get_forecast_for_multiple_days(7)
            dialogs = self._build_weekly_condition_dialogs(forecast, intent_data)
            dialogs.append(self._build_weekly_temperature_dialog(forecast, intent_data))
            self._display_multi_day_forecast(forecast, intent_data)
            for dialog in dialogs:
                self._speak_weather(dialog)

    def _build_weekly_condition_dialogs(self, forecast: List[Weather], intent_data: WeatherIntent) -> List[WeeklyDialog]:
        """Build the dialog communicating a weather condition on days it is forecasted.

        Args:
            forecast: seven day daily forecast
            intent_data: Parsed intent data

        Returns:
            List of dialogs for each condition expected in the coming week.
        """
        dialogs = list()
        conditions = set([daily.condition.category for daily in forecast])
        for condition in conditions:
            dialog = WeeklyDialog(intent_data, forecast)
            dialog.build_condition_dialog(condition=condition)
            dialogs.append(dialog)

        return dialogs

    def _build_weekly_temperature_dialog(self, forecast: List[Weather], intent_data: WeatherIntent) -> WeeklyDialog:
        """Build the dialog communicating the forecasted range of temperatures.

        Args:
            forecast: seven day daily forecast
            intent_data: Parsed intent data

        Returns:
            Dialog for the temperature ranges over the coming week.
        """
        dialog = WeeklyDialog(intent_data, forecast)
        dialog.build_temperature_dialog()

        return dialog

    def _display_multi_day_forecast(self, forecast: List[Weather], intent_data: WeatherIntent):
        """Display daily forecast data on devices that support the GUI.

        Args:
            forecast: daily forecasts to display
            intent_data: Parsed intent data
        """
        self._display_multi_day_scalable(forecast)

    def _display_multi_day_scalable(self, forecast: List[Weather]):
        """Display daily forecast data on GUI devices other than the Mark II.

        The generic layout supports displaying two days of a forecast at a time.

        Args:
            forecast: daily forecasts to display
        """
        display_data = []
        for day_number, day in enumerate(forecast):
            if day_number == 4:
                break
            display_data.append(
                dict(
                    weatherCondition=day.condition.animated_code,
                    highTemperature=day.temperature_high,
                    lowTemperature=day.temperature_low,
                    date=nice_weekday(day.date_time, lang=self.lang)[:3],
                )
            )
        self.gui["forecast"] = dict(all=display_data)
        self.gui.show_page("DailyForecast")

    def _report_temperature(self, message: Message, temperature_type: str = None):
        """Handles all requests for a temperature.

        Args:
            message: Message Bus event information from the intent parser
            temperature_type: current, high or low temperature
        """
        intent_data = self._get_intent_data(message)
        if temperature_type in ("high","low",):
            intent_data.timeframe = "daily"
        weather = self._get_weather(intent_data)
        if weather is not None:
            intent_weather = weather.get_weather_for_intent(intent_data)
            dialog = get_dialog_for_timeframe(intent_data, intent_weather)
            dialog.build_temperature_dialog(temperature_type)
            self._speak_weather(dialog)

    def _report_weather_condition(self, message: Message, condition: str):
        """Handles all requests for a specific weather condition.

        Args:
            message: Message Bus event information from the intent parser
            condition: the weather condition specified by the user
        """
        intent_data = self._get_intent_data(message)
        weather = self._get_weather(intent_data)
        if weather is not None:
            intent_weather = weather.get_weather_for_intent(intent_data)
            dialog = self._build_condition_dialog(
                intent_weather, intent_data, condition
            )
            self._speak_weather(dialog)

    def _build_condition_dialog(self, weather, intent_data: WeatherIntent, condition: str):
        """Builds a dialog for the requested weather condition.

        Args:
            weather: Current, hourly or daily weather forecast
            intent_data: Parsed intent data
            condition: weather condition requested by the user
        """
        dialog = get_dialog_for_timeframe(intent_data, weather)
        intent_match = self.voc_match(weather.condition.category.lower(), condition)
        dialog.build_condition_dialog(intent_match)
        return dialog

    def _report_wind(self, message: Message):
        """Handles all requests for a wind conditions.

        Args:
            message: Message Bus event information from the intent parser
        """
        intent_data = self._get_intent_data(message)
        weather = self._get_weather(intent_data)
        if weather is not None:
            intent_weather = weather.get_weather_for_intent(intent_data)
            dialog = get_dialog_for_timeframe(intent_data, intent_weather)
            dialog.build_wind_dialog()
            self._speak_weather(dialog)

    def _get_intent_data(self, message: Message) -> WeatherIntent:
        """Parse the intent data from the message into data used in the skill.

        Args:
            message: Message Bus event information from the intent parser

        Returns:
            parsed information about the intent
        """
        intent_data = None
        try:
            weather_config = self._get_weather_config(message)
            intent_data = WeatherIntent(message, weather_config)
        except ValueError:
            self.speak_dialog("cant-get-forecast")
        else:
            unit = message.data.get("unit")
            _dt = intent_data.intent_datetime
            
            if _dt != intent_data.location_datetime:  # ie current
                if _dt.hour == 0 and _dt.minute == 0:
                    intent_data.timeframe = DAILY
                else:
                    intent_data.timeframe = HOURLY
            elif self.voc_match(intent_data.utterance, "later"):
                intent_data.timeframe = HOURLY
                    
            if unit and self.voc_match(unit, "fahrenheit"):
                intent_data.config.settings["units"] = "imperial"
            elif unit and self.voc_match(unit, "celsius"):
                intent_data.config.settings["units"] = "metric"

        return intent_data

    def _get_weather_config(self, message=None):
        sess = SessionManager.get(message)
        cfg = {"lang": sess.lang,
               "system_unit": sess.system_unit,
               "location": sess.location_preferences,
               "date_format": sess.date_format,
               "time_format": sess.time_format}
        if self.settings.get("units") and self.settings.get("units") != "default":
            LOG.debug(f"overriding system_unit from settings.json : {sess.system_unit} -> {self.settings['units']}")
            cfg["system_unit"] = self.settings["units"]

        if message and "lat_lon" in message.data:
            latitude, longitude = message.data["lat_lon"]
            LOG.debug(f"weather lat, lon: {latitude} , {longitude}")
            cfg["location"]["coordinate"]["latitude"] = latitude
            cfg["location"]["coordinate"]["longitude"] = longitude
        return WeatherConfig(cfg)

    def _get_weather(self, intent_data: WeatherIntent) -> WeatherReport:
        """Call the Open Weather Map One Call API to get weather information

        Args:
            intent_data: Parsed intent data

        Returns:
            An object representing the data returned by the API
        """
        weather = None
        if intent_data is not None:
            try:
                weather = get_report(intent_data.config)
            except HTTPError as api_error:
                LOG.exception("Weather API failure")
                self._handle_api_error(api_error)
            except LocationNotFoundError:
                LOG.exception("City not found.")
                self.speak_dialog(
                    "location-not-found", data=dict(location=intent_data.location)
                )
            except Exception:
                LOG.exception("Unexpected error retrieving weather")
                self.speak_dialog("cant-get-forecast")

        return weather

    def _handle_api_error(self, exception: HTTPError):
        """Communicate an error condition to the user.

        Args:
            exception: the HTTPError returned by the API call
        """
        if exception.response.status_code == 401:
            self.bus.emit(Message("mycroft.not.paired"))
        else:
            self.speak_dialog("cant-get-forecast")

    def _speak_weather(self, dialog: WeatherDialog, wait: bool = False):
        """Instruct device to speak the contents of the specified dialog.

        :param dialog: the dialog that will be spoken
        """
        LOG.info(f"Speaking dialog: {dialog.name}")
        self.speak_dialog(dialog.name, dialog.data, wait=wait)

    def _format_dt(self, dt: datetime, incl_time: bool = False) -> str:
        """Convert a datetime object to a localized string.

        Args:
            dt: datetime object
            incl_time: whether to include the time in the output

        Returns:
            A localized string representing the datetime
        """
        dt_strings = get_date_strings(dt, lang=self.lang)
        wd_abbr = dt_strings["weekday_string"][:3].capitalize()
        month = dt_strings["month_string"].capitalize()
        day = dt_strings["day_string"]
        time = dt_strings["time_string"]

        if self.date_format == "MDY":
            dt_string = f"{wd_abbr}, {month} {day}"
        else:
            dt_string = f"{wd_abbr}, {day} {month}"
        if incl_time:
            return dt_string + f" {time}"
        
        return dt_string
    
    def _format_time(self, dt: datetime) -> str:
        """Format the datetime into a string for GUI display.

        The datetime builtin returns hour in two character format.  Remove the
        leading zero when present.

        Args:
            date_time: the sunrise or sunset

        Returns:
            the value to display on the screen
        """
        return nice_time(dt,
                         lang=self.lang,
                         speech=False,
                         use_24hour = self.use_24h,
                         use_ampm = not self.use_24h)

    @skill_api_method
    def get_current_weather_homescreen(self, message=None):
        """Get the current temperature and weather condition.
        Returns:
            Dict: {
                weather_temp: current temperature
                high_temperature: forecasted high for today
                low_temperature: forecasted low for today
                weather_code: code representing overall weather condition
                                see Maps for all codes in skill/weather.py
                condition_category: category of conditions eg "Cloudy"
                condition_description: more detail eg "slightly cloudly"
                system_unit: whether the report uses metric or imperial
            }
        """
        try:
            weather_config = self._get_weather_config(message=message)
            weather = get_report(weather_config)

            result = dict(
                weather_temp=weather.current.temperature,
                high_temperature=weather.daily[0].temperature_high,
                low_temperature=weather.daily[0].temperature_low,
                weather_code=weather.current.condition.code,
                condition_category=weather.current.condition.category,
                condition_description=self.resources.render_dialog(
                    weather.current.condition.description
                ),
                system_unit=weather_config.scale
            )

            self.bus.emit(Message("skill-ovos-weather.openvoiceos.weather.response",
                                  {"report": result}))
            return result
        except Exception:
            LOG.exception("Unexpected error getting weather for skill API.")

    def stop(self):
        self.gui.release()
