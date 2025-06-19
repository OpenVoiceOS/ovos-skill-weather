from __future__ import annotations
from pyhtmx.html_tag import HTMLTag
from pyhtmx import Div
from pyhtmx_gui.kit import Widget, Page, SessionItem
from typing import Any, Dict, Optional, List


CACHE_SUBDIR = "/cache/ovos-skill-weather.openvoiceos/py-htmx"


class HourlyForecastWidget(Widget):
    _parameters = ("hourlyForecast",)

    def __init__(self, session_data: Optional[Dict[str, Any]] = None):
        super().__init__(name="hourly-forecast-widget", session_data=session_data)

        hourly_forecast = session_data.get("hourlyForecast", {}).get("hours", [])

        forecast_items = []
        for hour in hourly_forecast:
            if isinstance(hour, dict):
                time = hour.get("time", "--:--")
                temperature = hour.get("temperature", "--")
                condition_code = hour.get("weatherCondition", 0)

                animation_src = self.get_weather_animation(condition_code)

                forecast_item = Div(
                    [
                        Div(inner_content=time, _class="text-[2vw] font-bold mb-[0.5vw] text-gray-800"),
                        HTMLTag(
                            tag="lottie-player",
                            src=animation_src,
                            background="transparent",
                            loop="",
                            autoplay="",
                            style={"width": "6vw", "height": "6vw"},
                        ),
                        Div(
                            inner_content=f"{temperature}°C",
                            _class="text-[1.5vw] font-semibold text-gray-800",
                        ),
                    ],
                    _class=(
                        "p-[1vw] border-[1px] border-gray-300 rounded-md flex flex-col items-center "
                        "bg-white shadow-md mb-[1vw]"
                    ),
                )
                forecast_items.append(forecast_item)
            else:
                print(f"WARNING: Unexpected data format for hour: {hour}")

        self._forecast_list = Div(
            forecast_items,
            _id="hourly-forecast-list",
            _class="flex flex-row flex-wrap justify-center gap-[1vw]",
        )
        self.add_interaction(
            "hourlyForecast",
            SessionItem(
                parameter="hourlyForecast",
                attribute="inner_content",
                component=self._forecast_list,
            ),
        )

        self._title = Div(
            inner_content="Hourly Forecast",
            _id="hourly-forecast-title",
            _class="text-[3vw] font-bold mb-[1vw] text-gray-800",
        )

        self._widget = Div(
            [
                self._title,
                self._forecast_list,
            ],
            _id="hourly-forecast-widget",
            _class=[
                "p-[2vw]",
                "flex",
                "grow",
                "flex-col",
                "justify-start",
                "items-center",
                "bg-blue-50",
            ],
        )

    @staticmethod
    def get_weather_animation(weather_code: int) -> str:
        animations = {
            0: f"{CACHE_SUBDIR}/animations/sun.json",
            1: f"{CACHE_SUBDIR}/animations/night.json",
            2: f"{CACHE_SUBDIR}/animations/partial_clouds.json",
            3: f"{CACHE_SUBDIR}/animations/partial_clouds.json",
            4: f"{CACHE_SUBDIR}/animations/clouds.json",
            5: f"{CACHE_SUBDIR}/animations/clouds.json",
            6: f"{CACHE_SUBDIR}/animations/partial_clouds.json",
            7: f"{CACHE_SUBDIR}/animations/partial_clouds.json",
            8: f"{CACHE_SUBDIR}/animations/rain.json",
            9: f"{CACHE_SUBDIR}/animations/rain.json",
            10: f"{CACHE_SUBDIR}/animations/rain.json",
            11: f"{CACHE_SUBDIR}/animations/rain.json",
            12: f"{CACHE_SUBDIR}/animations/storm.json",
            13: f"{CACHE_SUBDIR}/animations/storm.json",
            14: f"{CACHE_SUBDIR}/animations/snow.json",
            15: f"{CACHE_SUBDIR}/animations/snow.json",
            16: f"{CACHE_SUBDIR}/animations/fog.json",
            17: f"{CACHE_SUBDIR}/animations/fog.json",
        }
        return animations.get(weather_code, f"{CACHE_SUBDIR}/animations/default_weather.json")


class HourlyForecastPage(Page):
    def __init__(self, session_data: Optional[Dict[str, Any]] = None):
        super().__init__(name="hourly-forecast", session_data=session_data)

        hourly_forecast_widget = HourlyForecastWidget(session_data=session_data)
        self.add_component(hourly_forecast_widget)

        self._page = Div(
            hourly_forecast_widget.widget,
            _id="hourly-forecast",
            _class="flex flex-col",
            style={"width": "100vw", "height": "100vh"},
        )
