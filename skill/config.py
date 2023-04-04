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
"""Parse the device configuration and skill settings to determine the """
FAHRENHEIT = "fahrenheit"
CELSIUS = "celsius"
METRIC = "metric"
METERS_PER_SECOND = "meters per second"
MILES_PER_HOUR = "miles per hour"


class WeatherConfig:
    """Build an object representing the configuration values for the weather skill."""

    def __init__(self, core_config: dict, settings: dict):
        self.core_config = core_config
        self.settings = settings

    @property
    def city(self):
        """The current value of the city name in the device configuration."""
        return self.core_config["location"]["city"]["name"]

    @property
    def country(self):
        """The current value of the country name in the device configuration."""
        return self.core_config["location"]["city"]["state"]["country"]["name"]

    @property
    def latitude(self):
        """The current value of the latitude location configuration"""
        return self.core_config["location"]["coordinate"]["latitude"]

    @property
    def longitude(self):
        """The current value of the longitude location configuration"""
        return self.core_config["location"]["coordinate"]["longitude"]

    @property
    def state(self):
        """The current value of the state name in the device configuration."""
        return self.core_config["location"]["city"]["state"]["name"]
    
    @property
    def scale(self) -> str:
        unit_from_settings = self.settings.get("units")
        if unit_from_settings is not None and unit_from_settings != "default":
            return unit_from_settings

        return self.core_config["system_unit"]
    
    def speed_unit(self, scale=None) -> str:
        """Use the core configuration to determine the unit of speed.

        Returns: (str) 'meters_sec' or 'mph'
        """
        scale = scale or self.scale
        if scale == METRIC:
            return METERS_PER_SECOND
        else:
            return MILES_PER_HOUR

    def temperature_unit(self, scale=None) -> str:
        """Use the core configuration to determine the unit of temperature.

        Returns: "celsius" or "fahrenheit"""
        scale = scale or self.scale
        if scale == METRIC:
            return CELSIUS
        else:
            return FAHRENHEIT
