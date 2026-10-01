"""Every line of the current high/low temperature dialogs must render.

``CurrentDialog.build_temperature_dialog`` supplies ``temperature``,
``temperature_unit`` and, for a ``_location`` name, ``location``. The gl-ES
and pt-BR files named ``{high_temperature}``, ``{low_temperature}`` and
``{scale}``, which no builder in this repository supplies.

``DialogFile.load`` formats each line with that data and, on ``KeyError``,
warns and **skips the line**. A file whose every line names an unsupplied
slot therefore loads as an empty list, and the skill speaks nothing.

The test renders each file through the real loader with the slot set the
real builder produces, so it measures the two together and not a copy of
either. The en-US files are the positive control: they ship the same
handler's dialogs and already render every line.
"""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from ovos_workshop.resource_files import DialogFile, ResourceType

from ovos_skill_weather.weather_helpers.dialog import CurrentDialog

SKILL_DIR = Path(__file__).resolve().parents[2]

#: The locales that ship the qualified current-temperature dialogs.
QUALIFIED_LOCALES = ("gl-ES", "pt-BR")

GEOLOCATION = dict(city="Lisbon", region="Lisbon", country="Portugal")


def _build(lang, temperature_type, remote):
    """Return (name, data) exactly as the skill's own builder produces them."""
    config = SimpleNamespace(
        lang=lang, country="Portugal", temperature_unit="celsius")
    intent_data = SimpleNamespace(
        location="Lisbon" if remote else None,
        geolocation=GEOLOCATION,
        config=config)
    weather = SimpleNamespace(
        temperature=14, temperature_high=21, temperature_low=9)
    built = CurrentDialog(intent_data, weather)
    built.build_temperature_dialog(temperature_type)
    return built.name, built.data


def _render(lang, name, data):
    """Load one dialog file through the real loader. Returns the lines kept."""
    resource_type = ResourceType("dialog", ".dialog", language=lang)
    resource_type.locate_base_directory(str(SKILL_DIR))
    dialog_file = DialogFile(resource_type, name + ".dialog")
    dialog_file.data = data
    return dialog_file.load()


def _raw_lines(lang, name):
    path = SKILL_DIR / "locale" / lang / "dialog" / "current" / f"{name}.dialog"
    return [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


CELLS = [
    (lang, temperature_type, remote)
    for lang in QUALIFIED_LOCALES
    for temperature_type in ("high", "low")
    for remote in (False, True)
]


@pytest.mark.parametrize("lang, temperature_type, remote", CELLS)
def test_every_line_renders_with_the_builders_slot_set(
        lang, temperature_type, remote):
    name, data = _build(lang, temperature_type, remote)
    kept = _render(lang, name, data)
    expected = _raw_lines(lang, name)
    assert kept is not None, f"{lang}/{name}: the loader found no file"
    assert len(kept) == len(expected), (
        f"{lang}/{name}: {len(expected) - len(kept)} of {len(expected)} lines "
        f"name a slot the builder does not supply, so they are skipped; "
        f"the builder supplies {sorted(data)}")
    for line in kept:
        assert "{" not in line, f"{lang}/{name}: unresolved slot in {line!r}"


@pytest.mark.parametrize("lang, temperature_type, remote", CELLS)
def test_the_files_name_no_slot_the_builder_withholds(
        lang, temperature_type, remote):
    """Read the text directly: the names must be the builder's names."""
    name, data = _build(lang, temperature_type, remote)
    for line in _raw_lines(lang, name):
        for forbidden in ("{high_temperature}", "{low_temperature}", "{scale}"):
            assert forbidden not in line, (
                f"{lang}/{name}: {forbidden} is supplied by no builder")


@pytest.mark.parametrize("remote", (False, True))
def test_the_control_en_us_renders_every_line(remote):
    """The positive control: the unqualified en-US files already render.

    Without it, a loader that returned an empty list for every input would
    let the cells above pass by returning nothing to compare.
    """
    name, data = _build("en-US", "current", remote)
    kept = _render("en-US", name, data)
    assert kept, f"en-US/{name}: the control rendered nothing"
    assert len(kept) == len(_raw_lines("en-US", name))


def test_the_control_an_unsupplied_slot_is_dropped():
    """The negative control: the loader does skip, it does not raise.

    The whole defect rests on that behaviour. If a future loader raised
    instead, the cells above would error rather than report a short file,
    and this cell says which of the two is true today.
    """
    name, data = _build("en-US", "current", False)
    short = _render("en-US", name, {"temperature": 14})
    full = _render("en-US", name, data)
    assert len(short) < len(full), (
        "the loader kept a line naming temperature_unit without it; "
        "the skip behaviour this test depends on has changed")
