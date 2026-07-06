import os
import tempfile
import unittest
from datetime import date
from pathlib import Path
import sys

APP_DIR = Path(__file__).resolve().parents[1] / "flexible_shifts" / "app"
sys.path.insert(0, str(APP_DIR))

import db  # noqa: E402
from calculations import (  # noqa: E402
    annual_report,
    month_report,
    monthly_standard_hours,
    parse_time_value,
    shift_total_hours,
    weekend_days_in_month,
)


class CalculationTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        db.DB_PATH = str(Path(self.tempdir.name) / "test.db")
        db.init_db()
        self.user = db.create_user(
            {
                "name": "Test Part Time",
                "employment_type": "part_time",
                "target_basis": "weekly",
                "target_hours": 30.5,
                "monthly_from_weekly_mode": "x4",
                "overtime_min": 0,
                "overtime_max": 12,
                "active": True,
            }
        )

    def tearDown(self):
        self.tempdir.cleanup()

    def test_decimal_time_parser(self):
        self.assertEqual(parse_time_value("13,5"), "13:30")
        self.assertEqual(parse_time_value("6.5"), "06:30")
        self.assertEqual(parse_time_value("13.30"), "13:30")

    def test_split_shift_and_pause(self):
        split = {
            "work_segments": [
                {"start": "08:30", "end": "14:30"},
                {"start": "15:00", "end": "19:30"},
            ],
            "break_segments": [],
        }
        self.assertEqual(shift_total_hours(split), 10.5)

        paused = {
            "work_segments": [{"start": "08:00", "end": "17:00"}],
            "break_segments": [{"start": "12:30", "end": "13:00"}],
        }
        self.assertEqual(shift_total_hours(paused), 8.5)

    def test_sheet_compatible_monthly_standard(self):
        self.assertEqual(monthly_standard_hours(self.user), 122.0)

    def test_january_2026_has_nine_weekend_days(self):
        self.assertEqual(weekend_days_in_month(2026, 1), 9)

    def test_month_report_overtime_and_weekend(self):
        # 122 standard + 4.5 overtime = 126.5, matching the report pattern.
        db.upsert_shift(
            {
                "user_id": self.user["id"],
                "date": "2026-01-03",  # Saturday
                "work_segments": [{"start": "00:00", "end": "23:59"}],
                "break_segments": [],
                "note": "",
            }
        )
        # Add a second shift and a vacation week to reach a known total.
        db.upsert_shift(
            {
                "user_id": self.user["id"],
                "date": "2026-01-04",  # Sunday
                "work_segments": [{"start": "00:00", "end": "23:59"}],
                "break_segments": [],
                "note": "",
            }
        )
        db.create_vacation(
            {
                "user_id": self.user["id"],
                "start_date": "2026-01-05",
                "end_date": "2026-01-11",
                "credited_hours": 30.5,
                "note": "",
            }
        )
        report = month_report(self.user, 2026, 1)
        self.assertAlmostEqual(report["worked_hours"], 47.96, places=2)
        self.assertEqual(report["vacation_weeks"], 1)
        self.assertEqual(report["weekend_days_worked"], 2)
        self.assertEqual(report["weekend_days_available"], 9)

    def test_annual_report_current_month_cutoff(self):
        report = annual_report(self.user, 2026, today=date(2026, 5, 20))
        self.assertEqual(report["summary"]["active_months"], 5)
        self.assertEqual(report["summary"]["standard_hours"], 610.0)
        self.assertEqual(report["summary"]["weekend_days_available"], 44)

    def test_legacy_shift_migration(self):
        db.upsert_shift(
            {
                "user_id": self.user["id"],
                "date": "2026-02-02",
                "work_segments": [
                    {"start": "08:00", "end": "11:00"},
                    {"start": "15:00", "end": "19:30"},
                ],
                "break_segments": [],
                "note": "legacy",
            }
        )
        db.init_db()
        shift = db.get_shift_for_day(self.user["id"], "2026-02-02")
        self.assertEqual(shift["work_segments"], [{"start": "08:00", "end": "19:30"}])
        self.assertEqual(shift["break_segments"], [{"start": "11:00", "end": "15:00"}])
        self.assertEqual(shift_total_hours(shift), 7.5)


if __name__ == "__main__":
    unittest.main()
