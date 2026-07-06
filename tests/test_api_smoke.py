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

    def create_user(self):
        response = self.client.post(
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
        self.assertEqual(response.status_code, 201)
        return response.json()

    def test_create_user_preset_shift_and_report(self):
        user = self.create_user()
        user_id = user["id"]

        preset_response = self.client.post(
            "/api/presets",
            json={
                "user_id": user_id,
                "name": "Spezzato",
                "start_time": "08:00",
                "end_time": "19:30",
                "pause_start": "11:00",
                "pause_end": "15:00",
            },
        )
        self.assertEqual(preset_response.status_code, 201)
        preset_id = preset_response.json()["id"]

        presets = self.client.get(f"/api/presets?user_id={user_id}")
        self.assertEqual(presets.status_code, 200)
        self.assertEqual(len(presets.json()), 1)
        self.assertEqual(presets.json()[0]["name"], "Spezzato")

        update_preset = self.client.put(
            f"/api/presets/{preset_id}",
            json={
                "user_id": user_id,
                "name": "Spezzato lungo",
                "start_time": "08:00",
                "end_time": "20:00",
                "pause_start": "11:00",
                "pause_end": "15:00",
            },
        )
        self.assertEqual(update_preset.status_code, 200)
        self.assertEqual(update_preset.json()["name"], "Spezzato lungo")

        shift_response = self.client.post(
            "/api/shifts",
            json={
                "user_id": user_id,
                "date": "2026-01-10",
                "work_segments": [{"start": "08:00", "end": "19:30"}],
                "break_segments": [{"start": "11:00", "end": "15:00"}],
                "note": "test",
            },
        )
        self.assertEqual(shift_response.status_code, 201)
        self.assertEqual(shift_response.json()["total_hours"], 7.5)

        calendar = self.client.get(
            f"/api/calendar?user_ids={user_id}&start=2026-01-05&end=2026-01-11"
        )
        self.assertEqual(calendar.status_code, 200)
        self.assertEqual(len(calendar.json()["shifts"]), 1)

        report = self.client.get(f"/api/reports/annual?user_id={user_id}&year=2026")
        self.assertEqual(report.status_code, 200)
        self.assertEqual(report.json()["months"][0]["weekend_days_worked"], 1)

        health = self.client.get("/api/health")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["version"], "0.3.0")

        shift_id = shift_response.json()["id"]
        delete_shift = self.client.delete(f"/api/shifts/{shift_id}")
        self.assertEqual(delete_shift.status_code, 204)
        self.assertEqual(delete_shift.content, b"")

        delete_preset = self.client.delete(f"/api/presets/{preset_id}")
        self.assertEqual(delete_preset.status_code, 204)
        self.assertEqual(delete_preset.content, b"")

        vacation_response = self.client.post(
            "/api/vacations",
            json={
                "user_id": user_id,
                "start_date": "2026-01-12",
                "end_date": "2026-01-12",
                "note": "giorno ferie",
            },
        )
        self.assertEqual(vacation_response.status_code, 201)
        self.assertEqual(vacation_response.json()["start_date"], "2026-01-12")
        self.assertEqual(vacation_response.json()["end_date"], "2026-01-12")
        self.assertAlmostEqual(vacation_response.json()["credited_hours"], 30.5 / 7, places=5)
        vacation_id = vacation_response.json()["id"]
        delete_vacation = self.client.delete(f"/api/vacations/{vacation_id}")
        self.assertEqual(delete_vacation.status_code, 204)
        self.assertEqual(delete_vacation.content, b"")

        delete_user = self.client.delete(f"/api/users/{user_id}")
        self.assertEqual(delete_user.status_code, 204)
        self.assertEqual(delete_user.content, b"")

    def test_vacation_range_and_legacy_week_payload(self):
        user_id = self.create_user()["id"]
        response = self.client.post(
            "/api/vacations",
            json={
                "user_id": user_id,
                "start_date": "2026-02-02",
                "end_date": "2026-02-04",
                "note": "tre giorni",
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertAlmostEqual(response.json()["credited_hours"], 30.5 * 3 / 7, places=5)

        calendar = self.client.get(
            f"/api/calendar?user_ids={user_id}&start=2026-02-03&end=2026-02-03"
        )
        self.assertEqual(calendar.status_code, 200)
        vacation = calendar.json()["vacations"][0]
        self.assertEqual(vacation["vacation_days_in_range"], 1)
        self.assertAlmostEqual(vacation["equivalent_weeks_in_range"], 0.14, places=2)

        legacy = self.client.post(
            "/api/vacations",
            json={"user_id": user_id, "date_in_week": "2026-02-09"},
        )
        self.assertEqual(legacy.status_code, 201)
        self.assertEqual(legacy.json()["start_date"], "2026-02-09")
        self.assertEqual(legacy.json()["end_date"], "2026-02-15")
        self.assertEqual(legacy.json()["credited_hours"], 30.5)

    def test_multiple_work_intervals_are_rejected(self):
        user_id = self.create_user()["id"]
        response = self.client.post(
            "/api/shifts",
            json={
                "user_id": user_id,
                "date": "2026-01-11",
                "work_segments": [
                    {"start": "08:00", "end": "11:00"},
                    {"start": "15:00", "end": "19:30"},
                ],
                "break_segments": [],
                "note": "vecchio formato",
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_pause_must_be_inside_shift(self):
        user_id = self.create_user()["id"]
        response = self.client.post(
            "/api/shifts",
            json={
                "user_id": user_id,
                "date": "2026-01-11",
                "work_segments": [{"start": "08:00", "end": "14:00"}],
                "break_segments": [{"start": "15:00", "end": "16:00"}],
                "note": "pausa fuori turno",
            },
        )
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
