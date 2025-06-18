from __future__ import annotations
from typing import Any, Optional, Dict, List
from pyhtmx.html_tag import HTMLTag
from pyhtmx import Div
from pyhtmx_gui.kit import Widget, SessionItem, Page


class DailyForecastWidget(Widget):
    _parameters = ("forecast",)

    def __init__(self, session_data: Optional[Dict[str, Any]] = None):
        super().__init__(name="daily-forecast-widget", session_data=session_data)

        forecast: List[Dict[str, Any]] = session_data.get("forecast", {}).get("all", [])

        forecast_items: List[Div] = []
        for day in forecast:
            date = day.get("date", "Unknown")
            high_temp = day.get("highTemperature", "--")
            low_temp = day.get("lowTemperature", "--")
            condition_code = day.get("weatherCondition", 0)

            animation_src = self.get_weather_animation(condition_code)

            day_item = Div(
                [
                    Div(inner_content=date, _class="text-[2vw] font-bold mb-[0.5vw] text-gray-800"),
                    HTMLTag(
                        tag="lottie-player",
                        src=animation_src,
                        background="transparent",
                        loop="",
                        autoplay="",
                        style={"width": "8vw", "height": "8vw"},
                    ),
                    Div(
                        inner_content=f"High: {high_temp}°C | Low: {low_temp}°C",
                        _class="text-[1.5vw] font-semibold mt-[0.5vw] text-gray-800",
                    ),
                ],
                _class=(
                    "min-w-[20vw] p-[1vw] border border-gray-300 rounded-lg "
                    "flex flex-col items-center bg-white shadow-md"
                ),
            )
            forecast_items.append(day_item)

        self._forecast_list = Div(
            forecast_items,
            _id="daily-forecast-list",
            _class="flex flex-row w-full overflow-x-auto gap-[1vw] pb-[1vw] justify-center",
            style={"scrollbar-width": "none"},
        )

        self.add_interaction(
            "forecast",
            SessionItem(
                parameter="forecast",
                attribute="inner_content",
                component=self._forecast_list,
            ),
        )

        self._title = Div(
            inner_content="Daily Forecast",
            _id="daily-forecast-title",
            _class="text-[3vw] font-bold mb-[1vw] text-gray-800",
        )

        self._widget = Div(
            [
                self._title,
                self._forecast_list,
            ],
            _id="daily-forecast-widget",
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
            0: "assets/animations/sun.json",
            1: "assets/animations/night.json",
            2: "assets/animations/partial_clouds.json",
            3: "assets/animations/partial_clouds.json",
            4: "assets/animations/clouds.json",
            5: "assets/animations/clouds.json",
            6: "assets/animations/partial_clouds.json",
            7: "assets/animations/partial_clouds.json",
            8: "assets/animations/rain.json",
            9: "assets/animations/rain.json",
            10: "assets/animations/rain.json",
            11: "assets/animations/rain.json",
            12: "assets/animations/storm.json",
            13: "assets/animations/storm.json",
            14: "assets/animations/snow.json",
            15: "assets/animations/snow.json",
            16: "assets/animations/fog.json",
            17: "assets/animations/fog.json",
        }
        return animations.get(weather_code, "assets/animations/default_weather.json")


class DailyForecastPage(Page):
    def __init__(self, session_data: Optional[Dict[str, Any]] = None):
        super().__init__(name="daily-forecast-page", session_data=session_data)

        daily_forecast_widget = DailyForecastWidget(session_data=session_data)
        self.add_component(daily_forecast_widget)

        self._page = Div(
            [daily_forecast_widget.widget],
            _id="daily-forecast-page",
            _class="flex flex-col",
            style={"width": "100vw", "height": "100vh"},
        )
