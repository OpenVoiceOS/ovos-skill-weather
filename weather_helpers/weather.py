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
"""Representations and conversions of the data returned by the weather API."""
from datetime import timedelta
from pathlib import Path
from typing import List, Tuple

# TODO - get rid of relative imports as soon as skills can be properly packaged with arbitrary module structures
from .config import MILES_PER_HOUR
from .util import convert_to_local_datetime

# Forecast timeframes
CURRENT = "current"
DAILY = "daily"
HOURLY = "hourly"

# Days of week
SATURDAY = 5
SUNDAY = 6

# Condition Icons (see https://openweathermap.org/weather-conditions)
#   Map each of the possible weather condition icon codes from OpenWeatherMap to an
#   image/animation file used by the GUI.  The icon codes contain a number and a letter.
#   A "n" after the number indicates night and a "d" indicates day.
#
#   The icon/image map is used by the Mark II, which does not use animations for
#   performance reasons.  The icon/animation map is used by the scalable QML.  The
#   icon/code map is for the Mark I, which accepts a code to determine what
#   is displayed.
ICON_IMAGE_MAP = (
    (("01d",), "sun.svg"),
    (("01n",), "moon.svg"),
    (("04d", "04n"), "clouds.svg"),
    (("50d",), "fog.svg"),
    (("02d", "03d"), "partial_clouds_day.svg"),
    (("02n", "03n"), "partial_clouds_night.svg"),
    (("09d", "10d"), "rain.svg"),
    (("13d",), "snow.svg"),
    (("11d",), "storm.svg"),
)
ICON_ANIMATION_MAP = (
    (("01d", "01n"), "sun.json"),
    (("04d", "04n"), "clouds.json"),
    (("50d",), "fog.json"),
    (("02d", "03d", "02n", "03n"), "partial_clouds.json"),
    (("09d", "10d"), "rain.json"),
    (("13d",), "snow.json"),
    (("11d",), "storm.json"),
)

ICON_CODE_MAP = (
    (("01d", "01n"), 0),
    (("04d", "04n"), 2),
    (("50d", "50n"), 7),
    (("02d", "03d", "02n", "03n"), 1),
    (("09d", "09n", "10d", "10n"), 3),
    (("13d", "13n"), 6),
    (("11d", "11n"), 5),
)

ICON_CODE_MAP_ANIMATED = (
    (("01d",), 0),  # clear sky day
    (("01n",), 1),  # clear sky night
    (("02d",), 2),  # few clouds day
    (("02n",), 3),  # few clouds night
    (("03d",), 4),  # scattered clouds day
    (("03n",), 5),  # scattered clouds night
    (("04d",), 6),  # broken clouds day
    (("04n",), 7),  # broken clouds night
    (("09d",), 8),  # shower rain day
    (("09n",), 9),  # shower rain night
    (("10d",), 10),  # rain day
    (("10n",), 11),  # rain night
    (("11d",), 12),  # thunderstorm day
    (("11n",), 13),  # thunderstorm night
    (("13d",), 14),  # snow day
    (("13n",), 15),  # snow night
    (("50d",), 16),  # mist day
    (("50n",), 17),  # mist night
)

THIRTY_PERCENT = 30
WIND_DIRECTION_CONVERSION = (
    (22.5, "north"),
    (67.5, "northeast"),
    (112.5, "east"),
    (157.5, "southeast"),
    (202.5, "south"),
    (247.5, "southwest"),
    (292.5, "west"),
    (337.5, "northwest"),
)


class WeatherCondition:
    """Data representation of a weather conditions JSON object from the API
    WMO Weather interpretation codes (WW)
    Code 	Description
    0 	Clear sky
    1, 2, 3 	Mainly clear, partly cloudy, and overcast
    45, 48 	Fog and depositing rime fog
    51, 53, 55 	Drizzle: Light, moderate, and dense intensity
    56, 57 	Freezing Drizzle: Light and dense intensity
    61, 63, 65 	Rain: Slight, moderate and heavy intensity
    66, 67 	Freezing Rain: Light and heavy intensity
    71, 73, 75 	Snow fall: Slight, moderate, and heavy intensity
    77 	Snow grains
    80, 81, 82 	Rain showers: Slight, moderate, and violent
    85, 86 	Snow showers slight and heavy
    95 * 	Thunderstorm: Slight or moderate
    96, 99 * 	Thunderstorm with slight and heavy hail
    """

    def __init__(self, weather_code: str, is_day: bool = True):
        # TODO - localization + improve icon/category mappings
        weather_code = int(weather_code)
        if weather_code <= 1: # clear
            self.category = "clear"
            if is_day:
                self.icon = "01d"  # sun
            else:
                self.icon = "01n"  # moon
        elif 2 <= weather_code <= 3: # clouds
            self.category = "clouds"
            if is_day:
                self.icon = "02d"
            else:
                self.icon = "02n"
        elif 45 <= weather_code <= 48: # fog
            self.category = "fog"
            if is_day:
                self.icon = "50d"
            else:
                self.icon = "50n"
        elif 51 <= weather_code <= 67: # rain
            self.category = "rain"
            if is_day:
                self.icon = "10d"
            else:
                self.icon = "10n"
        elif 71 <= weather_code <= 77 or 85 <= weather_code <= 86: # snow
            self.category = "snow"
            if is_day:
                self.icon = "13d"
            else:
                self.icon = "13n"
        elif 80 <= weather_code <= 86: # rain shower
            self.category = "rain"
            if is_day:
                self.icon = "09d"
            else:
                self.icon = "09n"
        elif 95 <= weather_code <= 99: # thunderstorm
            self.category = "thunderstorm"
            if is_day:
                self.icon = "11d"
            else:
                self.icon = "11n"

        if weather_code == 0:
            self.description = "clear_sky"
        elif weather_code == 1:
            self.description = "mainly_clear"
        elif weather_code == 2:
            self.description = "partly_cloudy"
        elif weather_code == 3:
            self.description = "overcast"
        elif weather_code == 45:
            self.description = "fog"
        elif weather_code == 48:
            self.description = "depositing_rime_fog"
        elif weather_code == 51:
            self.description = "drizzle_light_intensity"
        elif weather_code == 53:
            self.description = "drizzle_moderate_intensity"
        elif weather_code == 55:
            self.description = "drizzle_dense_intensity"
        elif weather_code == 56:
            self.description = "freezing_drizzle_light_intensity"
        elif weather_code == 57:
            self.description = "freezing_drizzle_dense_intensity"
        elif weather_code == 61:
            self.description = "slight_rain"
        elif weather_code == 63:
            self.description = "moderate_rain"
        elif weather_code == 65:
            self.description = "heavy_rain"
        elif weather_code == 66:
            self.description = "freezing_rain_light_intensity"
        elif weather_code == 67:
            self.description = "freezing_rain_dense_intensity"
        elif weather_code == 71:
            self.description = "slight_snow_fall"
        elif weather_code == 73:
            self.description = "moderate_snow_fall"
        elif weather_code == 75:
            self.description = "heavy_snow_fall"
        elif weather_code == 77:
            self.description = "snow_grains"
        elif weather_code == 80:
            self.description = "slight_rain_showers"
        elif weather_code == 81:
            self.description = "moderate_rain_showers"
        elif weather_code == 82:
            self.description = "violent_rain_showers"
        elif weather_code == 85:
            self.description = "slight_snow_showers"
        elif weather_code == 86:
            self.description = "heavy_snow_showers"
        elif weather_code == 95:
            self.description = "thunderstorm"
        elif weather_code == 96:
            self.description = "thunderstorm_with_slight_hail"
        elif weather_code == 99:
            self.description = "thunderstorm_with_heavy_hail"
        self.id = weather_code

    @property
    def image(self) -> str:
        """Use the icon to image mapping to determine which image to display."""
        image_path = Path("images")
        for icons, image_file_name in ICON_IMAGE_MAP:
            if self.icon in icons:
                image_path = image_path.joinpath(image_file_name)
        return str(image_path)

    @property
    def animation(self) -> str:
        """Use the icon to animation mapping to determine which animation to display."""
        image_path = Path("animations")
        for icons, animation_file_name in ICON_ANIMATION_MAP:
            if self.icon in icons:
                image_path = image_path.joinpath(animation_file_name)
        return str(image_path)

    @property
    def code(self) -> str:
        """Use the icon to animation mapping to determine which animation to display."""
        condition_code = None
        for icons, code in ICON_CODE_MAP:
            if self.icon in icons:
                condition_code = code
        return condition_code

    @property
    def animated_code(self) -> str:
        """Use the icon to animation mapping to determine which animation to display."""
        condition_code = None
        for icons, code in ICON_CODE_MAP_ANIMATED:
            if self.icon in icons:
                condition_code = code
        return condition_code


class Weather:
    """Abstract data representation of commonalities in forecast types."""

    def __init__(self, weather: dict, timezone: str, units: dict):
        self.date_time = convert_to_local_datetime(weather["time"], timezone)
        self.units = units  # if any conversion is needed, this tells us the source units in the raw data
        # TODO - handle any missing data that we can derive
        self.pressure = weather.get("surface_pressure")
        self.humidity = weather.get("relativehumidity_2m") or \
                        weather.get("relativehumidity_1000hPa")
        self.dew_point = weather.get("dewpoint_2m")
        self.clouds = weather.get("cloudcover")
        self.wind_speed = weather.get("windspeed_10m")
        self.wind_speed_max = weather.get("windspeed_10m_max") or self.wind_speed
        self.wind_direction = weather.get("winddirection_10m") or weather.get("winddirection_10m_dominant")
        if self.wind_direction:
            self.wind_direction = self._determine_wind_direction(self.wind_direction)
        self.sunrise = weather.get("sunrise")
        if self.sunrise and isinstance(self.sunrise, str):
            self.sunrise = convert_to_local_datetime(self.sunrise, timezone)
        self.sunset = weather.get("sunset")
        if self.sunset and isinstance(self.sunset, str):
            self.sunset = convert_to_local_datetime(self.sunset, timezone)
        self.temperature = weather.get("temperature_2m")
        self.visibility = weather.get("visibility")
        self.temperature_low = weather.get("temperature_2m_min") or self.temperature
        self.temperature_high = weather.get("temperature_2m_max") or self.temperature
        self.chance_of_precipitation = weather.get("precipitation_probability_mean") or \
                                       weather.get("precipitation_probability_max") or \
                                       weather.get("precipitation_probability_min") or \
                                       weather.get("precipitation_probability") or 0
        self.precipitation = weather.get("precipitation_sum") or weather.get("precipitation")
        self.uvindex = weather.get("uv_index_max") or \
                int(weather.get("shortwave_radiation") * 3.6 / 27.8 )
        self.condition = WeatherCondition(weather["weathercode"])

    @staticmethod
    def _determine_wind_direction(degree_direction: int):
        """Convert wind direction from compass degrees to compass direction.

        Args:
            degree_direction: Degrees on a compass indicating wind direction.

        Returns:
            the wind direction in one of eight compass directions
        """
        for min_degree, compass_direction in WIND_DIRECTION_CONVERSION:
            if degree_direction < min_degree:
                wind_direction = compass_direction
                break
        else:
            wind_direction = "north"

        return wind_direction

    def determine_wind_strength(self, speed_unit: str):
        """Convert a wind speed to a wind strength.

        Args:
            speed_unit: unit of measure for speed depending on device configuration

        Returns:
            a string representation of the wind strength
        """
        if speed_unit == MILES_PER_HOUR:
            limits = dict(strong=20, moderate=11)
        else:
            limits = dict(strong=9, moderate=5)

        speed = self.wind_speed or self.wind_speed_max
        if speed >= limits["strong"]:
            wind_strength = "strong"
        elif speed >= limits["moderate"]:
            wind_strength = "moderate"
        else:
            wind_strength = "light"

        return wind_strength


class WeatherReport:
    """Full representation of the data returned by the OpenMeteo API"""

    def __init__(self, report):
        timezone = report["timezone"]
        self.hourly = []
        for idx, _ in enumerate(report["hourly"]["time"]):
            r = {k: hour[idx] for k, hour in report["hourly"].items()}
            # ['time', 'temperature_2m', 'relativehumidity_2m', 'dewpoint_2m', 'apparent_temperature',
            # 'pressure_msl', 'surface_pressure', 'cloudcover', 'cloudcover_low', 'cloudcover_mid',
            # 'cloudcover_high', 'windspeed_10m', 'windspeed_80m', 'windspeed_120m', 'windspeed_180m',
            # 'winddirection_10m', 'winddirection_80m', 'winddirection_120m', 'winddirection_180m',
            # 'windgusts_10m', 'shortwave_radiation', 'direct_radiation', 'diffuse_radiation',
            # 'vapor_pressure_deficit', 'cape', 'evapotranspiration', 'et0_fao_evapotranspiration',
            # 'precipitation', 'weathercode', 'snow_depth', 'showers', 'snowfall', 'visibility',
            # 'precipitation_probability', 'freezinglevel_height', 'soil_temperature_0cm',
            # 'soil_temperature_6cm', 'soil_temperature_18cm', 'soil_temperature_54cm',
            # 'soil_moisture_0_1cm', 'soil_moisture_1_3cm', 'soil_moisture_3_9cm', 'soil_moisture_9_27cm',
            # 'soil_moisture_27_81cm', 'is_day']
            self.hourly.append(Weather(r, timezone, report["hourly_units"]))
        
        self.current = self.hourly[0]

        self.daily = []
        for idx, _ in enumerate(report["daily"]["time"]):
            r = {k: hour[idx] for k, hour in report["daily"].items()}
            # ['time', 'temperature_2m_max', 'temperature_2m_min', 'apparent_temperature_max',
            # 'apparent_temperature_min', 'precipitation_sum', 'precipitation_hours', 'weathercode',
            # 'sunrise', 'sunset', 'windspeed_10m_max', 'windgusts_10m_max', 'winddirection_10m_dominant',
            # 'shortwave_radiation_sum', 'et0_fao_evapotranspiration', 'uv_index_max',
            # 'precipitation_probability_mean', 'precipitation_probability_min', 'precipitation_probability_max',
            # 'uv_index_clear_sky_max']
            self.daily.append(Weather(r, timezone, report["daily_units"]))

    def get_weather_for_intent(self, intent_data) -> Weather:
        """Use the intent to determine which forecast satisfies the request.

        Args:
            intent_data: Parsed intent data
        """
        if intent_data.timeframe == "hourly":
            weather = self.get_forecast_for_hour(intent_data)
        elif intent_data.timeframe == "daily":
            weather = self.get_forecast_for_date(intent_data)
        else:
            weather = self.current

        return weather

    def get_forecast_for_date(self, intent_data) -> Weather:
        """Use the intent to determine which daily forecast(s) satisfies the request.

        Args:
            intent_data: Parsed intent data
        """
        if intent_data.intent_datetime.date() == intent_data.location_datetime.date():
            forecast = self.daily[0]
        else:
            delta = intent_data.intent_datetime - intent_data.location_datetime
            day_delta = int(delta / timedelta(days=1))
            day_index = day_delta + 1
            forecast = self.daily[day_index]

        return forecast

    def get_forecast_for_multiple_days(self, days: int) -> List[Weather]:
        """Use the intent to determine which daily forecast(s) satisfies the request.

        Args:
            days: number of forecast days to return

        Returns:
            list of daily forecasts for the specified number of days

        Raises:
            IndexError when number of days is more than what is returned by the API
        """
        if days > 7:
            raise IndexError("Only seven days of forecasted weather available.")

        forecast = self.daily[1: days + 1]

        return forecast

    def get_forecast_for_hour(self, intent_data) -> Weather:
        """Use the intent to determine which hourly forecast satisfies the request.

        Args:
            intent_data: Parsed intent data

        Returns:
            A single hour of forecast data based on the intent data
        """
        delta = intent_data.intent_datetime - intent_data.location_datetime
        hour_delta = int(delta / timedelta(hours=1))
        hour_index = hour_delta + 1
        report = self.hourly[hour_index]

        return report

    def get_forecast_for_multiple_hours(self, intent_data) ->List[Weather]:
        """Use the intent to determine which hourly forecasts satisfies the request.
        The hourly up from the requested timeframe are returned

        Args:
            intent_data: Parsed intent data

        Returns:
            List of hourly forecasts
        """
        delta = intent_data.intent_datetime - intent_data.location_datetime
        hour_delta = int(delta / timedelta(hours=1))
        hour_index = hour_delta + 1
        forecast = self.hourly[hour_index:]

        return forecast 

    def get_weekend_forecast(self) -> List[Weather]:
        """Use the intent to determine which daily forecast(s) satisfies the request.

        Returns:
            The Saturday and Sunday forecast from the list of daily forecasts
        """
        forecast = list()
        for forecast_day in self.daily:
            report_date = forecast_day.date_time.date()
            if report_date.weekday() in (SATURDAY, SUNDAY):
                forecast.append(forecast_day)

        return forecast

    def get_next_precipitation(self, intent_data) -> Tuple[Weather, str]:
        """Determine when the next chance of precipitation is in the forecast.

        Args:
            intent_data: Parsed intent data

        Returns:
            The weather report containing the next chance of rain and the timeframe of
            the selected report.
        """
        report = None
        current_precipitation = True
        timeframe = HOURLY
        for hourly in self.hourly:
            if hourly.date_time.date() > intent_data.location_datetime.date():
                break
            if hourly.chance_of_precipitation > THIRTY_PERCENT:
                if not current_precipitation:
                    report = hourly
                    break
            else:
                current_precipitation = False

        if report is None:
            timeframe = DAILY
            for daily in self.daily:
                if daily.date_time.date() == intent_data.location_datetime.date():
                    continue
                if daily.chance_of_precipitation > THIRTY_PERCENT:
                    report = daily
                    break

        return report, timeframe
