"""Spoken clock times: the chronologia writer where it writes the language,
ovos-date-parser for every other language."""
import datetime

from chronologia.spoken import spoken_time as _time, writes
from ovos_date_parser import nice_time


def spoken_time(dt: datetime.datetime, lang: str) -> str:
    if writes(lang):
        return _time(lang, dt.hour, dt.minute, clock="12h", style="phrase")
    return nice_time(dt, lang=lang)
