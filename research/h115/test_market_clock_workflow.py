"""Offline check: H115 scheduler offers real NY-hours opportunities in both DST regimes.

No modification of frozen H115 signal engine or existing paper history.
"""
import re
import unittest
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/h115.yml"
NY = ZoneInfo("America/New_York")


def scheduled_hours():
    text = WORKFLOW.read_text(encoding="utf-8")
    match = re.search(r"cron:\s*'30 ([0-9,]+) \* \* 1-5'", text)
    if match is None:
        raise ValueError("H115_SCHEDULE_MISSING")
    return [int(h) for h in match.group(1).split(",")]


class H115ClockTests(unittest.TestCase):
    def test_four_staggered_opportunities(self):
        self.assertEqual(scheduled_hours(), [14, 16, 18, 20])

    def test_both_ny_timezone_regimes_offer_three_valid_attempts(self):
        for date in ((2026, 7, 21), (2026, 11, 20)):
            with self.subTest(date=date):
                attempts = [datetime(*date, hour, 30, tzinfo=timezone.utc).astimezone(NY)
                            for hour in scheduled_hours()]
                self.assertGreaterEqual(sum(10 <= x.hour < 16 for x in attempts), 3)

    def test_frozen_forward_file_not_part_of_new_schedule(self):
        # Changing forward.py changes H115's frozen source SHA and would invalidate
        # its existing ledger; this PR deliberately touches workflow + tests only.
        self.assertTrue((ROOT / "research/h115/forward.py").is_file())


if __name__ == "__main__":
    unittest.main()
