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
from pathlib import Path
from typing import List

import pytz
from ovos_date_parser import nice_date, extract_datetime
from ovos_utils.geolocation import get_geolocation as _get_geo
from ovos_utils.time import now_local, to_local

from .location import (
    answer_names_the_place,
    load_exonyms,
    location_candidates,
)

LOCALE_DIR = Path(__file__).resolve().parent.parent / "locale"


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
) -> datetime:
    """Get a datetime representation of a date or time concept in an utterance.

    Args:
        utterance: the words spoken by the user
        timezone: the timezone requested by the user
        language: the language configured on the device

    Returns:
        The date and time represented in the utterance in the specified timezone.
    """
    utterance_datetime = None
    if timezone is None:
        anchor_date = None
    else:
        intent_timezone = get_tz_info(timezone)
        anchor_date = datetime.now(intent_timezone)
    extract = extract_datetime(utterance, anchorDate=anchor_date, lang=language)
    if extract is not None:
        utterance_datetime, _ = extract
    return utterance_datetime


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
    geolocation = None
    refused = []
    for candidate in location_candidates(
            location, lang, load_exonyms(LOCALE_DIR, lang)):
        answer = _get_geo(candidate, lang=lang)
        if answer is None:
            continue
        named = answer["city"]["name"]
        if not answer_names_the_place(candidate, named):
            # the service answered, but with a district or an unrelated place:
            # speaking that forecast would name the wrong city out loud. See
            # weather_helpers/location.py for the measurements.
            refused.append(f"{candidate} -> {named}")
            continue
        geolocation = answer
        break

    if geolocation is None:
        detail = f" (refused: {'; '.join(refused)})" if refused else ""
        raise LocationNotFoundError(f"Location {location} is unknown{detail}")

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
    now = now_local()
    tomorrow = now.date() + timedelta(days=1)

    # A little hack to prevent nice_date() from returning "tomorrow"
    if date_to_speak.date() == tomorrow:
        now_arg = now - timedelta(days=1)
    else:
        now_arg = now

    speakable_date = nice_date(date_to_speak, now=now_arg, lang=lang)
    day_of_week = speakable_date.split(",")[0]

    return day_of_week


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
