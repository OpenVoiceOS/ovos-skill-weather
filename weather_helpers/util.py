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
"""Utility functions for the weather skill."""
from datetime import datetime, timedelta, tzinfo
from itertools import islice
from typing import List, Optional
from zoneinfo import ZoneInfo

import pytz
from chronologia import DAY_PARTS, extract_timespan
from ovos_date_parser import nice_weekday
from ovos_utils.geolocation import get_geolocation as _get_geo
from ovos_utils.time import now_local, to_local


class LocationNotFoundError(ValueError):
    """Raise when the API cannot find the requested location."""
    pass


def convert_to_local_datetime(isodate: str, timezone: str) -> datetime:
    """Convert a timestamp to a datetime object in the requested timezone.

    This function assumes it is passed a timestamp in the UTC timezone.  It
    then adjusts the datetime to match the specified timezone.

    Args:
        isodate: seconds since epoch
        timezone: the timezone of the weather report

    Returns:
        A datetime in the user timezone
    """
    naive_datetime = datetime.fromisoformat(isodate)
    tz_datetime = naive_datetime.astimezone(pytz.timezone(timezone))
    return to_local(tz_datetime)


def get_utterance_datetime(
        utterance: str, timezone: str = None, language: str = None
) -> Optional[datetime]:
    """Get a datetime representation of a date or time concept in an utterance.

    A time of a day or more ("tomorrow", "in 3 days", "this weekend") answers
    the midnight of its first day that is not over, which asks for a daily
    forecast. A part of the day ("tonight", "friday evening") answers its
    middle, and a shorter time ("at 9 pm") its start, which ask for an hourly
    forecast. A shorter time that holds the present moment ("this evening"
    said in the evening) answers None, which asks for the current weather.

    Args:
        utterance: the words spoken by the user
        timezone: the timezone requested by the user
        language: the language configured on the device

    Returns:
        The date and time represented in the utterance in the specified
        timezone, or None when the utterance names no time or a time that
        holds the present moment.
    """
    anchor = now_local() if timezone is None else datetime.now(ZoneInfo(timezone))
    found = extract_timespan(utterance, language, anchor)
    if found is None or None in (found.span.start_datetime, found.span.end_datetime):
        return None
    # chronologia answers in the anchor's wall clock without a zone
    start, end = (moment.replace(tzinfo=anchor.tzinfo) for moment in
                  (found.span.start_datetime, found.span.end_datetime))
    if found.span.width >= timedelta(days=1):
        return max(start, anchor).replace(hour=0, minute=0, second=0, microsecond=0) \
            if anchor < end else start
    if _is_part_of_day(start, end, language):
        # a night is the night of the day it opens on, so the band is cut at
        # midnight before its middle is taken
        end = min(end, start.replace(hour=0, minute=0, second=0, microsecond=0)
                  + timedelta(days=1))
        start = start + (end - start) / 2
    return None if start < anchor < end else start


def _is_part_of_day(start: datetime, end: datetime, language: str) -> bool:
    """Whether the span is exactly one of the language's parts of the day.

    A language with no bands of its own reads chronologia's default bands.
    """
    code = language.split("-")[0]
    bands = {(part.start, part.end) for part in DAY_PARTS.values() if part.lang == code} \
        or {(part.start, part.end) for part in DAY_PARTS.values() if part.lang is None}
    return (start.time(), end.time()) in bands


def get_tz_info(timezone: str) -> tzinfo:
    """Generate a tzinfo object from a timezone string.

    Args:
        timezone: a string representing a timezone

    Returns:
        timezone in a string format
    """
    return pytz.timezone(timezone)


def get_geolocation(location: str, lang: str = "en"):
    """Retrieve the geolocation information about the requested location.

    Args:
        location: a location specified in the utterance
        lang: lang to return country/region in

    Returns:
        A deserialized JSON object containing geolocation information for the
        specified city.

    Raises:
        LocationNotFound error if the API returns no results.
    """
    geolocation = _get_geo(location, lang=lang)

    if geolocation is None:
        raise LocationNotFoundError(f"Location {location} is unknown")

    # convert the dict to a simpler format
    return {
        "city": geolocation["city"]["name"],
        "region": geolocation["city"]["state"]["name"],
        "country": geolocation["city"]["state"]["country"]["name"],
        "latitude": geolocation["coordinate"]["latitude"],
        "longitude": geolocation["coordinate"]["longitude"],
        "timezone": geolocation["timezone"]["code"]
    }


def get_time_period(intent_datetime: datetime) -> str:
    """Translate a specific time '9am' to period of the day 'morning'

    Args:
        intent_datetime: the datetime extracted from an utterance

    Returns:
        A generalized time of day based on the passed datetime object.
    """
    hour = intent_datetime.time().hour
    if 1 <= hour < 5:
        period = "early morning"
    elif 5 <= hour < 12:
        period = "morning"
    elif 12 <= hour < 17:
        period = "afternoon"
    elif 17 <= hour < 20:
        period = "evening"
    else:
        period = "overnight"
    return period


def get_speakable_day_of_week(date_to_speak: datetime, lang: str):
    """Convert the time of the a daily weather forecast to a speakable day of week.

    Args:
        date_to_speak: The date/time for the forecast being reported.

    Returns:
        The day of the week in the device's configured language
    """
    return nice_weekday(date_to_speak, lang=lang)


def chunk_list(it: list, size: int) -> List[tuple]:
    """Takes in a list and chops it in `size` length tuples

    Args:
        it (list): list to chop
        size (int): size of the chunks

    Returns:
        List[tuple]: a list of tuple containing the chunks
    """
    it = iter(it)
    return list(iter(lambda: tuple(islice(it, size)), ()))
