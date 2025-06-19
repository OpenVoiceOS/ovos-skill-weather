from __future__ import annotations
from typing import Any, Optional, Dict
from pyhtmx import Div, Img
from pyhtmx_gui.kit import Widget, SessionItem, Page
from pyhtmx.html_tag import HTMLTag


CACHE_DIR = "/cache/ovos-skill-weather.openvoiceos/py-htmx"


class WeatherWidget(Widget):
    _parameters = (
        "weatherCode",
        "currentTimezone",
        "currentTemperature",
        "weatherCondition",
        "weatherLocation",
        "highTemperature",
        "lowTemperature",
        "chanceOfPrecipitation",
        "windSpeed",
        "humidity",
    )

    def __init__(self, session_data: Optional[Dict[str, Any]] = None):
        super().__init__(name="weather-widget", session_data=session_data)

        weather_code = session_data.get("weatherCode", 0)
        animation_src = WeatherWidget.get_weather_animation(weather_code)

        self._icon: HTMLTag = HTMLTag(
            tag="lottie-player",
            _id="weather-animation",
            src=animation_src,
            background="transparent",
            loop="",
            autoplay="",
            style={
                "width": "10vw",
                "height": "10vw",
            },
        )
        self.add_interaction(
            "weatherCondition",
            SessionItem(
                parameter="weatherCondition",
                attribute="src",
                component=self._icon,
            ),
        )

        self._temperature: Div = Div(
            inner_content=f"{session_data.get('currentTemperature', '--')}°C",
            _id="current-temperature",
            _class="text-[4vw] font-bold text-gray-800",
        )
        self.add_interaction(
            "currentTemperature",
            SessionItem(
                parameter="currentTemperature",
                attribute="inner_content",
                component=self._temperature,
            ),
        )

        self._location: Div = Div(
            inner_content=session_data.get("weatherLocation", "Unknown Location"),
            _id="weather-location",
            _class="text-[2vw] font-semibold text-gray-800",
        )
        self.add_interaction(
            "weatherLocation",
            SessionItem(
                parameter="weatherLocation",
                attribute="inner_content",
                component=self._location,
            ),
        )

        self._details: Div = Div(
            inner_content=(
                f"High: {session_data.get('highTemperature', '--')}°C | "
                f"Low: {session_data.get('lowTemperature', '--')}°C | "
                f"Humidity: {session_data.get('humidity', '--')}% | "
                f"Wind: {session_data.get('windSpeed', '--')} km/h | "
                f"Precipitation: {session_data.get('chanceOfPrecipitation', '--')}%"
            ),
            _id="weather-details",
            _class="text-[1.5vw] text-gray-800",
        )
        self.add_interaction(
            "weather-details",
            SessionItem(
                parameter="details",
                attribute="inner_content",
                component=self._details,
            ),
        )

        self._widget: Div = Div(
            [
                self._icon,
                self._temperature,
                self._location,
                self._details,
            ],
            _id="weather-widget",
            _class=[
                "p-[1vw]",
                "flex",
                "grow",
                "flex-col",
                "justify-center",
                "items-center",
                "bg-blue-100",
            ],
        )

    @staticmethod
    def get_weather_animation(weather_code: int) -> str:
        animations = {
            0: f"{CACHE_DIR}/animations/sun.json",
            1: f"{CACHE_DIR}/animations/night.json",
            2: f"{CACHE_DIR}/animations/partial_clouds.json",
            3: f"{CACHE_DIR}/animations/partial_clouds.json",
            4: f"{CACHE_DIR}/animations/clouds.json",
            5: f"{CACHE_DIR}/animations/clouds.json",
            6: f"{CACHE_DIR}/animations/partial_clouds.json",
            7: f"{CACHE_DIR}/animations/partial_clouds.json",
            8: f"{CACHE_DIR}/animations/rain.json",
            9: f"{CACHE_DIR}/animations/rain.json",
            10: f"{CACHE_DIR}/animations/rain.json",
            11: f"{CACHE_DIR}/animations/rain.json",
            12: f"{CACHE_DIR}/animations/storm.json",
            13: f"{CACHE_DIR}/animations/storm.json",
            14: f"{CACHE_DIR}/animations/snow.json",
            15: f"{CACHE_DIR}/animations/snow.json",
            16: f"{CACHE_DIR}/animations/fog.json",
            17: f"{CACHE_DIR}/animations/fog.json",
        }
        return animations.get(weather_code, f"{CACHE_DIR}/animations/default_weather.json")


class WeatherPage(Page):
    def __init__(self, session_data: Optional[Dict[str, Any]] = None):
        super().__init__(name="weather-page", session_data=session_data)

        weather_widget = WeatherWidget(session_data=session_data)
        self.add_component(weather_widget)

        self._page: Div = Div(
            [weather_widget._widget],
            _id="weather-page",
            _class="flex flex-col",
            style={"width": "100vw", "height": "100vh"},
        )
