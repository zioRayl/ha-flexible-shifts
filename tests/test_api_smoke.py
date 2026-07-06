import tempfile
import unittest
from pathlib import Path
import sys

APP_DIR = Path(__file__).resolve().parents[1] / "flexible_shifts" / "app"
sys.path.insert(0, str(APP_DIR))

import db  # noqa: E402
import main  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


class ApiSmokeTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        db.DB_PATH = str(Path(self.tempdir.name) / "api.db")
        main.DB_PATH = Path(db.DB_PATH)
        db.init_db()
        self.client = TestClient(main.app)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_create_user_shift_and_report(self):
        user_response = self.client.post(
            "/api/users",
            json={
                "name": "Mario",
                "employment_type": "part_time",
                "target_basis": "weekly",
                "target_hours": 30.5,
                "monthly_from_weekly_mode": "x4",
                "overtime_min": 0,
                "overtime_max": 12,
                "active": True,
            },
        )
        self.assertEqual(user_response.status_code, 201)
        user_id = user_response.json()["id"]

        shift_response = self.client.post(
            "/api/shifts",
            json={
                "user_id": user_id,
                "date": "2026-01-10",
                "work_segments": [{"start": "08:30", "end": "14:30"}],
                "break_segments": [],
                "note": "test",
            },
        )
        self.assertEqual(shift_response.status_code, 201)
        self.assertEqual(shift_response.json()["total_hours"], 6.0)

        calendar = self.client.get(
            f"/api/calendar?user_ids={user_id}&start=2026-01-05&end=2026-01-11"
        )
        self.assertEqual(calendar.status_code, 200)
        self.assertEqual(len(calendar.json()["shifts"]), 1)

        report = self.client.get(f"/api/reports/annual?user_id={user_id}&year=2026")
        self.assertEqual(report.status_code, 200)
        self.assertEqual(report.json()["months"][0]["weekend_days_worked"], 1)


if __name__ == "__main__":
    unittest.main()
