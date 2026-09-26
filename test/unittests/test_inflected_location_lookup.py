"""The spoken place name reaches the geocoder in a form the geocoder knows.

Every case here replays a lookup that was measured against the live service
(localize, T-5509 and T-5565) and is driven through a stub built from those
measurements, so the suite is offline and deterministic. The stub is the whole
point: it answers exactly what the real service answered, including the wrong
answers, so a test that passes here says the skill now asks better questions --
not that the service changed.
"""
import json
from pathlib import Path

import pytest

from weather_helpers import location as loc
from weather_helpers.util import LocationNotFoundError, get_geolocation

# What the live service returns, keyed by the string it is asked for. A value of
# None is "not found"; a string is the city name it answers with.
MEASURED = {
    # resolves today, and must keep resolving
    "Helsingissä": "Helsinki",
    "Helsinki": "Helsinki",
    "Turussa": "Turku",
    "Turku": "Turku",
    "Budapesten": "Budapest",
    "Budapest": "Budapest",
    "İstanbul'da": "İstanbul",
    "İstanbul": "İstanbul",
    # a miss today, and the stem answers
    "Tampereella": None,
    "Tampere": "Tampere",
    "Rovaniemellä": None,
    "Rovanieme": None,
    "Rovaniemi": "Rovaniemi",
    "Szegeden": None,
    "Szeged": "Szeged",
    # answers with a district today, which is worse than a miss
    "Ankarada": "Etimesgut",
    "Ankara": "Ankara",
    # the Finnish exonyms, which resolve to the wrong place by name
    "Lontoo": "City of Westminster",
    "London": "London",
    "Peking": "Chaoyang",
    "Beijing": "Beijing",
    "Tokio": "Shinjuku",
    "Tokyo": "Tokyo",
    "Meksiko": "Villa de Cos",
    "Mexico City": "Mexico City",
    "Souli": "Souli",          # a Greek village: the name even matches
    "Seoul": "Seoul",
    # the negative controls from the same measurement
    "qwertzuiop": None,
    "zzzxxxyyy": None,
    "iltapäivällä": None,
    "iltapäivä": None,
    "lämpötila": None,
}


def _answer(city):
    return {
        "city": {"name": city,
                 "state": {"name": "state", "country": {"name": "country"}}},
        "coordinate": {"latitude": 0.0, "longitude": 0.0},
        "timezone": {"code": "UTC"},
    }


@pytest.fixture
def service(monkeypatch):
    """The live service, as measured, plus a record of what was asked."""
    asked = []

    def _fake_get_geo(query, lang="en"):
        asked.append(query)
        city = MEASURED.get(query, "__unmeasured__")
        if city == "__unmeasured__":
            # an unlisted query is a miss: the point is never to assume the
            # service is generous with a form nobody measured.
            return None
        return _answer(city) if city else None

    monkeypatch.setattr("weather_helpers.util._get_geo", _fake_get_geo)
    loc._EXONYM_CACHE.clear()
    yield asked
    loc._EXONYM_CACHE.clear()


def test_the_stub_is_wired(service):
    """The control: with the stub in place a plain name still resolves."""
    assert get_geolocation("Helsinki", lang="fi-FI")["city"] == "Helsinki"
    assert service == ["Helsinki"]


@pytest.mark.parametrize("spoken,city,lang", [
    ("Helsingissä", "Helsinki", "fi-FI"),
    ("Turussa", "Turku", "fi-FI"),
    ("Budapesten", "Budapest", "hu-HU"),
    ("İstanbul'da", "İstanbul", "tr-TR"),
])
def test_a_form_that_already_worked_still_works(service, spoken, city, lang):
    """These four resolved before this change. They must not regress, and they
    must still cost one lookup: the form as said is always tried first."""
    assert get_geolocation(spoken, lang=lang)["city"] == city
    assert service[0] == spoken


@pytest.mark.parametrize("spoken,city,lang", [
    ("Tampereella", "Tampere", "fi-FI"),
    ("Rovaniemellä", "Rovaniemi", "fi-FI"),
    ("Szegeden", "Szeged", "hu-HU"),
])
def test_a_case_ending_no_longer_hides_the_place(service, spoken, city, lang):
    """The misses. The stem, or the stem with its final vowel restored, is what
    the service knows."""
    assert get_geolocation(spoken, lang=lang)["city"] == city


def test_a_district_answer_is_refused_and_the_city_is_found(service):
    """The dangerous case: Ankarada answered Etimesgut, a district of Ankara,
    so the skill read a forecast for the wrong place out loud."""
    assert get_geolocation("Ankarada", lang="tr-TR")["city"] == "Ankara"
    assert service[0] == "Ankarada", "the form as said is still tried first"
    assert "Ankara" in service


@pytest.mark.parametrize("spoken,city", [
    ("Lontoo", "London"),
    ("Peking", "Beijing"),
    ("Tokio", "Tokyo"),
    ("Meksiko", "Mexico City"),
])
def test_an_exonym_resolves_through_the_locale_table(service, spoken, city):
    """Half the Finnish exonyms answered with a district or another town. An
    exonym shares no prefix with its endonym, so the locale table carries it."""
    assert get_geolocation(spoken, lang="fi-FI")["city"] == city


@pytest.mark.parametrize("spoken", ["qwertzuiop", "zzzxxxyyy", "lämpötila"])
def test_a_word_that_is_not_a_place_is_still_not_a_place(service, spoken):
    """The negative control that makes the rest mean something. Candidate
    generation must not turn nonsense, or a common noun, into a hit."""
    with pytest.raises(LocationNotFoundError):
        get_geolocation(spoken, lang="fi-FI")


def test_a_refused_answer_is_named_in_the_error(service):
    """When every candidate is refused, the error says what was refused, or the
    next reader cannot tell a miss from a rejected district.

    Turkish has no exonym table, so "Lontoo" there is only ever the raw form,
    and the service answers City of Westminster, which the prefix rule refuses.
    """
    with pytest.raises(LocationNotFoundError) as caught:
        get_geolocation("Lontoo", lang="tr-TR")
    message = str(caught.value)
    assert "Lontoo" in message
    assert "City of Westminster" in message, \
        "the error must say what was refused, not only that nothing was found"


def test_the_souli_village_is_still_reachable_in_finnish(service):
    """Seoul in Finnish is Souli, and Souli is also a Greek village the service
    answers with that very name. The prefix rule alone cannot tell them apart,
    which is exactly why the exonym table is consulted before the stem."""
    assert get_geolocation("Souli", lang="fi-FI")["city"] == "Seoul"


def test_a_language_without_case_endings_costs_one_lookup(service):
    """Nothing changes for en-US: one candidate, one call."""
    assert get_geolocation("London", lang="en-US")["city"] == "London"
    assert service == ["London"]


class TestTheParts:
    """The helpers, pinned directly so a failure above can be located."""

    def test_the_prefix_rule_accepts_an_inflected_form(self):
        assert loc.answer_names_the_place("Helsingissä", "Helsinki")
        assert loc.answer_names_the_place("Turussa", "Turku")

    def test_the_prefix_rule_refuses_a_district(self):
        assert not loc.answer_names_the_place("Ankarada", "Etimesgut")
        assert not loc.answer_names_the_place("Lontoo", "City of Westminster")
        assert not loc.answer_names_the_place("Meksiko", "Villa de Cos")

    def test_the_prefix_rule_and_the_exonym_table_divide_the_work(self):
        """Tokio and Tokyo share "tok", so the prefix rule accepts that pair on
        its own and the table only has to get the lookup to Tokyo. Peking and
        Beijing share nothing, so for that pair the table is not optional."""
        assert loc.answer_names_the_place("Tokio", "Tokyo")
        assert not loc.answer_names_the_place("Peking", "Beijing")
        assert not loc.answer_names_the_place("Tokio", "Shinjuku")

    def test_a_short_stem_is_not_offered(self):
        """Stripping "de" from a three-letter name would leave one letter and
        match anything."""
        assert "E" not in loc.location_candidates("Ede", "tr-TR")

    def test_the_candidates_are_ordered_and_unique(self):
        got = loc.location_candidates("Tampereella", "fi-FI")
        assert got[0] == "Tampereella"
        assert "Tampere" in got
        assert len(got) == len(set(loc.fold(c) for c in got))

    def test_a_locale_with_no_table_loads_an_empty_one(self):
        table = loc.load_exonyms(
            Path(__file__).resolve().parents[2] / "locale", "de-DE")
        assert table == {}

    def test_the_finnish_table_is_read_from_the_locale_file(self):
        root = Path(__file__).resolve().parents[2]
        shipped = json.loads(
            (root / "locale" / "fi-FI" / "exonyms.json").read_text(encoding="utf-8"))
        table = loc.load_exonyms(root / "locale", "fi-FI")
        assert table, "the fi-FI table must not read as empty"
        assert set(table) == {loc.fold(k) for k in shipped}


def test_the_lookup_count_is_bounded(service):
    """Each miss costs one request, and the service rate-limits (429 measured),
    so one utterance must not walk a long list of spellings."""
    with pytest.raises(LocationNotFoundError):
        get_geolocation("qwertzuiop", lang="fi-FI")
    assert len(service) <= loc.MAX_CANDIDATES


def test_a_rate_limit_is_not_read_as_a_miss(monkeypatch):
    """A refused request must not be retried with a different spelling: that
    multiplies the pressure on a service that is already saying no."""
    calls = []

    def _refuse(query, lang="en"):
        calls.append(query)
        raise ConnectionError("Geolocation failed: status code 429")

    monkeypatch.setattr("weather_helpers.util._get_geo", _refuse)
    loc._EXONYM_CACHE.clear()
    with pytest.raises(ConnectionError):
        get_geolocation("Tampereella", lang="fi-FI")
    assert calls == ["Tampereella"], "the first refusal must end the attempt"
