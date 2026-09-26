"""No test module may import this skill by its bare module name.

CI runs `pytest`, not `python -m pytest`, so the checkout root is not on
sys.path and the tests must import the package as it is installed:
`ovos_skill_weather.weather_helpers`, never `weather_helpers`. A bare import
works locally, where `python -m pytest` puts the working directory on sys.path,
and raises ModuleNotFoundError at collection on a runner -- which took the whole
unit-test job red on every Python for eight shas of dev, because a collection
error interrupts the run rather than failing one test (T-5755).

This check reads the test files as text. It needs no import of its own, so it
cannot be defeated by the very path problem it is about.
"""
import re
from pathlib import Path

import pytest

TEST_ROOT = Path(__file__).resolve().parents[1]

# The first-party names that must always be reached through the package.
BARE = ("weather_helpers", "ovos_skill_weather.weather_helpers".split(".")[0])
BARE_IMPORT = re.compile(
    r"^\s*(?:from\s+(weather_helpers)(?:\.\S+)?\s+import|import\s+(weather_helpers)\b)",
    re.M)


def _test_files():
    return sorted(p for p in TEST_ROOT.rglob("*.py")
                  if ".venv" not in p.parts and "pytest-cache-files" not in str(p))


def test_the_test_files_are_found():
    """The control: an empty sweep would make the check below vacuous."""
    files = _test_files()
    assert len(files) > 5, f"{len(files)} test files found under {TEST_ROOT}"


@pytest.mark.parametrize("path", _test_files(), ids=lambda p: p.name)
def test_the_module_is_imported_through_the_installed_package(path):
    found = BARE_IMPORT.search(path.read_text(encoding="utf-8"))
    assert not found, (
        f"{path.relative_to(TEST_ROOT)} imports 'weather_helpers' by its bare "
        "name. CI runs `pytest`, so the checkout root is not on sys.path and "
        "this raises ModuleNotFoundError at collection, which interrupts the "
        "whole run. Import 'ovos_skill_weather.weather_helpers' instead")


def test_the_pattern_matches_what_it_claims_to():
    """The control in the other direction: the check can still fail.

    Without this, a pattern that matched nothing would leave every case above
    passing for the wrong reason.
    """
    assert BARE_IMPORT.search("from weather_helpers import dialog\n")
    assert BARE_IMPORT.search("from weather_helpers.dialog import CurrentDialog\n")
    assert BARE_IMPORT.search("import weather_helpers\n")
    assert not BARE_IMPORT.search(
        "from ovos_skill_weather.weather_helpers import dialog\n")
    assert not BARE_IMPORT.search(
        '"ovos_skill_weather.weather_helpers.intent.get_geolocation"\n')
