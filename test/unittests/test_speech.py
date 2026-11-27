import datetime
import unittest

from weather_helpers.speech import spoken_time


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


class TestSpokenTimeOtherLocales(unittest.TestCase):
    def test_en_us_keeps_nice_time(self):
        dt = datetime.datetime(2026, 3, 4, 7, 5)
        self.assertEqual(spoken_time(dt, "en-US"), "seven oh five")
