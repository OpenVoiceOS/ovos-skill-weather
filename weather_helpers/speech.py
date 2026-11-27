"""Spoken clock times: the chronologia writer where it writes the language,
ovos-date-parser for every other language and for each form chronologia
does not write."""
import datetime

from chronologia.spoken import UnsupportedForm, spoken_time as _time, writes
from ovos_date_parser import nice_time


def spoken_time(dt: datetime.datetime, lang: str) -> str:
    if writes(lang):
        try:
            return _time(lang, dt.hour, dt.minute, clock="12h", style="phrase")
        except UnsupportedForm:
            pass
    return nice_time(dt, lang=lang)
