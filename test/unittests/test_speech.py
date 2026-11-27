import datetime
import unittest

from ovos_skill_weather.weather_helpers.speech import spoken_time


class TestSpokenTimePtPT(unittest.TestCase):
    def _say(self, hour, minute):
        return spoken_time(datetime.datetime(2026, 3, 4, hour, minute), "pt-PT")

    def test_minutes_past(self):
        self.assertEqual(self._say(7, 5), "sete e cinco")

    def test_minutes_to(self):
        self.assertEqual(self._say(18, 40), "sete menos vinte")

    def test_noon(self):
        self.assertEqual(self._say(12, 0), "meio-dia em ponto")

    def test_midnight(self):
        self.assertEqual(self._say(0, 0), "meia-noite em ponto")


class TestSpokenTimePtBR(unittest.TestCase):
    """Gold from chronologia test/test_spoken_pt_br.py (Cunha & Cintra 2017
    p. 385)."""

    def _say(self, hour, minute):
        return spoken_time(datetime.datetime(2026, 3, 4, hour, minute), "pt-BR")

    def test_half_past_noon(self):
        self.assertEqual(self._say(12, 30), "meio-dia e meio")

    def test_half_past_midnight(self):
        self.assertEqual(self._say(0, 30), "meia-noite e meia")

    def test_minutes_past_noon(self):
        self.assertEqual(self._say(12, 10), "meio-dia e dez")

    def test_whole_hour_falls_back_to_nice_time(self):
        # chronologia refuses the pt-BR whole hour in the phrase style
        self.assertEqual(self._say(7, 0), "sete em ponto")


class TestSpokenTimeOtherLocales(unittest.TestCase):
    def test_en_us_keeps_nice_time(self):
        dt = datetime.datetime(2026, 3, 4, 7, 5)
        self.assertEqual(spoken_time(dt, "en-US"), "seven oh five")
